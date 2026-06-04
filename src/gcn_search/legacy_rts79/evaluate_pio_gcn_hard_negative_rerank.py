from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_pio_gcn_ensemble_ranking import _aggregate, _load_compact_baseline_rows, _load_truth, _make_score_table
from evaluate_rts79_paper_gcn_search import _load_gcn_model
from evaluate_rts79_pio_gcn_topk import _load_model as _load_pio_model
from rts79_cascade import Rts79InitialConfig, _build_branch_table, line_label_to_index_1based, run_initial_dcopf
from rts79_cascade_from_case import run_sequential_outages_from_case
from rts79_lodf import calculate_physical_vulnerability_y_p


@dataclass(frozen=True)
class RerankConfig:
    output_dir: str = "results/gcn_search/pio_rerank_preliminary"
    extended_dir: str = "results/gcn_search/pio_extended_fulltruth_5seed"
    pio_model: str = "results/gcn_search/pio_extended_fulltruth_5seed/training/physics_informed/rts79_physics_gcn_model.pt"
    pio_normalizer: str = "results/gcn_search/pio_extended_fulltruth_5seed/training/physics_dataset/rts79_step2_state_feature_normalizer_physics.json"
    paper_model: str = "results/gcn_search/paper_baseline_strong/paper_train_ce_only/rts79_physics_gcn_model.pt"
    paper_normalizer: str = "results/gcn_search/paper_baseline_strong/paper_dataset/rts79_step2_state_feature_normalizer.json"
    test_seed_start: int = 20260722
    test_num_seeds: int = 5
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    rerank_pool_size: int = 300
    beta: float = 1.2
    security_limit: float = 1.0


WEIGHTS = {
    "rerank_pio_dominant": {"pio": 0.65, "lodf": 0.15, "loading": 0.15, "relay": 0.05},
    "rerank_balanced": {"pio": 0.40, "lodf": 0.25, "loading": 0.25, "relay": 0.10},
    "rerank_physical_stress": {"pio": 0.25, "lodf": 0.25, "loading": 0.35, "relay": 0.15},
}


def evaluate_hard_negative_rerank(config: RerankConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    pio_model, pio_adjacency = _load_pio_model(config.pio_model)
    pio_normalizer = json.loads(Path(config.pio_normalizer).read_text(encoding="utf-8"))
    paper_model, paper_adjacency = _load_gcn_model(config.paper_model)
    paper_normalizer = json.loads(Path(config.paper_normalizer).read_text(encoding="utf-8"))
    per_seed_rows: list[dict] = []
    sweep_rows: list[dict] = []
    rescued_rows: list[dict] = []
    for seed in range(config.test_seed_start, config.test_seed_start + config.test_num_seeds):
        truth = _load_truth(config.extended_dir, seed)
        truth_by_path = truth.set_index("path")["critical"].astype(bool).to_dict()
        total_critical = int(truth["critical"].sum())
        score_table = _make_score_table(seed, config, pio_model, pio_adjacency, pio_normalizer, paper_model, paper_adjacency, paper_normalizer)
        pio_order = score_table.sort_values(["pio_score", "path"], ascending=[False, True])["path"].tolist()
        paper_order = score_table.sort_values(["paper_score", "path"], ascending=[False, True])["path"].tolist()
        oracle_order = truth.sort_values(["critical", "path"], ascending=[False, True])["path"].tolist()
        rerank_features = _make_rerank_features(seed, config, score_table, pio_order[: config.rerank_pool_size])
        orders = {
            "PIO_GCN": pio_order,
            "paper_GCN_path_prob_strong": paper_order,
            "oracle": oracle_order,
        }
        for method, weights in WEIGHTS.items():
            work = rerank_features.copy()
            work["rerank_score"] = (
                weights["pio"] * work["normalized_pio_score"]
                + weights["lodf"] * work["normalized_lodf_score"]
                + weights["loading"] * work["normalized_loading_stress"]
                + weights["relay"] * work["normalized_relay_risk"]
            )
            orders[method] = work.sort_values(["rerank_score", "path"], ascending=[False, True])["path"].tolist()
            sweep_rows.append(
                {
                    "seed": seed,
                    "method": method,
                    **{f"weight_{name}": value for name, value in weights.items()},
                    "top100_critical_count": sum(bool(truth_by_path.get(path, False)) for path in orders[method][:100]),
                    "top200_critical_count": sum(bool(truth_by_path.get(path, False)) for path in orders[method][:200]),
                }
            )
            pio_top200 = set(pio_order[:200])
            rerank_top200 = set(orders[method][:200])
            for path in sorted((rerank_top200 - pio_top200) & {p for p, c in truth_by_path.items() if c}):
                rescued_rows.append({"seed": seed, "method": method, "path": path, "critical": True})
        for method, order in orders.items():
            for k in config.top_k:
                subset = order[:k]
                found = sum(bool(truth_by_path.get(path, False)) for path in subset)
                per_seed_rows.append(
                    {
                        "seed": seed,
                        "method": method,
                        "top_k": k,
                        "critical_found": found,
                        "critical_path_recall": found / max(total_critical, 1),
                        "notes": "rerank top-300 PIO candidates" if method.startswith("rerank") else "baseline",
                    }
                )
        per_seed_rows.extend(_load_compact_baseline_rows(config.extended_dir, seed, config.top_k, methods=("LODF_yP",)))
    per_seed = pd.DataFrame(per_seed_rows)
    per_seed.to_csv(out / "rerank_topk_summary.csv", index=False, encoding="utf-8-sig")
    comparison = _aggregate(per_seed)
    comparison.to_csv(out / "rerank_method_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(sweep_rows).to_csv(out / "diagnostics" / "rerank_weight_sweep.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(rescued_rows).to_csv(out / "diagnostics" / "top200_rescued_paths.csv", index=False, encoding="utf-8-sig")
    _plot_recall_bar(comparison, out / "figures" / "rerank_recall_bar.png")
    return {"output_dir": str(out), "summary": str(out / "rerank_method_comparison.csv")}


def _make_rerank_features(seed: int, config: RerankConfig, score_table: pd.DataFrame, paths: list[str]) -> pd.DataFrame:
    root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
    lodf_lookup = _make_lodf_score_lookup(root_case, config)
    score_lookup = score_table.set_index("path").to_dict(orient="index")
    rows: list[dict] = []
    for path in paths:
        first, second = path.split("->")
        first_state = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        first_loading = _line_loading_ratio(root_case, first)
        second_loading = _line_loading_ratio(first_state["case"], second)
        max_s1_loading = _max_loading_ratio(first_state["case"])
        relay_risk = max(0.0, first_loading - config.beta) + max(0.0, second_loading - config.beta) + max(0.0, max_s1_loading - config.beta)
        loading_stress = max(first_loading, second_loading, max_s1_loading)
        row = score_lookup.get(path, {})
        rows.append(
            {
                "path": path,
                "pio_score": float(row.get("pio_score", 0.0)),
                "lodf_score": float(lodf_lookup.get(path, 0.0)),
                "first_line_loading_ratio": first_loading,
                "second_line_loading_ratio": second_loading,
                "loading_stress": loading_stress,
                "relay_risk": relay_risk,
                "security_margin_min": max(0.0, config.security_limit - loading_stress),
                "relay_margin_min": max(0.0, config.beta - loading_stress),
            }
        )
    table = pd.DataFrame(rows)
    table["normalized_pio_score"] = _minmax(table["pio_score"].to_numpy())
    table["normalized_lodf_score"] = _minmax(table["lodf_score"].to_numpy())
    table["normalized_loading_stress"] = _minmax(table["loading_stress"].to_numpy())
    table["normalized_relay_risk"] = _minmax(table["relay_risk"].to_numpy())
    return table


def _make_lodf_score_lookup(root_case: dict, config: RerankConfig) -> dict[str, float]:
    first_table = calculate_physical_vulnerability_y_p(root_case, beta=config.beta).dropna(subset=["y_P"])
    lookup: dict[str, float] = {}
    for _, first_row in first_table.iterrows():
        first = str(first_row["candidate_line"])
        state = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        second_table = calculate_physical_vulnerability_y_p(state["case"], beta=config.beta).dropna(subset=["y_P"])
        for _, second_row in second_table.iterrows():
            second = str(second_row["candidate_line"])
            if second == first:
                continue
            lookup[f"{first}->{second}"] = float(first_row["y_P"]) * float(second_row["y_P"])
    return lookup


def _line_loading_ratio(case: dict, label: str) -> float:
    branch_table = _build_branch_table(case)
    idx = line_label_to_index_1based(label) - 1
    if idx >= len(branch_table):
        return 0.0
    return float(branch_table.iloc[idx]["loading_ratio"])


def _max_loading_ratio(case: dict) -> float:
    branch_table = _build_branch_table(case)
    online = branch_table["status"] == 1
    return float(branch_table.loc[online, "loading_ratio"].max()) if online.any() else 0.0


def _minmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return values
    lo = float(np.nanmin(values))
    hi = float(np.nanmax(values))
    if hi - lo < 1e-12:
        return np.zeros_like(values, dtype=float)
    return (values - lo) / (hi - lo)


def _plot_recall_bar(comparison: pd.DataFrame, path: Path) -> None:
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["method"].astype(str), top["mean_recall"].astype(float))
    ax.set_title("Hard-Negative Rerank Recall at Max Top-K")
    ax.set_ylabel("Mean recall")
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate hard-negative-aware reranking for PIO-GCN path ranking.")
    parser.add_argument("--output-dir", default=RerankConfig.output_dir)
    parser.add_argument("--extended-dir", default=RerankConfig.extended_dir)
    parser.add_argument("--pio-model", default=RerankConfig.pio_model)
    parser.add_argument("--pio-normalizer", default=RerankConfig.pio_normalizer)
    parser.add_argument("--paper-model", default=RerankConfig.paper_model)
    parser.add_argument("--paper-normalizer", default=RerankConfig.paper_normalizer)
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=5)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100, 200])
    parser.add_argument("--rerank-pool-size", type=int, default=300)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_hard_negative_rerank(
        RerankConfig(
            output_dir=args.output_dir,
            extended_dir=args.extended_dir,
            pio_model=args.pio_model,
            pio_normalizer=args.pio_normalizer,
            paper_model=args.paper_model,
            paper_normalizer=args.paper_normalizer,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            rerank_pool_size=args.rerank_pool_size,
        )
    )


if __name__ == "__main__":
    main()
