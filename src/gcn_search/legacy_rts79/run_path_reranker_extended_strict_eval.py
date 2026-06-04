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
    make_path_feature_table,
    plot_recall_bar,
    plot_topk_curve,
    rank_shift_diagnostics,
    train_reranker_models,
    write_json,
)
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf


@dataclass(frozen=True)
class ExtendedStrictEvalConfig:
    output_dir: str = "results/gcn_search/path_reranker_extended_strict_eval"
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    external_seed_start: int = 20260727
    external_num_seeds: int = 3
    top_k: tuple[int, ...] = DEFAULT_TOP_K
    train_epochs: int = 80
    beta: float = 1.2
    security_limit: float = 1.0


def run_extended_strict_eval(config: ExtendedStrictEvalConfig) -> dict:
    out = Path(config.output_dir)
    (out / "diagnostics").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    write_json(out / "extended_strict_config.json", dataclass_payload(config))
    base_config = PathRerankerDatasetConfig(top_k=config.top_k, beta=config.beta, security_limit=config.security_limit)
    models = train_reranker_models(config.dataset_dir, epochs=config.train_epochs)
    per_seed_rows: list[pd.DataFrame] = []
    truth_summary_rows: list[dict] = []
    rank_rows: list[pd.DataFrame] = []
    missed_rows: list[pd.DataFrame] = []
    rescued_rows: list[pd.DataFrame] = []
    for seed in range(config.external_seed_start, config.external_seed_start + config.external_num_seeds):
        root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        truth = generate_truth_from_case(root_case, seed, base_config)
        dataset = make_path_feature_table(root_case, seed, truth, base_config)
        orders = make_orders(dataset, models, suffix="external")
        per_seed_rows.append(evaluate_orders(seed, truth, orders, config.top_k, _notes()))
        truth_summary_rows.append(
            {
                "seed": seed,
                "num_ordered_n2_paths": int(len(truth)),
                "total_critical_paths": int(truth["critical"].sum()),
                "full_truth": True,
            }
        )
        rank, missed, rescued = rank_shift_diagnostics(seed, dataset, orders)
        rank_rows.append(rank)
        missed_rows.append(missed)
        rescued_rows.append(rescued)
    per_seed = pd.concat(per_seed_rows, ignore_index=True)
    comparison = aggregate(per_seed)
    pd.DataFrame(truth_summary_rows).to_csv(out / "external_seed_fulltruth_summary.csv", index=False, encoding="utf-8-sig")
    per_seed.to_csv(out / "extended_strict_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(out / "extended_strict_method_comparison.csv", index=False, encoding="utf-8-sig")
    pd.concat(missed_rows, ignore_index=True).to_csv(out / "diagnostics" / "external_seed_missed_critical.csv", index=False, encoding="utf-8-sig")
    pd.concat(rescued_rows, ignore_index=True).to_csv(out / "diagnostics" / "external_seed_rescued_critical.csv", index=False, encoding="utf-8-sig")
    pd.concat(rank_rows, ignore_index=True).to_csv(out / "diagnostics" / "external_seed_rank_shift_summary.csv", index=False, encoding="utf-8-sig")
    plot_recall_bar(comparison, out / "figures" / "extended_strict_recall_bar.png", "External Seed Strict Recall")
    plot_topk_curve(comparison, out / "figures" / "extended_strict_topk_curve.png", "External Seed Strict Top-K Curve")
    return {"output_dir": str(out), "summary": str(out / "extended_strict_method_comparison.csv")}


def _notes() -> dict[str, str]:
    return {
        "PIO_GCN": "PIO-GCN PathRank baseline on external unseen seeds",
        "paper_GCN_path_prob_strong": "strong paper-style GCN baseline",
        "LODF_yP": "physical LODF-yP baseline",
        "rerank_physical_stress": "hand-crafted physical-stress rerank baseline",
        "learned_logistic_reranker_external": "trained on seeds 20260722-20260726, evaluated on unseen external seeds",
        "learned_mlp_reranker_external": "trained on seeds 20260722-20260726, evaluated on unseen external seeds",
        "oracle": "upper bound using full truth labels",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="External unseen-seed strict evaluation for learned path reranker.")
    parser.add_argument("--output-dir", default=ExtendedStrictEvalConfig.output_dir)
    parser.add_argument("--dataset-dir", default=ExtendedStrictEvalConfig.dataset_dir)
    parser.add_argument("--external-seed-start", type=int, default=ExtendedStrictEvalConfig.external_seed_start)
    parser.add_argument("--external-num-seeds", type=int, default=ExtendedStrictEvalConfig.external_num_seeds)
    parser.add_argument("--top-k", type=int, nargs="+", default=list(DEFAULT_TOP_K))
    parser.add_argument("--train-epochs", type=int, default=ExtendedStrictEvalConfig.train_epochs)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_extended_strict_eval(
        ExtendedStrictEvalConfig(
            output_dir=args.output_dir,
            dataset_dir=args.dataset_dir,
            external_seed_start=args.external_seed_start,
            external_num_seeds=args.external_num_seeds,
            top_k=tuple(args.top_k),
            train_epochs=args.train_epochs,
        )
    )


if __name__ == "__main__":
    main()
