from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from run_pio_gcn_formal_small_experiment import FormalSmallExperimentConfig, run_formal_small_experiment


@dataclass(frozen=True)
class ExtendedFullTruthConfig:
    output_dir: str = "results/gcn_search/pio_extended_fulltruth_5seed"
    base_experiment_dir: str = "results/gcn_search/pio_formal_preliminary_3seed"
    test_seed_start: int = 20260722
    test_num_seeds: int = 5
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    training_num_scenarios: int = 10
    training_epochs: int = 5
    training_max_active_depth: int = 1
    candidate_line_filter_mode: str = "high_flow_top_n"
    max_first_lines: int | None = 10
    beta: float = 1.2
    security_limit: float = 1.0
    paper_baseline_model: str | None = None
    paper_baseline_normalizer: str | None = None
    run_full_truth: bool = True
    notes: str = "Extended RTS-79 full-truth preliminary experiment."


def run_extended_fulltruth_experiment(config: ExtendedFullTruthConfig) -> dict:
    if config.test_num_seeds < 5:
        raise ValueError("Extended full-truth experiment must use at least 5 seeds.")
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")

    base = Path(config.base_experiment_dir)
    _copy_base_training_artifacts(base, out)
    paper_model = config.paper_baseline_model
    paper_normalizer = config.paper_baseline_normalizer
    if not paper_model:
        candidate = Path("results/gcn_search/paper_baseline_strong/paper_train_ce_only/rts79_physics_gcn_model.pt")
        paper_model = str(candidate) if candidate.exists() else None
    if not paper_normalizer:
        candidate = Path("results/gcn_search/paper_baseline_strong/paper_dataset/rts79_step2_state_feature_normalizer.json")
        paper_normalizer = str(candidate) if candidate.exists() else None

    run_formal_small_experiment(
        FormalSmallExperimentConfig(
            output_dir=str(out),
            training_num_scenarios=config.training_num_scenarios,
            training_epochs=config.training_epochs,
            training_max_active_depth=config.training_max_active_depth,
            test_seed_start=config.test_seed_start,
            test_num_seeds=config.test_num_seeds,
            top_k=config.top_k,
            beta=config.beta,
            security_limit=config.security_limit,
            skip_training_if_exists=True,
            paper_baseline_model=paper_model,
            paper_baseline_normalizer=paper_normalizer,
            candidate_line_filter_mode=config.candidate_line_filter_mode,
            max_first_lines=config.max_first_lines,
        )
    )
    _copy_base_training_if_needed(base, out)
    legacy_truth_summary = out / "per_seed_full_truth_summary.csv"
    requested_truth_summary = out / "per_seed_fulltruth_summary.csv"
    if legacy_truth_summary.exists():
        requested_truth_summary.write_bytes(legacy_truth_summary.read_bytes())
    _write_extended_diagnostics(out, config)
    return {
        "output_dir": str(out),
        "aggregate_method_comparison": str(out / "aggregate_method_comparison.csv"),
        "aggregate_topk_summary": str(out / "aggregate_topk_summary.csv"),
    }


def _copy_base_training_if_needed(base: Path, out: Path) -> None:
    # Keep this function intentionally conservative. It does not copy models or NPZ files.
    for name in ("physics_training_metrics.csv", "physics_ce_training_metrics.csv", "training_dataset_stats.json"):
        src = base / name
        dst = out / name
        if src.exists() and not dst.exists():
            dst.write_bytes(src.read_bytes())


def _copy_base_training_artifacts(base: Path, out: Path) -> None:
    src = base / "training"
    dst = out / "training"
    if src.exists() and not dst.exists():
        shutil.copytree(src, dst)
    for name in ("physics_training_metrics.csv", "physics_ce_training_metrics.csv", "training_dataset_stats.json"):
        src_file = base / name
        dst_file = out / name
        if src_file.exists() and not dst_file.exists():
            dst_file.write_bytes(src_file.read_bytes())


def _write_extended_diagnostics(out: Path, config: ExtendedFullTruthConfig) -> None:
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    pio = pd.read_csv(out / "pio_topk_per_seed_summary.csv")
    baseline = pd.read_csv(out / "baseline_per_seed_summary.csv")
    truth = pd.read_csv(out / "per_seed_full_truth_summary.csv")
    rows: list[dict] = []
    for seed, group in pio.groupby("seed"):
        truth_row = truth.loc[truth["seed"] == seed].iloc[0].to_dict()
        row = {
            "seed": int(seed),
            "total_critical_paths": int(truth_row["total_critical_paths"]),
            "num_ordered_n2_paths": int(truth_row["num_ordered_n2_paths"]),
        }
        for _, item in group.iterrows():
            top_k = int(item["top_k"])
            row[f"pio_found_at_{top_k}"] = int(item["critical_found"])
            row[f"pio_recall_at_{top_k}"] = float(item["critical_path_recall"])
        rows.append(row)
    variability = pd.DataFrame(rows)
    variability.to_csv(diagnostics / "per_seed_variability.csv", index=False, encoding="utf-8-sig")

    key_col = f"pio_recall_at_{max(config.top_k)}"
    if key_col in variability.columns and not variability.empty:
        worst = variability.sort_values(key_col, ascending=True).head(1)
        best = variability.sort_values(key_col, ascending=False).head(1)
    else:
        worst = variability.head(1)
        best = variability.head(1)
    worst.to_csv(diagnostics / "worst_seed_summary.csv", index=False, encoding="utf-8-sig")
    best.to_csv(diagnostics / "best_seed_summary.csv", index=False, encoding="utf-8-sig")

    # Ensure a compact baseline summary is available for review.
    baseline.groupby("method", sort=False).agg(
        num_test_seeds=("seed", "nunique"),
        mean_runtime_seconds=("runtime_seconds", "mean"),
        notes=("notes", "first"),
    ).reset_index().to_csv(diagnostics / "baseline_runtime_summary.csv", index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run extended RTS-79 PIO-GCN full-truth evaluation.")
    parser.add_argument("--output-dir", default="results/gcn_search/pio_extended_fulltruth_5seed")
    parser.add_argument("--base-experiment-dir", default="results/gcn_search/pio_formal_preliminary_3seed")
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=5)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100, 200])
    parser.add_argument("--training-num-scenarios", type=int, default=10)
    parser.add_argument("--training-epochs", type=int, default=5)
    parser.add_argument("--training-max-active-depth", type=int, default=1)
    parser.add_argument("--candidate-line-filter-mode", choices=["all", "first_n", "high_flow_top_n"], default="high_flow_top_n")
    parser.add_argument("--max-first-lines", type=int, default=10)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--paper-baseline-model")
    parser.add_argument("--paper-baseline-normalizer")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_extended_fulltruth_experiment(
        ExtendedFullTruthConfig(
            output_dir=args.output_dir,
            base_experiment_dir=args.base_experiment_dir,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            training_num_scenarios=args.training_num_scenarios,
            training_epochs=args.training_epochs,
            training_max_active_depth=args.training_max_active_depth,
            candidate_line_filter_mode=args.candidate_line_filter_mode,
            max_first_lines=args.max_first_lines,
            beta=args.beta,
            security_limit=args.security_limit,
            paper_baseline_model=args.paper_baseline_model,
            paper_baseline_normalizer=args.paper_baseline_normalizer,
        )
    )


if __name__ == "__main__":
    main()
