from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _load_model, _make_full_truth, _make_path_order
from gcn_physics_constraints import make_candidate_mask
from renewable_scenarios import RenewableScenarioConfig, apply_renewable_scenario_to_case, summarize_renewable_case
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf
from rts79_cascade_from_case import run_sequential_outages_from_case, simulate_cascade_path_from_case
from rts79_lodf import calculate_physical_vulnerability_y_p
from train_rts79_paper_gcn import _make_x_gcn
from evaluate_rts79_paper_gcn_search import _load_gcn_model, _normalize_with_saved_stats


@dataclass(frozen=True)
class RenewablePreliminaryConfig:
    output_dir: str = "results/gcn_search/pio_renewable_preliminary"
    model: str = "results/gcn_search/pio_formal_preliminary_3seed/training/physics_informed/rts79_physics_gcn_model.pt"
    normalizer: str = "results/gcn_search/pio_formal_preliminary_3seed/training/physics_dataset/rts79_step2_state_feature_normalizer_physics.json"
    test_seed_start: int = 20260722
    test_num_seeds: int = 3
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    beta: float = 1.2
    security_limit: float = 1.0
    renewable_penetration_ratio: float = 0.2
    fluctuation_low: float = 0.6
    fluctuation_high: float = 1.1
    run_full_truth: bool = True
    paper_baseline_model: str | None = "results/gcn_search/paper_baseline_strong/paper_train_ce_only/rts79_physics_gcn_model.pt"
    paper_baseline_normalizer: str | None = "results/gcn_search/paper_baseline_strong/paper_dataset/rts79_step2_state_feature_normalizer.json"


def run_renewable_preliminary_experiment(config: RenewablePreliminaryConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    model, adjacency = _load_model(config.model)
    normalizer = json.loads(Path(config.normalizer).read_text(encoding="utf-8"))
    paper_model = paper_adjacency = paper_normalizer = None
    if config.paper_baseline_model and config.paper_baseline_normalizer and Path(config.paper_baseline_model).exists() and Path(config.paper_baseline_normalizer).exists():
        paper_model, paper_adjacency = _load_gcn_model(config.paper_baseline_model)
        paper_normalizer = json.loads(Path(config.paper_baseline_normalizer).read_text(encoding="utf-8"))
    case_rows, pio_rows, baseline_rows, truth_rows = [], [], [], []
    for offset in range(config.test_num_seeds):
        seed = config.test_seed_start + offset
        base_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        renewable_config = RenewableScenarioConfig(
            renewable_penetration_ratio=config.renewable_penetration_ratio,
            fluctuation_low=config.fluctuation_low,
            fluctuation_high=config.fluctuation_high,
            random_seed=seed,
            description="Synthetic renewable perturbation for RTS-79 PIO-GCN robustness check; not EMT or dynamic simulation.",
        )
        root_case = apply_renewable_scenario_to_case(base_case, renewable_config)
        case_summary = summarize_renewable_case(base_case, root_case, renewable_config)
        case_summary["seed"] = seed
        case_rows.append(case_summary)
        pio_config = PioTopkConfig(model=config.model, normalizer=config.normalizer, output_dir="", seed=seed, beta=config.beta, security_limit=config.security_limit, top_k=config.top_k, run_full_truth=config.run_full_truth)
        start = time.time()
        order = pd.DataFrame(_make_path_order(model, adjacency, normalizer, root_case, pio_config))
        runtime = time.time() - start
        sim_rows = []
        for _, row in order.head(max(config.top_k)).iterrows():
            first, second = str(row["path"]).split("->")
            result = simulate_cascade_path_from_case(root_case, [first, second], beta=config.beta, security_limit=config.security_limit)
            sim_rows.append({"path": row["path"], "critical": bool(result.total_load_shed_mw > 1e-7), "total_load_shed_mw": float(result.total_load_shed_mw)})
        sim = pd.DataFrame(sim_rows)
        truth = _make_full_truth(root_case, pio_config) if config.run_full_truth else sim.copy()
        total_critical = int(truth["critical"].sum())
        truth_rows.append({"seed": seed, "num_ordered_n2_paths": int(len(truth)), "total_critical_paths": total_critical, "full_truth": bool(config.run_full_truth)})
        for k in config.top_k:
            subset = sim.head(k)
            found = int(subset["critical"].sum())
            pio_rows.append({"seed": seed, "method": f"PIO_GCN_Top{k}", "top_k": k, "critical_found": found, "critical_path_recall": found / max(total_critical, 1), "runtime_seconds": runtime, "notes": "synthetic renewable preliminary"})
        baseline_rows.extend(_renewable_baselines(seed, root_case, truth, config, paper_model, paper_adjacency, paper_normalizer))
    pd.DataFrame(case_rows).to_csv(out / "renewable_case_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(truth_rows).to_csv(out / "per_seed_fulltruth_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(pio_rows).to_csv(out / "pio_topk_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(baseline_rows).to_csv(out / "baseline_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    aggregate_topk = _aggregate_pio(pd.DataFrame(pio_rows))
    comparison = _aggregate_comparison(pd.DataFrame(pio_rows), pd.DataFrame(baseline_rows))
    aggregate_topk.to_csv(out / "aggregate_topk_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(out / "aggregate_method_comparison.csv", index=False, encoding="utf-8-sig")
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    case_diag = pd.DataFrame(case_rows)
    case_diag.to_csv(diagnostics / "renewable_case_diagnostics.csv", index=False, encoding="utf-8-sig")
    pio_summary = pd.DataFrame(pio_rows)
    pio_summary.sort_values("critical_path_recall").head(1).to_csv(diagnostics / "renewable_worst_seed_summary.csv", index=False, encoding="utf-8-sig")
    pio_summary.sort_values("critical_path_recall", ascending=False).head(1).to_csv(diagnostics / "renewable_best_seed_summary.csv", index=False, encoding="utf-8-sig")
    _plot_renewable(comparison, out / "figures")
    return {"output_dir": str(out)}


def _renewable_baselines(seed: int, root_case: dict, truth: pd.DataFrame, config: RenewablePreliminaryConfig, paper_model, paper_adjacency, paper_normalizer) -> list[dict]:
    rows = []
    truth_by_path = truth.set_index("path").to_dict(orient="index")
    total = int(truth["critical"].sum())
    paths = sorted(truth["path"].astype(str).tolist())
    rng = np.random.default_rng(seed)
    random_paths = paths.copy()
    rng.shuffle(random_paths)
    oracle_paths = truth.sort_values(["critical", "total_load_shed_mw"], ascending=[False, False])["path"].astype(str).tolist()
    orders = {
        "random": random_paths,
        "line_order": paths,
        "oracle": oracle_paths,
        "LODF_yP": _make_lodf_order_from_case(root_case, config),
    }
    if paper_model is not None and paper_adjacency is not None and paper_normalizer is not None:
        orders["paper_GCN_path_prob_strong"] = _make_paper_gcn_order_from_case(root_case, config, paper_model, paper_adjacency, paper_normalizer)
    for method, ordered in orders.items():
        for k in config.top_k:
            subset = ordered[:k]
            found = sum(bool(truth_by_path.get(path, {}).get("critical", False)) for path in subset)
            rows.append({"seed": seed, "method": method, "top_k": k, "critical_found": found, "critical_path_recall": found / max(total, 1), "runtime_seconds": 0.0, "notes": "synthetic renewable baseline"})
    return rows


def _make_lodf_order_from_case(root_case: dict, config: RenewablePreliminaryConfig) -> list[str]:
    paths: list[str] = []
    first_order = _rank_yp(root_case, config.beta)
    for first in first_order:
        state = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        for second in _rank_yp(state["case"], config.beta):
            if second != first:
                paths.append(f"{first}->{second}")
    return _dedupe(paths)


def _rank_yp(case: dict, beta: float) -> list[str]:
    table = calculate_physical_vulnerability_y_p(case, beta=beta).dropna(subset=["y_P"])
    return table.sort_values(["y_P", "candidate_line"], ascending=[False, True])["candidate_line"].astype(str).tolist()


def _make_paper_gcn_order_from_case(root_case: dict, config: RenewablePreliminaryConfig, model, adjacency, normalizer: dict) -> list[str]:
    first_prob = _predict_paper_probability(model, adjacency, normalizer, root_case, config.beta)
    first_mask = make_candidate_mask(root_case)
    paths: list[tuple[str, float]] = []
    for first_idx in np.where(first_mask)[0]:
        first = f"L{first_idx + 1:02d}"
        state = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        second_prob = _predict_paper_probability(model, adjacency, normalizer, state["case"], config.beta)
        second_mask = make_candidate_mask(state["case"], used_lines=[first])
        for second_idx in np.where(second_mask)[0]:
            second = f"L{second_idx + 1:02d}"
            paths.append((f"{first}->{second}", float(first_prob[first_idx] * second_prob[second_idx])))
    paths.sort(key=lambda item: (-item[1], item[0]))
    return _dedupe([path for path, _ in paths])


def _predict_paper_probability(model, adjacency, normalizer: dict, case: dict, beta: float) -> np.ndarray:
    x_raw = _make_x_gcn(case, beta)[None, :, :]
    x = _normalize_with_saved_stats(x_raw, normalizer)
    with torch.no_grad():
        logits = model(torch.tensor(x, dtype=torch.float32), adjacency)
        return torch.softmax(logits, dim=2)[0, :, 1].numpy()


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def _aggregate_pio(pio: pd.DataFrame) -> pd.DataFrame:
    return pio.groupby(["method", "top_k"], sort=False).agg(num_test_seeds=("seed", "nunique"), mean_critical_found=("critical_found", "mean"), std_critical_found=("critical_found", lambda x: x.std(ddof=0)), mean_critical_path_recall=("critical_path_recall", "mean"), std_critical_path_recall=("critical_path_recall", lambda x: x.std(ddof=0)), mean_runtime_seconds=("runtime_seconds", "mean"), notes=("notes", "first")).reset_index()


def _aggregate_comparison(pio: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    all_rows = pd.concat([pio, baseline], ignore_index=True)
    return all_rows.groupby(["method", "top_k"], sort=False).agg(num_test_seeds=("seed", "nunique"), mean_found=("critical_found", "mean"), std_found=("critical_found", lambda x: x.std(ddof=0)), mean_recall=("critical_path_recall", "mean"), std_recall=("critical_path_recall", lambda x: x.std(ddof=0)), mean_runtime_seconds=("runtime_seconds", "mean"), notes=("notes", "first")).reset_index()


def _plot_renewable(comparison: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    for filename, value_col, title in [
        ("renewable_topk_recall_bar.png", "mean_recall", "Synthetic Renewable Recall"),
        ("renewable_baseline_comparison.png", "mean_found", "Synthetic Renewable Critical Paths Found"),
        ("renewable_runtime_comparison.png", "mean_runtime_seconds", "Synthetic Renewable Runtime"),
    ]:
        fig, ax = plt.subplots(figsize=(8, 4), dpi=160)
        ax.bar(top["method"].astype(str), top[value_col].astype(float))
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
        fig.tight_layout()
        fig.savefig(figure_dir / filename)
        plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run synthetic renewable RTS-79 PIO-GCN preliminary evaluation.")
    parser.add_argument("--output-dir", default="results/gcn_search/pio_renewable_preliminary")
    parser.add_argument("--model", default=RenewablePreliminaryConfig.model)
    parser.add_argument("--normalizer", default=RenewablePreliminaryConfig.normalizer)
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=3)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100, 200])
    parser.add_argument("--renewable-penetration-ratio", type=float, default=0.2)
    parser.add_argument("--fluctuation-low", type=float, default=0.6)
    parser.add_argument("--fluctuation-high", type=float, default=1.1)
    parser.add_argument("--paper-baseline-model", default=RenewablePreliminaryConfig.paper_baseline_model)
    parser.add_argument("--paper-baseline-normalizer", default=RenewablePreliminaryConfig.paper_baseline_normalizer)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_renewable_preliminary_experiment(
        RenewablePreliminaryConfig(
            output_dir=args.output_dir,
            model=args.model,
            normalizer=args.normalizer,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            renewable_penetration_ratio=args.renewable_penetration_ratio,
            fluctuation_low=args.fluctuation_low,
            fluctuation_high=args.fluctuation_high,
            paper_baseline_model=args.paper_baseline_model,
            paper_baseline_normalizer=args.paper_baseline_normalizer,
        )
    )


if __name__ == "__main__":
    main()
