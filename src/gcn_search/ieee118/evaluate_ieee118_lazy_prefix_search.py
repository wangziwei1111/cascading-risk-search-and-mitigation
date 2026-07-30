from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from active_replay_search_metrics import load_active_replay_search_context
from build_ieee118_dc_lodf_low_fidelity_targets import portable_result_path
from evaluate_ieee118_active_dual_anchor import (
    _ensemble_predictions,
    _local_replay_checkpoint,
    _oracle_costs,
    _single_oracle_cost,
    fuse_probabilities,
)
from run_ieee118_active_label_replay import DEFAULT_DATASET
from simulation_efficient_prefix_search import (
    adaptive_probe_then_promote_ordered_n2,
    evaluate_lazy_ranking,
    lazy_best_first_ordered_n2,
)
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
)


DEFAULT_RUN_ROOT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_pg_lure_curve"
)
DEFAULT_EVAL_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
)
DEFAULT_TRUTH_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
)
DEFAULT_NORMALIZER = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_feature_normalizer.json"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_lazy_prefix_search"
)
DEFAULT_STRICT_FRAGILITY = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_paper_aligned_training_scaleup"
    / "strict_fragility_targets"
    / "ieee118_strict_fragility_probabilities_compact.csv"
)
DEFAULT_LOW_FIDELITY = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_dc_lodf_low_fidelity"
    / "ieee118_dc_lodf_low_fidelity_targets.npz"
)
DEFAULT_ITERATIVE_PROXY = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_iterative_lodf_n1_proxy"
    / "ieee118_iterative_lodf_n1_proxy_deployment_scores.csv"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Retrospectively evaluate best-first IEEE118 ordered-prefix "
            "activation with unchanged RTS-79 GCN checkpoints."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--fallback-anchor-run-root",
        type=Path,
        default=None,
        help="Optional representative-label RTS-79 GCN checkpoint root.",
    )
    parser.add_argument(
        "--fallback-anchor-acquisition-mode",
        default="random",
    )
    parser.add_argument(
        "--fallback-score-fusion",
        choices=["none", "mean", "geometric_mean"],
        default="none",
    )
    parser.add_argument(
        "--acquisition-modes",
        nargs="+",
        default=["pg_lure", "pg_lure_unweighted"],
    )
    parser.add_argument(
        "--acquisition-seeds",
        type=int,
        nargs="+",
        default=[20260730, 20260731, 20260732, 20260733, 20260734],
    )
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
        default=DEFAULT_NORMALIZER,
    )
    parser.add_argument("--search-test-seed", type=int, default=20260708)
    parser.add_argument(
        "--first-prefix-score-mode",
        choices=[
            "s0_direct",
            "strict_fragility",
            "dc_lodf_proxy",
            "iterative_lodf_proxy",
        ],
        default="s0_direct",
    )
    parser.add_argument(
        "--strict-fragility-probabilities-csv",
        type=Path,
        default=DEFAULT_STRICT_FRAGILITY,
    )
    parser.add_argument(
        "--dc-lodf-low-fidelity-npz",
        type=Path,
        default=DEFAULT_LOW_FIDELITY,
    )
    parser.add_argument(
        "--iterative-lodf-proxy-scores-csv",
        type=Path,
        default=DEFAULT_ITERATIVE_PROXY,
    )
    parser.add_argument(
        "--dc-lodf-prefix-transform",
        choices=["raw", "rank"],
        default="raw",
    )
    parser.add_argument(
        "--second-score-physics-blend",
        type=float,
        default=0.0,
        help=(
            "Geometric blend between the conditional GCN score and the "
            "rank-normalized S0 DC/LODF line-risk prior."
        ),
    )
    parser.add_argument("--second-score-physics-gate-size", type=int, default=0)
    parser.add_argument("--physics-gate-floor", type=float, default=0.90)
    parser.add_argument("--prefix-rank-floor", type=float, default=0.0)
    parser.add_argument(
        "--adaptive-probes-per-second-line",
        type=int,
        default=0,
        help=(
            "When positive, query this many N-2 probes for each physics-gate "
            "second line before deciding which lines to expand."
        ),
    )
    parser.add_argument(
        "--adaptive-promotion-min-positives",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--adaptive-target",
        choices=["critical", "relay_cascade"],
        default="critical",
    )
    parser.add_argument(
        "--strict-fragility-target-name",
        default="max_shed_top30",
        help="Target frozen by validation AP before path-level test auditing.",
    )
    parser.add_argument("--k-gcn", type=int, default=6)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--topk-output-rows", type=int, default=500)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _curve_budgets(num_paths: int) -> list[int]:
    values = {
        50,
        100,
        200,
        500,
        1000,
        2000,
        5000,
        num_paths,
    }
    values.update(
        max(1, int(round(num_paths * ratio)))
        for ratio in (0.005, 0.01, 0.02, 0.05, 0.10)
    )
    values.update(range(250, min(5000, num_paths) + 1, 250))
    values.update(range(5500, num_paths + 1, 1000))
    return sorted(value for value in values if 0 < value <= num_paths)


def _threshold_row(
    ranked: pd.DataFrame,
    *,
    target_column: str,
    target_fraction: float,
) -> dict[str, int | float | None]:
    target = ranked[target_column].astype(bool).to_numpy()
    total = int(target.sum())
    required = int(np.ceil(total * float(target_fraction)))
    positions = np.flatnonzero(np.cumsum(target) >= required)
    if not len(positions):
        return {
            "target_total": total,
            "target_fraction": float(target_fraction),
            "candidate_evaluations": None,
            "n2_physical_verifications": None,
            "n1_state_constructions": None,
            "total_physical_evaluations": None,
        }
    row = ranked.iloc[int(positions[0])]
    return {
        "target_total": total,
        "target_fraction": float(target_fraction),
        "candidate_evaluations": int(row["rank"]),
        "n2_physical_verifications": int(row["n2_verifications_so_far"]),
        "n1_state_constructions": int(
            row["n1_state_constructions_so_far"]
        ),
        "total_physical_evaluations": int(
            row["total_physical_evaluations_so_far"]
        ),
    }


def _mean_std_table(
    table: pd.DataFrame,
    *,
    group_columns: list[str],
) -> pd.DataFrame:
    numeric = [
        column
        for column in table.select_dtypes(include=[np.number]).columns
        if column not in group_columns and column != "acquisition_seed"
    ]
    rows: list[dict[str, Any]] = []
    for keys, group in table.groupby(group_columns, sort=True, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row: dict[str, Any] = dict(zip(group_columns, keys))
        row["num_seeds"] = int(group["acquisition_seed"].nunique())
        for column in numeric:
            values = pd.to_numeric(group[column], errors="coerce")
            row[f"{column}_mean"] = float(values.mean())
            row[f"{column}_std"] = (
                float(values.std(ddof=1)) if values.notna().sum() > 1 else 0.0
            )
        rows.append(row)
    return pd.DataFrame(rows)


def rank_normalize_line_scores(
    score: np.ndarray,
    line_labels: np.ndarray,
) -> np.ndarray:
    values = np.asarray(score, dtype=np.float64)
    labels = np.asarray(line_labels, dtype=str)
    if values.shape != labels.shape:
        raise ValueError("Line scores and labels must align.")
    if np.any(~np.isfinite(values)):
        raise ValueError("Line scores must be finite for rank normalization.")
    order = np.lexsort((labels, -values))
    normalized = np.empty(len(values), dtype=np.float64)
    normalized[order] = (
        len(values) - np.arange(len(values), dtype=np.float64)
    ) / max(len(values), 1)
    return normalized


def apply_second_line_physics_gate(
    conditional: float,
    *,
    in_physics_gate: bool,
    physics_gate_floor: float,
    adaptive_feedback_enabled: bool,
) -> float:
    """Use a blanket gate only for the static, non-feedback baseline."""

    value = float(conditional)
    if adaptive_feedback_enabled:
        return value
    remaining_mass = 1.0 - float(physics_gate_floor)
    return (
        float(physics_gate_floor) + remaining_mass * value
        if in_physics_gate
        else remaining_mass * value
    )


def evaluate_lazy_prefix_search(args: argparse.Namespace) -> dict[str, Any]:
    if not 0.0 <= args.second_score_physics_blend <= 1.0:
        raise ValueError("--second-score-physics-blend must be in [0, 1].")
    if args.second_score_physics_gate_size < 0:
        raise ValueError("--second-score-physics-gate-size must be non-negative.")
    if not 0.0 <= args.physics_gate_floor < 1.0:
        raise ValueError("--physics-gate-floor must be in [0, 1).")
    if not 0.0 <= args.prefix_rank_floor < 1.0:
        raise ValueError("--prefix-rank-floor must be in [0, 1).")
    if args.adaptive_probes_per_second_line < 0:
        raise ValueError(
            "--adaptive-probes-per-second-line must be non-negative."
        )
    if args.adaptive_promotion_min_positives < 1:
        raise ValueError(
            "--adaptive-promotion-min-positives must be positive."
        )
    if (
        args.adaptive_probes_per_second_line > 0
        and args.adaptive_promotion_min_positives
        > args.adaptive_probes_per_second_line
    ):
        raise ValueError(
            "--adaptive-promotion-min-positives cannot exceed the probe count."
        )
    if (
        args.fallback_score_fusion != "none"
        and args.fallback_anchor_run_root is None
    ):
        raise ValueError(
            "A fallback score fusion requires --fallback-anchor-run-root."
        )
    for path, label in (
        (args.dataset_npz, "active-replay dataset"),
        (args.search_eval_dataset_npz, "176-state search dataset"),
        (args.search_fulltruth_csv, "early-stop full-truth CSV"),
        (args.search_first_step_summary_csv, "first-step summary CSV"),
        (args.search_feature_normalizer_json, "feature normalizer JSON"),
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing local {label}: {path}. Lazy-prefix evaluation "
                "will not regenerate large IEEE118 artifacts."
            )
    strict_first_scores: dict[str, float] | None = None
    dc_lodf_first_score: np.ndarray | None = None
    if args.first_prefix_score_mode == "strict_fragility":
        if not args.strict_fragility_probabilities_csv.exists():
            raise FileNotFoundError(
                "Missing local strict-fragility probabilities CSV: "
                f"{args.strict_fragility_probabilities_csv}. This evaluator "
                "will not retrain the first-prefix model."
            )
        strict = pd.read_csv(args.strict_fragility_probabilities_csv)
        required = {
            "seed",
            "target_name",
            "line_label",
            "q_strict_fragile",
        }
        missing = sorted(required - set(strict))
        if missing:
            raise ValueError(
                f"Strict-fragility probabilities are missing fields: {missing}"
            )
        selected = strict.loc[
            pd.to_numeric(strict["seed"], errors="coerce").eq(
                args.search_test_seed
            )
            & strict["target_name"].astype(str).eq(
                args.strict_fragility_target_name
            )
        ].copy()
        if selected["line_label"].astype(str).duplicated().any():
            raise ValueError(
                "Strict-fragility probabilities contain duplicate test lines."
            )
        strict_first_scores = dict(
            zip(
                selected["line_label"].astype(str),
                pd.to_numeric(
                    selected["q_strict_fragile"],
                    errors="raise",
                ).astype(float),
            )
        )
    elif args.first_prefix_score_mode == "dc_lodf_proxy":
        if not args.dc_lodf_low_fidelity_npz.exists():
            raise FileNotFoundError(
                "Missing local DC/LODF low-fidelity target NPZ: "
                f"{args.dc_lodf_low_fidelity_npz}. This evaluator will not "
                "regenerate cascade truth."
            )
    elif args.first_prefix_score_mode == "iterative_lodf_proxy":
        if not args.iterative_lodf_proxy_scores_csv.exists():
            raise FileNotFoundError(
                "Missing validation-frozen iterative LODF deployment scores: "
                f"{args.iterative_lodf_proxy_scores_csv}. This evaluator "
                "will not run high-fidelity N-1 cascades."
            )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dataset = np.load(args.dataset_npz, allow_pickle=True)
    line_labels = dataset["line_labels"].astype(str)
    context = load_active_replay_search_context(
        eval_dataset_npz=args.search_eval_dataset_npz,
        fulltruth_csv=args.search_fulltruth_csv,
        first_step_summary_csv=args.search_first_step_summary_csv,
        feature_normalizer_json=args.search_feature_normalizer_json,
        expected_line_labels=line_labels,
        expected_branch_from_bus=dataset["branch_from_bus"],
        expected_branch_to_bus=dataset["branch_to_bus"],
        test_seed=args.search_test_seed,
    )
    split = dataset["split"].astype(str)
    sample_type = dataset["sample_type"].astype(str)
    seed = dataset["seed"].astype(np.int64)
    s0_rows = np.where(
        (split == "test")
        & (sample_type == "S0")
        & (seed == int(args.search_test_seed))
    )[0]
    if len(s0_rows) != 1:
        raise ValueError(
            f"Expected one S0 test state for seed {args.search_test_seed}; "
            f"found {len(s0_rows)}."
        )
    if args.first_prefix_score_mode == "dc_lodf_proxy":
        low_fidelity = np.load(
            args.dc_lodf_low_fidelity_npz,
            allow_pickle=True,
        )
        required = {"proxy_score", "line_labels"}
        missing = sorted(required - set(low_fidelity.files))
        if missing:
            raise ValueError(
                f"DC/LODF low-fidelity NPZ is missing arrays: {missing}"
            )
        if low_fidelity["proxy_score"].shape[:2] != dataset["y_gcn"].shape:
            raise ValueError(
                "DC/LODF proxy shape does not match the active-replay dataset."
            )
        if not np.array_equal(
            low_fidelity["line_labels"].astype(str),
            line_labels,
        ):
            raise ValueError(
                "DC/LODF proxy line labels do not match the active-replay dataset."
            )
        dc_lodf_first_score = low_fidelity["proxy_score"][
            int(s0_rows[0])
        ].astype(np.float64)
        if not np.isfinite(dc_lodf_first_score).all():
            raise ValueError(
                "S0 DC/LODF proxy does not cover every IEEE118 line."
            )
        dc_lodf_rank_score = rank_normalize_line_scores(
            dc_lodf_first_score,
            line_labels,
        )
    elif args.first_prefix_score_mode == "iterative_lodf_proxy":
        iterative = pd.read_csv(args.iterative_lodf_proxy_scores_csv)
        required = {"seed", "line_label", "selected_proxy_score"}
        missing = sorted(required - set(iterative))
        if missing:
            raise ValueError(
                f"Iterative LODF deployment scores are missing fields: {missing}"
            )
        iterative = iterative.loc[
            pd.to_numeric(iterative["seed"], errors="coerce").eq(
                args.search_test_seed
            )
        ].copy()
        if iterative["line_label"].astype(str).duplicated().any():
            raise ValueError(
                "Iterative LODF deployment scores contain duplicate lines."
            )
        score_by_line = dict(
            zip(
                iterative["line_label"].astype(str),
                pd.to_numeric(
                    iterative["selected_proxy_score"],
                    errors="raise",
                ).astype(float),
            )
        )
        missing_lines = sorted(set(line_labels) - set(score_by_line))
        if missing_lines:
            raise ValueError(
                "Iterative LODF deployment scores do not cover lines: "
                f"{missing_lines[:10]}"
            )
        dc_lodf_first_score = np.asarray(
            [score_by_line[label] for label in line_labels],
            dtype=np.float64,
        )
        dc_lodf_rank_score = rank_normalize_line_scores(
            dc_lodf_first_score,
            line_labels,
        )
    else:
        dc_lodf_rank_score = None
    if (
        args.second_score_physics_gate_size > 0
        and dc_lodf_rank_score is None
    ):
        raise ValueError(
            "A physics gate requires a DC/LODF or iterative LODF prefix mode."
        )
    if args.second_score_physics_gate_size > len(line_labels):
        raise ValueError(
            "--second-score-physics-gate-size exceeds the line count."
        )
    physics_gate_line_order = (
        line_labels[
            np.argsort(-dc_lodf_rank_score, kind="stable")[
                : args.second_score_physics_gate_size
            ]
        ].tolist()
        if args.second_score_physics_gate_size > 0
        else []
    )
    physics_gate_lines = set(physics_gate_line_order)
    if args.adaptive_probes_per_second_line > 0 and not physics_gate_lines:
        raise ValueError(
            "Adaptive feedback probing requires a non-empty physics gate."
        )
    x_s0 = dataset["x_gcn"][s0_rows].astype(np.float32)
    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    adjacency = build_branch_graph_adjacency_from_endpoints(
        dataset["branch_from_bus"],
        dataset["branch_to_bus"],
    )
    adjacency_powers = torch.tensor(
        symbols["_build_adjacency_powers"](adjacency, int(args.k_gcn)),
        dtype=torch.float32,
    )
    line_index = {label: index for index, label in enumerate(line_labels)}
    state_index = {
        label: index for index, label in enumerate(context.first_lines)
    }
    truth_columns = [
        "path",
        "critical",
        "relay_cascade",
        "total_load_shed_mw",
    ]
    truth = context.truth[truth_columns].copy()
    num_first_lines = len(context.first_lines)
    num_paths = len(truth)
    expected_paths = num_first_lines * (len(line_labels) - 1)
    if num_paths != expected_paths:
        raise ValueError(
            f"Valid truth has {num_paths} paths; expected {expected_paths} "
            "from the available first-line states."
        )

    curve_parts = []
    threshold_rows: list[dict[str, Any]] = []
    top_parts = []
    run_rows: list[dict[str, Any]] = []
    budgets = _curve_budgets(num_paths)
    for mode in args.acquisition_modes:
        for acquisition_seed in args.acquisition_seeds:
            run_dir = args.run_root / f"{mode}_seed_{acquisition_seed}"
            checkpoint_path = run_dir / "active_label_replay_checkpoint.pt"
            s0_probability, s1_probability = _ensemble_predictions(
                checkpoint_path,
                x_s0,
                context.x_eval,
                adjacency_powers,
                symbols,
                args,
            )
            active_local_checkpoint = _local_replay_checkpoint(run_dir)
            anchor_oracle_labels = 0
            active_oracle_labels = _single_oracle_cost(
                active_local_checkpoint,
                split,
            )
            union_oracle_labels = active_oracle_labels
            if args.fallback_score_fusion != "none":
                anchor_run_dir = (
                    args.fallback_anchor_run_root
                    / (
                        f"{args.fallback_anchor_acquisition_mode}_seed_"
                        f"{acquisition_seed}"
                    )
                )
                anchor_s0, anchor_s1 = _ensemble_predictions(
                    anchor_run_dir / "active_label_replay_checkpoint.pt",
                    x_s0,
                    context.x_eval,
                    adjacency_powers,
                    symbols,
                    args,
                )
                s0_probability = fuse_probabilities(
                    anchor_s0,
                    s0_probability,
                    args.fallback_score_fusion,
                )
                s1_probability = fuse_probabilities(
                    anchor_s1,
                    s1_probability,
                    args.fallback_score_fusion,
                )
                (
                    anchor_oracle_labels,
                    active_oracle_labels,
                    union_oracle_labels,
                ) = _oracle_costs(
                    _local_replay_checkpoint(anchor_run_dir),
                    active_local_checkpoint,
                    split,
                )
            if dc_lodf_first_score is not None:
                selected_prefix_score = (
                    (
                        args.prefix_rank_floor
                        + (1.0 - args.prefix_rank_floor)
                        * dc_lodf_rank_score
                    )
                    if args.dc_lodf_prefix_transform == "rank"
                    else dc_lodf_first_score
                )
                first_scores = {
                    first_line: float(
                        selected_prefix_score[line_index[first_line]]
                    )
                    for first_line in context.first_lines
                }
            elif strict_first_scores is None:
                first_scores = {
                    first_line: float(s0_probability[line_index[first_line]])
                    for first_line in context.first_lines
                }
            else:
                missing_first = sorted(
                    set(context.first_lines) - set(strict_first_scores)
                )
                if missing_first:
                    raise ValueError(
                        "Strict-fragility probabilities do not cover valid "
                        f"first lines: {missing_first[:10]}"
                    )
                first_scores = {
                    first_line: strict_first_scores[first_line]
                    for first_line in context.first_lines
                }

            def second_provider(
                first_line: str,
                *,
                probabilities: np.ndarray = s1_probability,
            ) -> dict[str, float]:
                row = probabilities[state_index[first_line]]
                records = {}
                for label in line_labels:
                    if label == first_line:
                        continue
                    conditional = float(row[line_index[label]])
                    if (
                        dc_lodf_rank_score is not None
                        and args.second_score_physics_blend > 0.0
                    ):
                        physics_prior = float(
                            dc_lodf_rank_score[line_index[label]]
                        )
                        blend = float(args.second_score_physics_blend)
                        conditional = (
                            max(conditional, 1e-12) ** (1.0 - blend)
                            * max(physics_prior, 1e-12) ** blend
                        )
                    if physics_gate_lines:
                        conditional = apply_second_line_physics_gate(
                            conditional,
                            in_physics_gate=label in physics_gate_lines,
                            physics_gate_floor=float(args.physics_gate_floor),
                            adaptive_feedback_enabled=bool(
                                args.adaptive_probes_per_second_line > 0
                            ),
                        )
                    records[label] = conditional
                return records

            lazy = lazy_best_first_ordered_n2(
                first_line_scores=first_scores,
                line_labels=line_labels,
                second_score_provider=second_provider,
                max_candidates=num_paths,
                scenario_id=str(args.search_test_seed),
            )
            if args.adaptive_probes_per_second_line > 0:
                target_by_path = dict(
                    zip(
                        truth["path"].astype(str),
                        truth[args.adaptive_target].astype(bool),
                    )
                )
                adaptive = adaptive_probe_then_promote_ordered_n2(
                    first_line_scores=first_scores,
                    line_labels=line_labels,
                    fallback_ranking=lazy.ranking,
                    gate_second_lines=physics_gate_line_order,
                    outcome_oracle=lambda path: target_by_path[path],
                    state_builder=second_provider,
                    probes_per_second_line=(
                        args.adaptive_probes_per_second_line
                    ),
                    promotion_min_positives=(
                        args.adaptive_promotion_min_positives
                    ),
                    max_candidates=num_paths,
                    scenario_id=str(args.search_test_seed),
                )
                search_ranking = adaptive.ranking
                search_result = adaptive
                search_policy = "adaptive_probe_then_promote"
            else:
                search_ranking = lazy.ranking
                search_result = lazy
                search_policy = "static_lazy_best_first"
            ranked = search_ranking.merge(
                truth,
                on="path",
                how="left",
                validate="one_to_one",
            )
            if ranked["critical"].isna().any():
                raise ValueError("Lazy ranking contains paths absent from truth.")
            method = (
                f"RTS79_GCN_{mode}_lazy_prefix_"
                f"{args.first_prefix_score_mode}"
                f"_second_physics_{args.second_score_physics_blend:.2f}"
                f"_gate_{args.second_score_physics_gate_size}"
            )
            if args.adaptive_probes_per_second_line > 0:
                method += (
                    f"_adaptive_probe_{args.adaptive_probes_per_second_line}"
                    f"_min_{args.adaptive_promotion_min_positives}"
                    f"_{args.adaptive_target}"
                )
            if args.fallback_score_fusion != "none":
                method += (
                    f"_anchor_{args.fallback_anchor_acquisition_mode}"
                    f"_{args.fallback_score_fusion}"
                )
            curve = evaluate_lazy_ranking(
                search_ranking,
                truth,
                budgets,
                method=method,
            )
            curve.insert(1, "acquisition_mode", mode)
            curve.insert(2, "acquisition_seed", int(acquisition_seed))
            curve.insert(
                3,
                "first_prefix_score_mode",
                args.first_prefix_score_mode,
            )
            curve.insert(
                4,
                "second_score_physics_blend",
                float(args.second_score_physics_blend),
            )
            curve.insert(
                5,
                "second_score_physics_gate_size",
                int(args.second_score_physics_gate_size),
            )
            curve.insert(
                6,
                "search_policy",
                search_policy,
            )
            curve.insert(
                7,
                "adaptive_probes_per_second_line",
                int(args.adaptive_probes_per_second_line),
            )
            curve.insert(
                8,
                "adaptive_promotion_min_positives",
                int(args.adaptive_promotion_min_positives),
            )
            curve.insert(9, "adaptive_target", args.adaptive_target)
            curve.insert(
                10,
                "fallback_score_fusion",
                args.fallback_score_fusion,
            )
            curve["eager_n1_state_constructions"] = num_first_lines
            curve["saved_n1_state_constructions"] = (
                num_first_lines - curve["n1_state_constructions"]
            )
            curve_parts.append(curve)

            run_rows.append(
                {
                    "method": method,
                    "acquisition_mode": mode,
                    "acquisition_seed": int(acquisition_seed),
                    "first_prefix_score_mode": (
                        args.first_prefix_score_mode
                    ),
                    "dc_lodf_prefix_transform": (
                        args.dc_lodf_prefix_transform
                    ),
                    "second_score_physics_blend": float(
                        args.second_score_physics_blend
                    ),
                    "second_score_physics_gate_size": int(
                        args.second_score_physics_gate_size
                    ),
                    "search_policy": search_policy,
                    "adaptive_probes_per_second_line": int(
                        args.adaptive_probes_per_second_line
                    ),
                    "adaptive_promotion_min_positives": int(
                        args.adaptive_promotion_min_positives
                    ),
                    "adaptive_target": args.adaptive_target,
                    "fallback_score_fusion": args.fallback_score_fusion,
                    "fallback_anchor_acquisition_mode": (
                        args.fallback_anchor_acquisition_mode
                        if args.fallback_score_fusion != "none"
                        else None
                    ),
                    "anchor_training_oracle_labels": anchor_oracle_labels,
                    "active_training_oracle_labels": active_oracle_labels,
                    "union_training_oracle_labels": union_oracle_labels,
                    "promoted_second_lines": (
                        ";".join(adaptive.promoted_second_lines)
                        if args.adaptive_probes_per_second_line > 0
                        else ""
                    ),
                    "num_probe_paths": (
                        len(adaptive.probe_paths)
                        if args.adaptive_probes_per_second_line > 0
                        else 0
                    ),
                    "num_paths": num_paths,
                    "num_critical_paths": int(truth["critical"].sum()),
                    "num_relay_cascade_paths": int(
                        truth["relay_cascade"].sum()
                    ),
                    "eager_n1_state_constructions": num_first_lines,
                    "lazy_full_ranking_n1_state_constructions": (
                        search_result.num_activated_first_lines
                    ),
                }
            )
            for target_column, target_name in (
                ("critical", "critical"),
                ("relay_cascade", "relay_cascade"),
            ):
                for fraction in (0.90, 0.95, 0.99):
                    threshold_rows.append(
                        {
                            "method": method,
                            "acquisition_mode": mode,
                            "acquisition_seed": int(acquisition_seed),
                            "first_prefix_score_mode": (
                                args.first_prefix_score_mode
                            ),
                            "dc_lodf_prefix_transform": (
                                args.dc_lodf_prefix_transform
                            ),
                            "second_score_physics_blend": float(
                                args.second_score_physics_blend
                            ),
                            "second_score_physics_gate_size": int(
                                args.second_score_physics_gate_size
                            ),
                            "search_policy": search_policy,
                            "adaptive_probes_per_second_line": int(
                                args.adaptive_probes_per_second_line
                            ),
                            "adaptive_promotion_min_positives": int(
                                args.adaptive_promotion_min_positives
                            ),
                            "adaptive_target": args.adaptive_target,
                            "fallback_score_fusion": (
                                args.fallback_score_fusion
                            ),
                            "target": target_name,
                            **_threshold_row(
                                ranked,
                                target_column=target_column,
                                target_fraction=fraction,
                            ),
                            "eager_n1_state_constructions": num_first_lines,
                        }
                    )
            top = ranked.head(args.topk_output_rows).copy()
            top.insert(0, "method", method)
            top.insert(1, "acquisition_seed", int(acquisition_seed))
            top_parts.append(top)
            print(
                "[lazy-prefix] "
                f"mode={mode} seed={acquisition_seed} "
                f"first_score={args.first_prefix_score_mode} "
                f"top500_n1={int(ranked.iloc[min(499, len(ranked) - 1)]['n1_state_constructions_so_far'])} "
                f"full_n1={search_result.num_activated_first_lines} "
                f"policy={search_policy}",
                flush=True,
            )

    curve_raw = pd.concat(curve_parts, ignore_index=True)
    thresholds_raw = pd.DataFrame(threshold_rows)
    runs = pd.DataFrame(run_rows)
    curve_summary = _mean_std_table(
        curve_raw,
        group_columns=[
            "method",
            "acquisition_mode",
            "first_prefix_score_mode",
            "second_score_physics_blend",
            "second_score_physics_gate_size",
            "search_policy",
            "adaptive_probes_per_second_line",
            "adaptive_promotion_min_positives",
            "adaptive_target",
            "fallback_score_fusion",
            "candidate_evaluations",
        ],
    )
    threshold_summary = _mean_std_table(
        thresholds_raw,
        group_columns=[
            "method",
            "acquisition_mode",
            "first_prefix_score_mode",
            "second_score_physics_blend",
            "second_score_physics_gate_size",
            "search_policy",
            "adaptive_probes_per_second_line",
            "adaptive_promotion_min_positives",
            "adaptive_target",
            "fallback_score_fusion",
            "target",
            "target_fraction",
        ],
    )
    curve_raw.to_csv(
        args.output_dir / "ieee118_lazy_prefix_curve_points_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    curve_summary.to_csv(
        args.output_dir / "ieee118_lazy_prefix_curve_points.csv",
        index=False,
        encoding="utf-8-sig",
    )
    thresholds_raw.to_csv(
        args.output_dir / "ieee118_lazy_prefix_thresholds_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    threshold_summary.to_csv(
        args.output_dir / "ieee118_lazy_prefix_thresholds.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.concat(top_parts, ignore_index=True).to_csv(
        args.output_dir / "ieee118_lazy_prefix_topk_paths.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary = {
        "status": "complete",
        "research_stage": (
            "Phase 3 retrospective application experiment; prospective "
            "simulator callback timing remains future work"
        ),
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "num_valid_ordered_n2_paths": num_paths,
        "num_valid_first_line_states": num_first_lines,
        "num_critical_paths": int(truth["critical"].sum()),
        "num_relay_cascade_paths": int(truth["relay_cascade"].sum()),
        "first_prefix_score_mode": args.first_prefix_score_mode,
        "strict_fragility_target_name": (
            args.strict_fragility_target_name
            if args.first_prefix_score_mode == "strict_fragility"
            else None
        ),
        "dc_lodf_proxy_source": (
            portable_result_path(args.dc_lodf_low_fidelity_npz)
            if args.first_prefix_score_mode == "dc_lodf_proxy"
            else None
        ),
        "iterative_lodf_proxy_source": (
            portable_result_path(args.iterative_lodf_proxy_scores_csv)
            if args.first_prefix_score_mode == "iterative_lodf_proxy"
            else None
        ),
        "dc_lodf_prefix_transform": args.dc_lodf_prefix_transform,
        "second_score_physics_blend": float(
            args.second_score_physics_blend
        ),
        "second_score_physics_gate_size": int(
            args.second_score_physics_gate_size
        ),
        "physics_gate_floor": float(args.physics_gate_floor),
        "prefix_rank_floor": float(args.prefix_rank_floor),
        "physics_gate_lines": physics_gate_line_order,
        "search_policy": (
            "adaptive_probe_then_promote"
            if args.adaptive_probes_per_second_line > 0
            else "static_lazy_best_first"
        ),
        "adaptive_feedback": {
            "enabled": bool(args.adaptive_probes_per_second_line > 0),
            "probes_per_second_line": int(
                args.adaptive_probes_per_second_line
            ),
            "promotion_min_positives": int(
                args.adaptive_promotion_min_positives
            ),
            "target": args.adaptive_target,
            "hidden_truth_access": (
                "Only the selected path outcome is returned by the "
                "retrospective oracle callback after each N-2 verification."
            ),
        },
        "fallback_anchor": {
            "enabled": bool(args.fallback_score_fusion != "none"),
            "run_root": (
                portable_result_path(args.fallback_anchor_run_root)
                if args.fallback_anchor_run_root is not None
                else None
            ),
            "acquisition_mode": (
                args.fallback_anchor_acquisition_mode
                if args.fallback_score_fusion != "none"
                else None
            ),
            "score_fusion": args.fallback_score_fusion,
            "model_class": (
                "PaperStyleRts79Gcn"
                if args.fallback_score_fusion != "none"
                else None
            ),
        },
        "acquisition_modes": list(args.acquisition_modes),
        "acquisition_seeds": [int(value) for value in args.acquisition_seeds],
        "cost_accounting": {
            "n2_physical_verifications": (
                "Second-outage candidate cascade simulations only."
            ),
            "n1_state_constructions": (
                "First-outage S1 states activated by best-first expansion."
            ),
            "total_physical_evaluations": (
                "n2_physical_verifications + n1_state_constructions"
            ),
        },
        "algorithm": {
            "first_prefix_bound": args.first_prefix_score_mode,
            "exact_candidate_score": (
                "probe feedback promotion, then unchanged-GCN fallback"
                if args.adaptive_probes_per_second_line > 0
                else "first_prefix_score * p_shed_second"
            ),
            "bound_is_admissible": (
                "p_shed_second is in [0, 1] and first-prefix scores are "
                "non-negative"
            ),
            "cache_key": "(scenario_id, ordered_outage_prefix)",
        },
        "retrospective_caveat": (
            "This audit loads all precomputed S1 feature rows to obtain model "
            "scores, then replays which prefixes the best-first policy would "
            "activate. Adaptive runs reveal an outcome only when its selected "
            "path calls the oracle callback. This does not yet prove wall-clock "
            "savings in a live simulator."
        ),
        "strict_fragility_training_caveat": (
            "The optional strict-fragility head avoids deployment-time N-1 "
            "state construction, but its current offline training targets "
            "still come from existing path labels. A prospective "
            "active-query version remains required."
            if args.first_prefix_score_mode == "strict_fragility"
            else None
        ),
        "dc_lodf_proxy_caveat": (
            "The first-prefix proxy uses base DCOPF signs and DC LODF "
            "redistribution. It does not require an N-1 cascade call, but it "
            "does not model relay timing, island shedding, or redispatch."
            if args.first_prefix_score_mode == "dc_lodf_proxy"
            else None
        ),
        "iterative_lodf_proxy_caveat": (
            "The iterative proxy was selected by validation-seed N-1 AP and "
            "the deployment CSV contains no high-fidelity labels. It uses "
            "LODF relay updates but no island solve or redispatch."
            if args.first_prefix_score_mode == "iterative_lodf_proxy"
            else None
        ),
        "runs": runs.to_dict(orient="records"),
        "outputs": {
            "curve_points": "ieee118_lazy_prefix_curve_points.csv",
            "thresholds": "ieee118_lazy_prefix_thresholds.csv",
            "topk_paths": "ieee118_lazy_prefix_topk_paths.csv",
        },
    }
    (args.output_dir / "ieee118_lazy_prefix_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_lazy_prefix_readme.md").write_text(
        "# IEEE118 lazy ordered-prefix search\n\n"
        "This compact audit separates second-outage verification calls from "
        "on-demand first-outage S1 construction. Unopened first-line prefixes "
        "use `p_shed_first` as an admissible upper bound; an S1 state is "
        "activated only when that bound reaches the best-first queue head.\n\n"
        "When adaptive probing is enabled, a validation-frozen low-fidelity "
        "gate receives a small number of real N-2 probes. Only second lines "
        "confirmed by those queried outcomes are expanded before the original "
        "GCN fallback order. Unqueried full-truth labels are never read by the "
        "policy.\n\n"
        "The experiment is retrospective because the local evaluation dataset "
        "already contains every S1 feature row. The reported activation trace "
        "is suitable for policy comparison, but prospective simulator timing "
        "is still required before claiming operational speedup.\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    evaluate_lazy_prefix_search(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
