from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from run_ieee118_active_label_replay import (
    DEFAULT_DATASET,
    parse_args as parse_replay_args,
    replay,
)
from summarize_ieee118_active_label_replay import summarize


DEFAULT_TRUTH_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
)
DEFAULT_EVAL_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
)
DEFAULT_RESIDUAL_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase2_multibudget"
)
PROPENSITY_MODES = {
    "lure_entropy",
    "pg_lure",
    "pg_lure_blend",
    "pg_lure_unweighted",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a resumable multi-budget, multi-seed IEEE118 hidden-label "
            "acquisition experiment with the unchanged RTS-79 GCN."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--acquisition-modes",
        nargs="+",
        choices=[
            "random",
            "entropy",
            "physics_kcenter",
            "pmf_bal",
            "pmf_quota",
            "pmf_hybrid",
            "pmf_hybrid_prior_corrected",
            "lure_entropy",
            "pg_lure",
            "pg_lure_blend",
            "pg_lure_unweighted",
        ],
        default=[
            "random",
            "entropy",
            "physics_kcenter",
            "pmf_bal",
            "pmf_quota",
            "pmf_hybrid",
            "pmf_hybrid_prior_corrected",
        ],
    )
    parser.add_argument("--acquisition-seeds", type=int, nargs="+", default=[20260730])
    parser.add_argument(
        "--label-budget-fractions",
        type=float,
        nargs="+",
        default=[0.0025, 0.005, 0.01],
    )
    parser.add_argument("--epochs-per-round", type=int, default=3)
    parser.add_argument("--ensemble-members", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--positive-weight", type=float, default=20.0)
    parser.add_argument("--k-gcn", type=int, default=6)
    parser.add_argument("--initial-pool-multiplier", type=int, default=10)
    parser.add_argument("--shortlist-multiplier", type=int, default=10)
    parser.add_argument("--max-diversity-selections", type=int, default=500)
    parser.add_argument("--lure-exploration-mass", type=float, default=0.50)
    parser.add_argument("--lure-utility-power", type=float, default=1.0)
    parser.add_argument("--lure-loss-mix", type=float, default=0.50)
    parser.add_argument("--lure-uncertainty-weight", type=float, default=0.45)
    parser.add_argument("--lure-risk-weight", type=float, default=0.35)
    parser.add_argument("--lure-physics-weight", type=float, default=0.20)
    parser.add_argument("--low-fidelity-target-npz", type=Path, default=None)
    parser.add_argument("--low-fidelity-pretrain-epochs", type=int, default=0)
    parser.add_argument(
        "--low-fidelity-target-mode",
        choices=["overload", "top_quantile", "per_state_top_quantile"],
        default="top_quantile",
    )
    parser.add_argument("--low-fidelity-overload-threshold", type=float, default=1.2)
    parser.add_argument("--low-fidelity-upper-quantile", type=float, default=0.95)
    parser.add_argument("--low-fidelity-positive-weight", type=float, default=5.0)
    parser.add_argument("--max-query-log-rows", type=int, default=500)
    parser.add_argument("--risk-alpha", type=float, default=0.05)
    parser.add_argument(
        "--search-eval-dataset-npz",
        type=Path,
        default=DEFAULT_EVAL_DIR / "ieee118_rts79_gcn_dataset.npz",
    )
    parser.add_argument(
        "--search-fulltruth-csv",
        type=Path,
        default=DEFAULT_TRUTH_DIR / "ieee118_fulltruth_summary.csv",
    )
    parser.add_argument(
        "--search-first-step-summary-csv",
        type=Path,
        default=DEFAULT_TRUTH_DIR / "ieee118_first_step_summary.csv",
    )
    parser.add_argument(
        "--search-feature-normalizer-json",
        type=Path,
        default=DEFAULT_RESIDUAL_DIR / "ieee118_residual_reachable_feature_normalizer.json",
    )
    parser.add_argument("--search-test-seed", type=int, default=20260708)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Optional debug limit on mode/seed combinations.",
    )
    return parser.parse_args(argv)


def _replay_arguments(
    args: argparse.Namespace,
    *,
    mode: str,
    seed: int,
    output_dir: Path,
) -> list[str]:
    values = [
        "--dataset-npz",
        str(args.dataset_npz),
        "--output-dir",
        str(output_dir),
        "--acquisition-mode",
        mode,
        "--label-budget-fractions",
        *[str(value) for value in args.label_budget_fractions],
        "--epochs-per-round",
        str(args.epochs_per_round),
        "--ensemble-members",
        str(args.ensemble_members),
        "--batch-size",
        str(args.batch_size),
        "--learning-rate",
        str(args.learning_rate),
        "--positive-weight",
        str(args.positive_weight),
        "--k-gcn",
        str(args.k_gcn),
        "--initial-pool-multiplier",
        str(args.initial_pool_multiplier),
        "--shortlist-multiplier",
        str(args.shortlist_multiplier),
        "--max-diversity-selections",
        str(args.max_diversity_selections),
        "--lure-exploration-mass",
        str(args.lure_exploration_mass),
        "--lure-utility-power",
        str(args.lure_utility_power),
        "--lure-loss-mix",
        str(args.lure_loss_mix),
        "--lure-uncertainty-weight",
        str(args.lure_uncertainty_weight),
        "--lure-risk-weight",
        str(args.lure_risk_weight),
        "--lure-physics-weight",
        str(args.lure_physics_weight),
        "--low-fidelity-pretrain-epochs",
        str(args.low_fidelity_pretrain_epochs),
        "--low-fidelity-target-mode",
        str(args.low_fidelity_target_mode),
        "--low-fidelity-overload-threshold",
        str(args.low_fidelity_overload_threshold),
        "--low-fidelity-upper-quantile",
        str(args.low_fidelity_upper_quantile),
        "--low-fidelity-positive-weight",
        str(args.low_fidelity_positive_weight),
        "--max-query-log-rows",
        str(args.max_query_log_rows),
        "--risk-alpha",
        str(args.risk_alpha),
        "--random-seed",
        str(seed),
        "--search-eval-dataset-npz",
        str(args.search_eval_dataset_npz),
        "--search-fulltruth-csv",
        str(args.search_fulltruth_csv),
        "--search-first-step-summary-csv",
        str(args.search_first_step_summary_csv),
        "--search-feature-normalizer-json",
        str(args.search_feature_normalizer_json),
        "--search-test-seed",
        str(args.search_test_seed),
    ]
    if args.low_fidelity_target_npz is not None:
        values.extend(
            [
                "--low-fidelity-target-npz",
                str(args.low_fidelity_target_npz),
            ]
        )
    if args.resume:
        values.append("--resume")
    return values


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_runs is not None and args.max_runs <= 0:
        raise ValueError("--max-runs must be positive when supplied.")
    combinations = [
        (mode, seed)
        for mode in args.acquisition_modes
        for seed in args.acquisition_seeds
    ]
    if args.max_runs is not None:
        combinations = combinations[: args.max_runs]
    if not combinations:
        raise ValueError("No acquisition mode/seed combinations were requested.")
    args.output_root.mkdir(parents=True, exist_ok=True)
    completed: list[dict[str, Any]] = []
    for position, (mode, seed) in enumerate(combinations, start=1):
        run_dir = args.output_root / f"{mode}_seed_{seed}"
        print(
            f"[label-efficiency] run={position}/{len(combinations)} "
            f"mode={mode} seed={seed}",
            flush=True,
        )
        result = replay(
            parse_replay_args(
                _replay_arguments(
                    args,
                    mode=mode,
                    seed=seed,
                    output_dir=run_dir,
                )
            )
        )
        completed.append(
            {
                "mode": mode,
                "seed": int(seed),
                "output_dir": str(run_dir),
                "status": result["status"],
            }
        )

    aggregate_dir = args.output_root / "compact"
    comparison = summarize(args.output_root, aggregate_dir, run_glob="*_seed_*")
    manifest = {
        "status": "complete",
        "research_stage": (
            "Phase 3 DC/LODF multi-fidelity active-label experiment"
            if args.low_fidelity_pretrain_epochs > 0
            else "Phase 3 propensity-aware retrospective label-efficiency experiment"
            if any(mode in PROPENSITY_MODES for mode, _ in combinations)
            else "Phase 2 retrospective multi-budget label-efficiency experiment"
        ),
        "dataset_npz": str(args.dataset_npz),
        "label_budget_fractions": [float(value) for value in args.label_budget_fractions],
        "num_runs": len(completed),
        "runs": completed,
        "comparison": comparison,
        "interpretation_limit": (
            "This is retrospective hidden-label replay. Prospective savings require "
            "calling the high-fidelity physical oracle only for selected labels."
        ),
    }
    (aggregate_dir / "ieee118_label_efficiency_experiment_manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    print(json.dumps(run_experiment(parse_args()), indent=2))


if __name__ == "__main__":
    main()
