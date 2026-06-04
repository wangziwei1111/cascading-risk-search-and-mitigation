from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from evaluate_pio_gcn_ensemble_ranking import _make_score_table
from evaluate_rts79_paper_gcn_search import _load_gcn_model
from evaluate_rts79_pio_gcn_topk import _load_model as _load_pio_model
from rts79_cascade import Rts79InitialConfig, _build_branch_table, line_label_to_index_1based, run_initial_dcopf
from rts79_cascade_from_case import run_sequential_outages_from_case
from rts79_lodf import calculate_physical_vulnerability_y_p


@dataclass(frozen=True)
class PathRerankerDatasetConfig:
    output_dir: str = "results/gcn_search/path_reranker_dataset"
    extended_dir: str = "results/gcn_search/pio_extended_fulltruth_5seed"
    pio_model: str = "results/gcn_search/pio_extended_fulltruth_5seed/training/physics_informed/rts79_physics_gcn_model.pt"
    pio_normalizer: str = "results/gcn_search/pio_extended_fulltruth_5seed/training/physics_dataset/rts79_step2_state_feature_normalizer_physics.json"
    paper_model: str = "results/gcn_search/paper_baseline_strong/paper_train_ce_only/rts79_physics_gcn_model.pt"
    paper_normalizer: str = "results/gcn_search/paper_baseline_strong/paper_dataset/rts79_step2_state_feature_normalizer.json"
    test_seed_start: int = 20260722
    test_num_seeds: int = 5
    train_seeds: tuple[int, ...] = (20260722, 20260723, 20260724)
    val_seeds: tuple[int, ...] = (20260725,)
    test_seeds: tuple[int, ...] = (20260726,)
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    beta: float = 1.2
    security_limit: float = 1.0


def build_path_reranker_dataset(config: PathRerankerDatasetConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "path_reranker_dataset_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    pio_model, pio_adjacency = _load_pio_model(config.pio_model)
    pio_normalizer = json.loads(Path(config.pio_normalizer).read_text(encoding="utf-8"))
    paper_model, paper_adjacency = _load_gcn_model(config.paper_model)
    paper_normalizer = json.loads(Path(config.paper_normalizer).read_text(encoding="utf-8"))
    rows: list[dict] = []
    for seed in range(config.test_seed_start, config.test_seed_start + config.test_num_seeds):
        root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        truth = _load_truth(config.extended_dir, seed)
        score_table = _make_score_table(seed, config, pio_model, pio_adjacency, pio_normalizer, paper_model, paper_adjacency, paper_normalizer)
        score_by_path = score_table.set_index("path").to_dict(orient="index")
        pio_rank = _rank_lookup(score_table, "pio_score")
        paper_rank = _rank_lookup(score_table, "paper_score")
        lodf_score = _make_lodf_score_lookup(root_case, config)
        lodf_rank = _rank_lookup(pd.DataFrame({"path": list(lodf_score), "lodf_score": list(lodf_score.values())}), "lodf_score")
        first_state_cache: dict[str, dict] = {}
        for _, item in truth.iterrows():
            path = str(item["path"])
            first, second = path.split("->")
            if first not in first_state_cache:
                first_state_cache[first] = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
            first_state = first_state_cache[first]
            score_row = score_by_path.get(path, {})
            first_loading = _line_loading_ratio(root_case, first)
            second_loading = _line_loading_ratio(first_state["case"], second)
            first_abs_flow = _line_abs_flow(root_case, first)
            second_abs_flow = _line_abs_flow(first_state["case"], second)
            first_outage_max_loading = _max_loading_ratio(first_state["case"])
            loading_values = [first_loading, second_loading, first_outage_max_loading]
            max_loading = float(max(loading_values))
            rows.append(
                {
                    "seed": seed,
                    "first_line": first,
                    "second_line": second,
                    "path": path,
                    "is_critical": int(bool(item["critical"])),
                    "total_load_shed_mw": float(item.get("total_load_shed_mw", 0.0)),
                    "rank_in_pio": int(pio_rank.get(path, 999999)),
                    "rank_in_paper": int(paper_rank.get(path, 999999)),
                    "rank_in_lodf": int(lodf_rank.get(path, 999999)),
                    "pio_score": float(score_row.get("pio_score", 0.0)),
                    "paper_score": float(score_row.get("paper_score", 0.0)),
                    "lodf_score": float(lodf_score.get(path, 0.0)),
                    "ensemble_score_alpha_0_75": 0.75 * float(score_row.get("normalized_pio_score", 0.0)) + 0.25 * float(score_row.get("normalized_paper_score", 0.0)),
                    "first_line_loading_ratio": first_loading,
                    "second_line_loading_ratio": second_loading,
                    "max_loading_ratio": max_loading,
                    "min_security_margin": float(config.security_limit - max_loading),
                    "min_relay_margin": float(config.beta - max_loading),
                    "first_line_abs_flow": first_abs_flow,
                    "second_line_abs_flow": second_abs_flow,
                    "first_outage_num_overloaded_lines": _num_overloaded(first_state["case"], config.security_limit),
                    "first_outage_max_loading_ratio": first_outage_max_loading,
                    "first_outage_total_load_shed_mw": float(first_state.get("island_load_shed_mw", 0.0)) + float(first_state.get("redispatch_load_shed_mw", 0.0)),
                    "candidate_position_min_rank": min(int(pio_rank.get(path, 999999)), int(paper_rank.get(path, 999999)), int(lodf_rank.get(path, 999999))),
                    "y_critical": int(bool(item["critical"])),
                    "y_load_shed": float(item.get("total_load_shed_mw", 0.0)),
                }
            )
    dataset = pd.DataFrame(rows)
    _write_split(dataset, config.train_seeds, out / "path_reranker_train.csv")
    _write_split(dataset, config.val_seeds, out / "path_reranker_val.csv")
    _write_split(dataset, config.test_seeds, out / "path_reranker_test.csv")
    dataset.head(300).to_csv(out / "path_reranker_dataset_sample.csv", index=False, encoding="utf-8-sig")
    stats = _make_stats(dataset, config)
    (out / "path_reranker_dataset_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def _load_truth(extended_dir: str | Path, seed: int) -> pd.DataFrame:
    return pd.read_csv(Path(extended_dir) / "seeds" / f"seed_{seed}" / "pio_topk_full_truth" / "pio_gcn_topk_full_truth.csv")


def _rank_lookup(table: pd.DataFrame, score_col: str) -> dict[str, int]:
    if table.empty or score_col not in table:
        return {}
    ordered = table.sort_values([score_col, "path"], ascending=[False, True])["path"].tolist()
    return {path: rank for rank, path in enumerate(ordered, start=1)}


def _make_lodf_score_lookup(root_case: dict, config: PathRerankerDatasetConfig) -> dict[str, float]:
    first_table = calculate_physical_vulnerability_y_p(root_case, beta=config.beta).dropna(subset=["y_P"])
    lookup: dict[str, float] = {}
    for _, first_row in first_table.iterrows():
        first = str(first_row["candidate_line"])
        state = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        second_table = calculate_physical_vulnerability_y_p(state["case"], beta=config.beta).dropna(subset=["y_P"])
        for _, second_row in second_table.iterrows():
            second = str(second_row["candidate_line"])
            if second != first:
                lookup[f"{first}->{second}"] = float(first_row["y_P"]) * float(second_row["y_P"])
    return lookup


def _branch_row(case: dict, label: str) -> pd.Series:
    table = _build_branch_table(case)
    return table.iloc[line_label_to_index_1based(label) - 1]


def _line_loading_ratio(case: dict, label: str) -> float:
    return float(_branch_row(case, label)["loading_ratio"])


def _line_abs_flow(case: dict, label: str) -> float:
    return abs(float(_branch_row(case, label)["F_MW"]))


def _max_loading_ratio(case: dict) -> float:
    table = _build_branch_table(case)
    online = table["status"] == 1
    return float(table.loc[online, "loading_ratio"].max()) if online.any() else 0.0


def _num_overloaded(case: dict, limit: float) -> int:
    table = _build_branch_table(case)
    return int(((table["status"] == 1) & (table["loading_ratio"] > limit)).sum())


def _write_split(dataset: pd.DataFrame, seeds: tuple[int, ...], path: Path) -> None:
    dataset[dataset["seed"].isin(seeds)].to_csv(path, index=False, encoding="utf-8-sig")


def _make_stats(dataset: pd.DataFrame, config: PathRerankerDatasetConfig) -> dict:
    by_seed = dataset.groupby("seed").agg(num_samples=("path", "count"), num_critical=("y_critical", "sum")).reset_index()
    return {
        "num_samples": int(len(dataset)),
        "num_critical": int(dataset["y_critical"].sum()),
        "positive_ratio": float(dataset["y_critical"].mean()),
        "train_seeds": list(config.train_seeds),
        "val_seeds": list(config.val_seeds),
        "test_seeds": list(config.test_seeds),
        "per_seed": by_seed.to_dict(orient="records"),
        "notes": "Compact path-level dataset; full-truth detail files remain local under ignored seed directories.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compact path-level dataset for learned PIO-GCN reranking.")
    parser.add_argument("--output-dir", default=PathRerankerDatasetConfig.output_dir)
    parser.add_argument("--extended-dir", default=PathRerankerDatasetConfig.extended_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_path_reranker_dataset(PathRerankerDatasetConfig(output_dir=args.output_dir, extended_dir=args.extended_dir))


if __name__ == "__main__":
    main()
