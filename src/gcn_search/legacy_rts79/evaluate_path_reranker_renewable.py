from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from build_path_reranker_dataset import PathRerankerDatasetConfig
from path_reranker_eval_utils import (
    DEFAULT_TOP_K,
    aggregate,
    dataclass_payload,
    evaluate_orders,
    generate_truth_from_case,
    make_orders,
    make_path_feature_table_from_scores,
    make_score_table_from_case,
    plot_recall_bar,
    plot_topk_curve,
    rank_shift_diagnostics,
    train_reranker_models,
    write_json,
)
from renewable_scenarios import RenewableScenarioConfig, apply_renewable_scenario_to_case, summarize_renewable_case
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf


@dataclass(frozen=True)
class RenewableRerankerEvalConfig:
    output_dir: str = "results/gcn_search/path_reranker_renewable_eval"
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    test_seed_start: int = 20260722
    test_num_seeds: int = 3
    top_k: tuple[int, ...] = DEFAULT_TOP_K
    train_epochs: int = 80
    renewable_penetration_ratio: float = 0.30
    fluctuation_low: float = 0.6
    fluctuation_high: float = 1.1
    beta: float = 1.2
    security_limit: float = 1.0


def evaluate_path_reranker_renewable(config: RenewableRerankerEvalConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    write_json(out / "renewable_path_reranker_config.json", dataclass_payload(config))
    base_config = PathRerankerDatasetConfig(top_k=config.top_k, beta=config.beta, security_limit=config.security_limit)
    models = train_reranker_models(config.dataset_dir, epochs=config.train_epochs)
    per_seed_rows: list[pd.DataFrame] = []
    case_rows: list[dict] = []
    rank_rows: list[pd.DataFrame] = []
    missed_rows: list[pd.DataFrame] = []
    for seed in range(config.test_seed_start, config.test_seed_start + config.test_num_seeds):
        base_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        renewable_config = RenewableScenarioConfig(
            renewable_penetration_ratio=config.renewable_penetration_ratio,
            fluctuation_low=config.fluctuation_low,
            fluctuation_high=config.fluctuation_high,
            random_seed=seed,
            description="Synthetic renewable perturbation for path-reranker robustness; not a real SCADA/PMU deployment.",
        )
        root_case = apply_renewable_scenario_to_case(base_case, renewable_config)
        case_summary = summarize_renewable_case(base_case, root_case, renewable_config)
        case_summary["seed"] = seed
        case_rows.append(case_summary)
        truth = generate_truth_from_case(root_case, seed, base_config)
        score_table = make_score_table_from_case(root_case, seed, base_config)
        dataset = make_path_feature_table_from_scores(root_case, seed, truth, base_config, score_table)
        orders = make_orders(dataset, models, suffix="renewable")
        renamed_orders = {}
        for method, order in orders.items():
            renamed_orders[method.replace("_external_renewable", "_renewable").replace("_external", "_renewable")] = order
        per_seed_rows.append(evaluate_orders(seed, truth, renamed_orders, config.top_k, _notes()))
        rank, missed, _ = rank_shift_diagnostics(seed, dataset, renamed_orders)
        rank_rows.append(rank)
        missed_rows.append(missed)
    per_seed = pd.concat(per_seed_rows, ignore_index=True)
    comparison = aggregate(per_seed)
    pd.DataFrame(case_rows).to_csv(out / "renewable_case_summary.csv", index=False, encoding="utf-8-sig")
    per_seed.to_csv(out / "renewable_path_reranker_topk_summary.csv", index=False, encoding="utf-8-sig")
    per_seed.to_csv(out / "renewable_path_reranker_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(out / "renewable_path_reranker_method_comparison.csv", index=False, encoding="utf-8-sig")
    pd.concat(missed_rows, ignore_index=True).to_csv(out / "diagnostics" / "renewable_missed_critical.csv", index=False, encoding="utf-8-sig")
    pd.concat(rank_rows, ignore_index=True).to_csv(out / "diagnostics" / "renewable_rank_shift_summary.csv", index=False, encoding="utf-8-sig")
    plot_recall_bar(comparison, out / "figures" / "renewable_path_reranker_recall_bar.png", "Synthetic Renewable Path Reranker Recall")
    plot_topk_curve(comparison, out / "figures" / "renewable_path_reranker_topk_curve.png", "Synthetic Renewable Path Reranker Top-K Curve")
    return {"output_dir": str(out), "summary": str(out / "renewable_path_reranker_method_comparison.csv")}


def _notes() -> dict[str, str]:
    return {
        "PIO_GCN": "PIO-GCN PathRank on synthetic renewable cases",
        "paper_GCN_path_prob_strong": "strong paper-style GCN baseline on synthetic renewable cases",
        "LODF_yP": "LODF-yP baseline on synthetic renewable cases",
        "rerank_physical_stress": "hand-crafted physical-stress rerank baseline",
        "learned_logistic_reranker_renewable": "trained on standard RTS-79 seeds, tested on synthetic renewable perturbation",
        "learned_mlp_reranker_renewable": "trained on standard RTS-79 seeds, tested on synthetic renewable perturbation",
        "oracle": "upper bound using full truth labels",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate learned path reranker on synthetic renewable RTS-79 cases.")
    parser.add_argument("--output-dir", default=RenewableRerankerEvalConfig.output_dir)
    parser.add_argument("--dataset-dir", default=RenewableRerankerEvalConfig.dataset_dir)
    parser.add_argument("--test-seed-start", type=int, default=RenewableRerankerEvalConfig.test_seed_start)
    parser.add_argument("--test-num-seeds", type=int, default=RenewableRerankerEvalConfig.test_num_seeds)
    parser.add_argument("--top-k", type=int, nargs="+", default=list(DEFAULT_TOP_K))
    parser.add_argument("--train-epochs", type=int, default=RenewableRerankerEvalConfig.train_epochs)
    parser.add_argument("--renewable-penetration-ratio", type=float, default=RenewableRerankerEvalConfig.renewable_penetration_ratio)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_path_reranker_renewable(
        RenewableRerankerEvalConfig(
            output_dir=args.output_dir,
            dataset_dir=args.dataset_dir,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            train_epochs=args.train_epochs,
            renewable_penetration_ratio=args.renewable_penetration_ratio,
        )
    )


if __name__ == "__main__":
    main()
