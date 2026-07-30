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

from active_replay_search_metrics import (
    active_replay_search_thresholds,
    load_active_replay_search_context,
)
from run_ieee118_active_label_replay import DEFAULT_DATASET
from train_ieee118_paper_aligned_gcn import predict_probability, split_metrics
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
)


DEFAULT_RUN_ROOT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase2_budget_curve"
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
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose dual-anchor score fusion using unchanged RTS-79 GCN "
            "checkpoints from active replay."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument(
        "--anchor-run-root",
        type=Path,
        default=None,
        help="Optional run root for the representative anchor model.",
    )
    parser.add_argument(
        "--active-run-root",
        type=Path,
        default=None,
        help="Optional run root for the target-focused active model.",
    )
    parser.add_argument("--anchor-method", default="random")
    parser.add_argument("--active-method", default="pmf_hybrid_prior_corrected")
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
    parser.add_argument("--k-gcn", type=int, default=6)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument(
        "--experiment-prefix",
        default="ieee118_phase2_dual_anchor",
        help="Prefix used for compact output filenames.",
    )
    parser.add_argument(
        "--research-stage",
        default="Phase 2 exploratory dual-anchor score fusion",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def fuse_probabilities(
    anchor_probability: np.ndarray,
    active_probability: np.ndarray,
    mode: str,
) -> np.ndarray:
    anchor = np.asarray(anchor_probability, dtype=float)
    active = np.asarray(active_probability, dtype=float)
    if anchor.shape != active.shape:
        raise ValueError("Anchor and active probabilities must have the same shape.")
    if mode == "anchor":
        return anchor.copy()
    if mode == "active":
        return active.copy()
    if mode == "mean":
        return 0.5 * (anchor + active)
    if mode == "geometric_mean":
        return np.sqrt(np.clip(anchor, 0.0, 1.0) * np.clip(active, 0.0, 1.0))
    raise ValueError(f"Unknown probability fusion mode: {mode}")


def _load_checkpoint(torch: Any, path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing active-replay model checkpoint: {path}. "
            "Dual-anchor evaluation will not retrain it."
        )
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:  # pragma: no cover
        return torch.load(path, map_location="cpu")


def _ensemble_predictions(
    checkpoint_path: Path,
    x_s0: np.ndarray,
    x_eval: np.ndarray,
    adjacency_powers: Any,
    symbols: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray]:
    torch = symbols["torch"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    checkpoint = _load_checkpoint(torch, checkpoint_path)
    states = checkpoint["member_states"]
    if not states:
        raise ValueError(f"Checkpoint contains no ensemble states: {checkpoint_path}")
    s0_members = []
    s1_members = []
    for member, state in enumerate(states):
        config = PaperGcnTrainConfig(
            epochs=1,
            batch_size=128,
            learning_rate=0.005,
            k_gcn=int(args.k_gcn),
            first_layer_channels=int(args.first_layer_channels),
            second_layer_channels=int(args.second_layer_channels),
            positive_weight=1.0,
            validation_fraction=0.0,
            random_seed=int(member),
        )
        model = PaperStyleRts79Gcn(
            input_channels=x_s0.shape[2],
            config=config,
        )
        model.load_state_dict(state)
        s0_members.append(
            predict_probability(model, x_s0, adjacency_powers, torch)[0]
        )
        s1_members.append(
            predict_probability(model, x_eval, adjacency_powers, torch)
        )
    return np.mean(s0_members, axis=0), np.mean(s1_members, axis=0)


def _local_replay_checkpoint(run_dir: Path) -> dict[str, np.ndarray]:
    path = run_dir / "active_label_replay_local_checkpoint.npz"
    if not path.exists():
        raise FileNotFoundError(f"Missing active-replay query mask/probabilities: {path}")
    checkpoint = np.load(path)
    return {
        "source_indices": checkpoint["subset_source_state_indices"].astype(np.int64),
        "query_mask": checkpoint["query_mask"].astype(bool),
        "probability": checkpoint["mean_probability"].astype(float),
    }


def _oracle_costs(
    anchor: dict[str, np.ndarray],
    active: dict[str, np.ndarray],
    full_split: np.ndarray,
) -> tuple[int, int, int]:
    if not np.array_equal(anchor["source_indices"], active["source_indices"]):
        raise ValueError("Dual-anchor local checkpoints use different state subsets.")
    if anchor["query_mask"].shape != active["query_mask"].shape:
        raise ValueError("Dual-anchor query masks do not have the same shape.")
    selected_split = full_split[anchor["source_indices"]]
    train_rows = selected_split == "train"
    anchor_mask = anchor["query_mask"]
    active_mask = active["query_mask"]
    return (
        int(anchor_mask[train_rows].sum()),
        int(active_mask[train_rows].sum()),
        int((anchor_mask | active_mask)[train_rows].sum()),
    )


def _single_oracle_cost(
    checkpoint: dict[str, np.ndarray],
    full_split: np.ndarray,
) -> int:
    source_indices = np.asarray(checkpoint["source_indices"], dtype=np.int64)
    query_mask = np.asarray(checkpoint["query_mask"], dtype=bool)
    if query_mask.ndim != 2 or query_mask.shape[0] != len(source_indices):
        raise ValueError(
            "Active-replay query mask rows must match its source indices."
        )
    if np.any(source_indices < 0) or np.any(source_indices >= len(full_split)):
        raise ValueError("Active-replay source indices are outside the full split.")
    train_rows = np.asarray(full_split).astype(str)[source_indices] == "train"
    return int(query_mask[train_rows].sum())


def _validation_s1_ap(
    dataset: Any,
    local: dict[str, np.ndarray],
) -> float:
    source_indices = local["source_indices"]
    selected_split = dataset["split"][source_indices].astype(str)
    selected_type = dataset["sample_type"][source_indices].astype(str)
    rows = (selected_split == "validation") & (selected_type == "S1")
    if not rows.any():
        raise ValueError("Dual-anchor validation requires at least one validation S1 state.")
    return float(
        split_metrics(
            dataset["y_gcn"][source_indices][rows],
            local["probability"][rows],
            dataset["loss_mask"][source_indices][rows],
        )["average_precision"]
    )


def _validation_fusion_ap(
    dataset: Any,
    anchor: dict[str, np.ndarray],
    active: dict[str, np.ndarray],
    mode: str,
) -> float:
    if not np.array_equal(anchor["source_indices"], active["source_indices"]):
        raise ValueError("Cannot fuse validation predictions from different state subsets.")
    fused = {
        **anchor,
        "probability": fuse_probabilities(
            anchor["probability"],
            active["probability"],
            mode,
        ),
    }
    return _validation_s1_ap(dataset, fused)


def evaluate_dual_anchor(args: argparse.Namespace) -> dict[str, Any]:
    if not args.dataset_npz.exists():
        raise FileNotFoundError(
            f"Missing local residual GCN dataset: {args.dataset_npz}. "
            "Dual-anchor evaluation will not regenerate it."
        )
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
    train_rows = split == "train"
    num_available = int(dataset["loss_mask"][train_rows].sum())
    records: list[dict[str, Any]] = []
    anchor_root = args.anchor_run_root or args.run_root
    active_root = args.active_run_root or args.run_root
    for acquisition_seed in args.acquisition_seeds:
        anchor_dir = anchor_root / f"{args.anchor_method}_seed_{acquisition_seed}"
        active_dir = active_root / f"{args.active_method}_seed_{acquisition_seed}"
        anchor_s0, anchor_s1 = _ensemble_predictions(
            anchor_dir / "active_label_replay_checkpoint.pt",
            x_s0,
            context.x_eval,
            adjacency_powers,
            symbols,
            args,
        )
        active_s0, active_s1 = _ensemble_predictions(
            active_dir / "active_label_replay_checkpoint.pt",
            x_s0,
            context.x_eval,
            adjacency_powers,
            symbols,
            args,
        )
        anchor_local = _local_replay_checkpoint(anchor_dir)
        active_local = _local_replay_checkpoint(active_dir)
        anchor_cost, active_cost, union_cost = _oracle_costs(
            anchor_local,
            active_local,
            split,
        )
        anchor_validation_ap = _validation_s1_ap(dataset, anchor_local)
        active_validation_ap = _validation_s1_ap(dataset, active_local)
        mean_validation_ap = _validation_fusion_ap(
            dataset,
            anchor_local,
            active_local,
            "mean",
        )
        geometric_validation_ap = _validation_fusion_ap(
            dataset,
            anchor_local,
            active_local,
            "geometric_mean",
        )
        variants = {
            "anchor_standalone": (
                anchor_s0,
                anchor_s1,
                anchor_cost,
                anchor_validation_ap,
            ),
            "active_standalone": (
                active_s0,
                active_s1,
                active_cost,
                active_validation_ap,
            ),
            "dual_anchor_active_second": (
                anchor_s0,
                active_s1,
                union_cost,
                active_validation_ap,
            ),
            "dual_anchor_mean_second": (
                anchor_s0,
                fuse_probabilities(anchor_s1, active_s1, "mean"),
                union_cost,
                mean_validation_ap,
            ),
            "dual_anchor_geometric_second": (
                anchor_s0,
                fuse_probabilities(anchor_s1, active_s1, "geometric_mean"),
                union_cost,
                geometric_validation_ap,
            ),
        }
        for method, (
            s0_probability,
            s1_probability,
            oracle_cost,
            validation_ap,
        ) in variants.items():
            records.append(
                {
                    "method": method,
                    "acquisition_seed": int(acquisition_seed),
                    "training_oracle_labels": oracle_cost,
                    "training_oracle_fraction": oracle_cost
                    / max(num_available, 1),
                    "validation_s1_average_precision": validation_ap,
                    **active_replay_search_thresholds(
                        context,
                        s0_probability=s0_probability,
                        s1_probability=s1_probability,
                    ),
                }
            )

    by_seed = pd.DataFrame(records).sort_values(
        ["method", "acquisition_seed"],
        kind="stable",
    )
    numeric = [
        name
        for name in by_seed.columns
        if name not in {"method", "acquisition_seed"}
    ]
    aggregate_rows = []
    for method, group in by_seed.groupby("method", sort=True):
        row: dict[str, Any] = {
            "method": str(method),
            "num_acquisition_seeds": int(group["acquisition_seed"].nunique()),
        }
        for name in numeric:
            values = pd.to_numeric(group[name], errors="coerce").dropna()
            row[f"{name}_mean"] = float(values.mean())
            row[f"{name}_std"] = float(values.std(ddof=0))
        aggregate_rows.append(row)
    aggregate = pd.DataFrame(aggregate_rows)
    fusion_methods = aggregate.loc[
        aggregate["method"].str.startswith("dual_anchor_")
    ]
    selected = fusion_methods.sort_values(
        ["validation_s1_average_precision_mean", "method"],
        ascending=[False, True],
    ).iloc[0]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    by_seed_name = f"{args.experiment_prefix}_by_seed.csv"
    aggregate_name = f"{args.experiment_prefix}_summary.csv"
    by_seed.to_csv(
        args.output_dir / by_seed_name,
        index=False,
        encoding="utf-8-sig",
    )
    aggregate.to_csv(
        args.output_dir / aggregate_name,
        index=False,
        encoding="utf-8-sig",
    )
    summary = {
        "status": "complete",
        "research_stage": str(args.research_stage),
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "anchor_method": args.anchor_method,
        "active_method": args.active_method,
        "anchor_run_root": str(anchor_root),
        "active_run_root": str(active_root),
        "num_acquisition_seeds": len(args.acquisition_seeds),
        "methods": aggregate.to_dict(orient="records"),
        "validation_selected_fusion": str(selected["method"]),
        "validation_selection_metric": "mean validation S1 average precision",
        "recommended_for_next_seed": selected.to_dict(),
        "formal_status": "freeze_then_confirm_on_independent_operating_scenarios",
        "cost_rule": (
            "Standalone methods count their own query mask. Dual methods count "
            "the union of anchor and active queried-label masks."
        ),
        "interpretation_limit": (
            "Fusion is selected by validation S1 AP, but the diagnostic was developed "
            "in a stage that also inspected the existing frozen test truth. Freeze the "
            "mean-fusion rule and confirm it on new operating scenarios before treating "
            "it as a formal generalization result."
        ),
        "output_files": {
            "by_seed": by_seed_name,
            "aggregate": aggregate_name,
        },
    }
    summary_name = f"{args.experiment_prefix}_summary.json"
    summary["output_files"]["summary"] = summary_name
    (args.output_dir / summary_name).write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    print(json.dumps(evaluate_dual_anchor(parse_args()), indent=2))


if __name__ == "__main__":
    main()
