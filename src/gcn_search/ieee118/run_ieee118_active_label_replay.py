from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from simulation_efficient_active_learning import (
    AcquisitionBatch,
    assert_no_label_leakage,
    binary_entropy,
    candidate_pairs,
    select_active_query_batch,
    select_initial_batch,
    select_quota_active_query_batch,
    select_random_batch,
    update_query_mask,
)
from risk_controlled_selective_verification import (
    calibrate_missed_positive_risk,
    missed_positive_fraction_by_unit,
    selected_for_physical_verification,
)
from active_replay_search_metrics import (
    active_replay_search_thresholds,
    load_active_replay_search_context,
)
from propensity_debiased_active_learning import (
    PropensityQueryBatch,
    effective_sample_size,
    lure_weight_matrix,
    physics_guided_lure_utility,
    sample_propensity_batch,
)
from dc_lodf_low_fidelity import binary_low_fidelity_target
from train_ieee118_paper_aligned_gcn import predict_probability, split_metrics
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
)


DEFAULT_DATASET = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_gcn_dataset.npz"
)
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_simulation_efficient_gcn" / "active_replay"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay sparse high-fidelity label acquisition with the unchanged RTS-79 PaperStyleRts79Gcn. "
            "Existing labels are hidden and exposed only through the query mask."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--acquisition-mode",
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
        default="pmf_bal",
    )
    parser.add_argument("--initial-labels", type=int, default=1000)
    parser.add_argument("--query-batch-size", type=int, default=1000)
    parser.add_argument("--rounds", type=int, default=3)
    budget_group = parser.add_mutually_exclusive_group()
    budget_group.add_argument(
        "--label-budgets",
        type=int,
        nargs="+",
        default=None,
        help="Exact cumulative queried-label budgets; overrides initial/batch/round scheduling.",
    )
    budget_group.add_argument(
        "--label-budget-fractions",
        type=float,
        nargs="+",
        default=None,
        help="Cumulative fractions of available training labels, for example 0.0025 0.005 0.01.",
    )
    parser.add_argument("--epochs-per-round", type=int, default=5)
    parser.add_argument("--ensemble-members", type=int, default=3)
    parser.add_argument("--physics-fraction", type=float, default=0.5)
    parser.add_argument("--initial-pool-multiplier", type=int, default=10)
    parser.add_argument("--shortlist-multiplier", type=int, default=10)
    parser.add_argument("--max-diversity-selections", type=int, default=500)
    parser.add_argument(
        "--lure-exploration-mass",
        type=float,
        default=0.50,
        help=(
            "Uniform proposal mass for randomized LURE modes. A positive value "
            "keeps support over every remaining training candidate."
        ),
    )
    parser.add_argument("--lure-utility-power", type=float, default=1.0)
    parser.add_argument(
        "--lure-loss-mix",
        type=float,
        default=0.50,
        help=(
            "For pg_lure_blend, fraction of LURE-corrected population risk; "
            "the remainder is the enriched active-sample risk."
        ),
    )
    parser.add_argument("--lure-uncertainty-weight", type=float, default=0.45)
    parser.add_argument("--lure-risk-weight", type=float, default=0.35)
    parser.add_argument("--lure-physics-weight", type=float, default=0.20)
    parser.add_argument(
        "--low-fidelity-target-npz",
        type=Path,
        default=None,
        help=(
            "Optional local DC/LODF proxy target file. It is used only for "
            "pretraining and never replaces high-fidelity evaluation labels."
        ),
    )
    parser.add_argument("--low-fidelity-pretrain-epochs", type=int, default=0)
    parser.add_argument(
        "--low-fidelity-target-mode",
        choices=["overload", "top_quantile", "per_state_top_quantile"],
        default="top_quantile",
    )
    parser.add_argument("--low-fidelity-overload-threshold", type=float, default=1.2)
    parser.add_argument("--low-fidelity-upper-quantile", type=float, default=0.95)
    parser.add_argument("--low-fidelity-positive-weight", type=float, default=5.0)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--positive-weight", type=float, default=20.0)
    parser.add_argument("--k-gcn", type=int, default=6)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--random-seed", type=int, default=20260730)
    parser.add_argument("--max-train-states", type=int, default=None)
    parser.add_argument("--max-validation-states", type=int, default=None)
    parser.add_argument("--max-test-states", type=int, default=None)
    parser.add_argument("--max-query-log-rows", type=int, default=500)
    parser.add_argument("--risk-alpha", type=float, default=0.05)
    parser.add_argument(
        "--reinitialize-each-round",
        action="store_true",
        help="Ablation: train each active round from random weights instead of warm-starting.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the local per-round torch checkpoint in the output directory.",
    )
    parser.add_argument(
        "--search-eval-dataset-npz",
        type=Path,
        default=None,
        help="Optional 176-state S1 dataset used only for formal path-ranking evaluation.",
    )
    parser.add_argument(
        "--search-fulltruth-csv",
        type=Path,
        default=None,
        help="Optional early-stop full-truth used only after inference to score rankings.",
    )
    parser.add_argument(
        "--search-first-step-summary-csv",
        type=Path,
        default=None,
        help="N-1 summary paired with --search-fulltruth-csv.",
    )
    parser.add_argument(
        "--search-feature-normalizer-json",
        type=Path,
        default=None,
        help="Training normalizer applied to raw features in the search evaluation dataset.",
    )
    parser.add_argument("--search-test-seed", type=int, default=20260708)
    return parser.parse_args(argv)


def require_dataset(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing local IEEE118 residual GCN dataset: {path}. "
            "Active replay will not regenerate exhaustive cascade labels."
        )


def _limited_split_indices(split: np.ndarray, name: str, maximum: int | None) -> np.ndarray:
    indices = np.where(split == name)[0]
    if maximum is None:
        return indices
    if maximum < 0:
        raise ValueError("Maximum state counts must be non-negative.")
    return indices[:maximum]


def _subset_indices(split: np.ndarray, args: argparse.Namespace) -> np.ndarray:
    selected = [
        _limited_split_indices(split, "train", args.max_train_states),
        _limited_split_indices(split, "validation", args.max_validation_states),
        _limited_split_indices(split, "test", args.max_test_states),
    ]
    indices = np.concatenate(selected)
    if len(indices) == 0:
        raise ValueError("State limits removed every train/validation/test state.")
    return indices.astype(np.int64)


def _validate_data(data: Any) -> None:
    required = {
        "x_gcn",
        "y_gcn",
        "loss_mask",
        "seed",
        "split",
        "sample_type",
        "active_first_line",
        "line_labels",
        "branch_from_bus",
        "branch_to_bus",
        "feature_names",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Active-replay dataset is missing arrays: {missing}")
    if data["x_gcn"].shape[:2] != data["y_gcn"].shape:
        raise ValueError("x_gcn and y_gcn state/line dimensions do not match.")
    if data["loss_mask"].shape != data["y_gcn"].shape:
        raise ValueError("loss_mask and y_gcn dimensions do not match.")
    assert_no_label_leakage(data["feature_names"].astype(str).tolist())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _input_content_digests(args: argparse.Namespace) -> dict[str, str | None]:
    paths = {
        "dataset_npz": args.dataset_npz,
        "low_fidelity_target_npz": args.low_fidelity_target_npz,
        "search_eval_dataset_npz": args.search_eval_dataset_npz,
        "search_fulltruth_csv": args.search_fulltruth_csv,
        "search_first_step_summary_csv": args.search_first_step_summary_csv,
        "search_feature_normalizer_json": args.search_feature_normalizer_json,
    }
    return {
        name: _file_sha256(Path(path)) if path is not None else None
        for name, path in paths.items()
    }


def sample_order_sha256(data: Any, original_indices: np.ndarray) -> str:
    required = ("seed", "split", "sample_type", "active_first_line")
    missing = [name for name in required if name not in data]
    if missing:
        raise ValueError(
            f"Cannot fingerprint sample order; missing identity arrays: {missing}"
        )
    indices = np.asarray(original_indices, dtype=np.int64)
    digest = hashlib.sha256()
    digest.update(indices.astype("<i8", copy=False).tobytes())
    for name in required:
        values = np.asarray(data[name])[indices].astype(str).reshape(-1)
        digest.update(name.encode("ascii"))
        digest.update(np.asarray(values.shape, dtype="<i8").tobytes())
        for value in values:
            encoded = value.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, byteorder="little"))
            digest.update(encoded)
    return digest.hexdigest()


def high_fidelity_data_cost_summary(
    query_mask: np.ndarray,
    valid_mask: np.ndarray,
    split: np.ndarray,
    *,
    policy_selection_label_count: int = 0,
    policy_selection_reuses_validation: bool = True,
    formal_search_audit_label_count: int = 0,
) -> dict[str, Any]:
    query = np.asarray(query_mask, dtype=bool)
    valid = np.asarray(valid_mask, dtype=bool)
    split_names = np.asarray(split).astype(str)
    if query.shape != valid.shape or query.shape[0] != len(split_names):
        raise ValueError("Query mask, valid mask, and split dimensions must match.")
    if policy_selection_label_count < 0:
        raise ValueError("Policy-selection label count must be non-negative.")
    if formal_search_audit_label_count < 0:
        raise ValueError("Formal search-audit label count must be non-negative.")

    train = valid & (split_names == "train")[:, None]
    validation = valid & (split_names == "validation")[:, None]
    test = valid & (split_names == "test")[:, None]
    training_available = int(train.sum())
    training_queried = int((query & train).sum())
    validation_labels = int(validation.sum())
    test_labels = int(test.sum())
    if policy_selection_reuses_validation and policy_selection_label_count > validation_labels:
        raise ValueError(
            "Policy-selection labels cannot exceed validation labels when they are reused."
        )
    additional_policy_labels = (
        0 if policy_selection_reuses_validation else int(policy_selection_label_count)
    )
    unique_development = (
        training_queried + validation_labels + additional_policy_labels
    )
    full_reference = (
        training_available + validation_labels + additional_policy_labels
    )
    return {
        "num_available_training_high_fidelity_labels": training_available,
        "num_training_query_labels": training_queried,
        "num_validation_model_selection_labels": validation_labels,
        "num_calibration_labels": validation_labels,
        "calibration_reuses_validation_labels": True,
        "num_policy_selection_labels": int(policy_selection_label_count),
        "policy_selection_reuses_validation_labels": bool(
            policy_selection_reuses_validation
        ),
        "num_unique_development_high_fidelity_labels": unique_development,
        "num_test_audit_labels": test_labels,
        "num_formal_search_audit_path_labels": int(
            formal_search_audit_label_count
        ),
        "test_audit_labels_excluded_from_development_cost": True,
        "formal_search_audit_labels_excluded_from_development_cost": True,
        "num_full_label_reference_development_labels": full_reference,
        "training_query_reduction_fraction": float(
            1.0 - training_queried / max(training_available, 1)
        ),
        "total_development_label_reduction_fraction": float(
            1.0 - unique_development / max(full_reference, 1)
        ),
    }


def _fit_one_model(
    x: np.ndarray,
    y: np.ndarray,
    query_mask: np.ndarray,
    valid_mask: np.ndarray,
    split: np.ndarray,
    adjacency_powers: Any,
    symbols: dict[str, Any],
    args: argparse.Namespace,
    *,
    member_seed: int,
    initial_state: dict[str, Any] | None = None,
    positive_weight_override: float | None = None,
    label_weight: np.ndarray | None = None,
    epochs_override: int | None = None,
) -> tuple[Any, list[dict[str, Any]]]:
    torch = symbols["torch"]
    nn = symbols["nn"]
    DataLoader = symbols["DataLoader"]
    TensorDataset = symbols["TensorDataset"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]

    train_rows = np.where((split == "train") & query_mask.any(axis=1))[0]
    validation_rows = np.where(split == "validation")[0]
    if len(train_rows) == 0:
        raise ValueError("No queried training labels are available.")
    if len(validation_rows) == 0:
        raise ValueError("Active replay requires a non-empty validation scenario split.")
    if label_weight is None:
        label_weight = query_mask.astype(np.float32)
    else:
        label_weight = np.asarray(label_weight, dtype=np.float32)
        if label_weight.shape != query_mask.shape:
            raise ValueError("label_weight must match the state-by-line query mask.")
        if np.any(label_weight < 0.0) or not np.isfinite(label_weight).all():
            raise ValueError("label_weight must be finite and non-negative.")
        if np.any(label_weight[query_mask] <= 0.0):
            raise ValueError("Every queried label must have positive training weight.")
    config = PaperGcnTrainConfig(
        epochs=int(
            args.epochs_per_round
            if epochs_override is None
            else epochs_override
        ),
        batch_size=int(args.batch_size),
        learning_rate=float(args.learning_rate),
        k_gcn=int(args.k_gcn),
        first_layer_channels=int(args.first_layer_channels),
        second_layer_channels=int(args.second_layer_channels),
        positive_weight=float(
            args.positive_weight
            if positive_weight_override is None
            else positive_weight_override
        ),
        validation_fraction=0.0,
        random_seed=int(member_seed),
    )
    torch.manual_seed(config.random_seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=config)
    if initial_state is not None:
        model.load_state_dict(initial_state)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loss_fn = nn.CrossEntropyLoss(
        weight=torch.tensor([1.0, config.positive_weight], dtype=torch.float32),
        reduction="none",
    )
    generator = torch.Generator().manual_seed(config.random_seed)
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_rows], dtype=torch.float32),
            torch.tensor(y[train_rows], dtype=torch.long),
            torch.tensor(query_mask[train_rows], dtype=torch.bool),
            torch.tensor(label_weight[train_rows], dtype=torch.float32),
        ),
        batch_size=config.batch_size,
        shuffle=True,
        generator=generator,
    )
    best_ap = float("-inf")
    best_state: dict[str, Any] | None = None
    log_rows: list[dict[str, Any]] = []
    if initial_state is not None:
        initial_probability = predict_probability(
            model,
            x[validation_rows],
            adjacency_powers,
            torch,
        )
        initial_metrics = split_metrics(
            y[validation_rows],
            initial_probability,
            valid_mask[validation_rows],
        )
        best_ap = float(initial_metrics["average_precision"])
        best_state = {
            name: value.detach().cpu().clone()
            for name, value in model.state_dict().items()
        }
        log_rows.append(
            {
                "member_seed": int(member_seed),
                "epoch": 0,
                "train_loss": float("nan"),
                "validation_average_precision": best_ap,
                "validation_recall_at_0_5": float(initial_metrics["recall"]),
                "warm_start_checkpoint": True,
            }
        )
    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        total_count = 0
        for xb, yb, mb, wb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            loss_matrix = loss_fn(logits.reshape(-1, 2), yb.reshape(-1)).reshape_as(yb)
            weighted_loss = loss_matrix[mb] * wb[mb]
            loss = weighted_loss.sum() / max(int(mb.sum()), 1)
            loss.backward()
            optimizer.step()
            count = int(mb.sum())
            total_loss += float(weighted_loss.detach().sum())
            total_count += count
        validation_probability = predict_probability(
            model,
            x[validation_rows],
            adjacency_powers,
            torch,
        )
        validation_metrics = split_metrics(
            y[validation_rows],
            validation_probability,
            valid_mask[validation_rows],
        )
        row = {
            "member_seed": int(member_seed),
            "epoch": int(epoch),
            "train_loss": total_loss / max(total_count, 1),
            "validation_average_precision": float(validation_metrics["average_precision"]),
            "validation_recall_at_0_5": float(validation_metrics["recall"]),
            "warm_start_checkpoint": False,
        }
        log_rows.append(row)
        if row["validation_average_precision"] > best_ap:
            best_ap = row["validation_average_precision"]
            best_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
    if best_state is None:
        raise RuntimeError("No active-replay checkpoint produced finite validation AP.")
    model.load_state_dict(best_state)
    return model, log_rows


def _top_entropy_batch(
    mean_probability: np.ndarray,
    valid_mask: np.ndarray,
    query_mask: np.ndarray,
    batch_size: int,
) -> np.ndarray:
    pairs = candidate_pairs(valid_mask, query_mask)
    if len(pairs) == 0 or batch_size <= 0:
        return np.empty((0, 2), dtype=np.int64)
    score = binary_entropy(mean_probability[pairs[:, 0], pairs[:, 1]])
    chosen = np.argsort(-score, kind="stable")[: min(int(batch_size), len(pairs))]
    return pairs[chosen]


def _physics_kcenter_batch(
    member_probability: np.ndarray,
    x: np.ndarray,
    valid_mask: np.ndarray,
    query_mask: np.ndarray,
    feature_names: np.ndarray,
    args: argparse.Namespace,
    batch_size: int,
) -> AcquisitionBatch:
    return select_active_query_batch(
        member_probability,
        x,
        valid_mask,
        query_mask,
        feature_names,
        batch_size,
        shortlist_multiplier=args.shortlist_multiplier,
        max_diversity_selections=args.max_diversity_selections,
        uncertainty_weight=0.0,
        severity_weight=1.0,
        positive_weight=0.0,
    )


def _retrieval_rows(
    y: np.ndarray,
    probability: np.ndarray,
    mask: np.ndarray,
    *,
    split_name: str,
) -> list[dict[str, Any]]:
    truth = y[mask].astype(bool)
    score = probability[mask].astype(float)
    if len(truth) == 0:
        return []
    order = np.argsort(-score, kind="stable")
    truth = truth[order]
    total_positive = int(truth.sum())
    rows: list[dict[str, Any]] = []
    budgets = sorted({min(k, len(truth)) for k in (50, 100, 200, 500, 1000, 2000, 5000)})
    for k in budgets:
        hits = int(truth[:k].sum())
        rows.append(
            {
                "split": split_name,
                "k": int(k),
                "critical_hits": hits,
                "critical_recall": hits / max(total_positive, 1),
                "precision_at_k": hits / max(k, 1),
                "budget_ratio": k / len(truth),
                "num_candidates": int(len(truth)),
                "num_critical": total_positive,
            }
        )
    return rows


def _append_query_log(
    rows: list[dict[str, Any]],
    batch: AcquisitionBatch | PropensityQueryBatch | np.ndarray,
    y: np.ndarray,
    original_indices: np.ndarray,
    line_labels: np.ndarray,
    *,
    query_round: int,
    mode: str,
    max_rows: int,
) -> None:
    if max_rows <= 0:
        return
    pairs = (
        batch.pairs()
        if isinstance(batch, (AcquisitionBatch, PropensityQueryBatch))
        else np.asarray(batch, dtype=np.int64)
    )
    score = (
        batch.acquisition_score
        if isinstance(batch, AcquisitionBatch)
        else (
            batch.acquisition_utility
            if isinstance(batch, PropensityQueryBatch)
            else np.full(len(pairs), np.nan)
        )
    )
    entropy = (
        batch.predictive_entropy
        if isinstance(batch, (AcquisitionBatch, PropensityQueryBatch))
        else np.full(len(pairs), np.nan)
    )
    disagreement = (
        batch.ensemble_disagreement
        if isinstance(batch, (AcquisitionBatch, PropensityQueryBatch))
        else np.full(len(pairs), np.nan)
    )
    severity = (
        batch.physics_severity
        if isinstance(batch, (AcquisitionBatch, PropensityQueryBatch))
        else np.full(len(pairs), np.nan)
    )
    proposal_probability = (
        batch.proposal_probability
        if isinstance(batch, PropensityQueryBatch)
        else np.full(len(pairs), np.nan)
    )
    limit = min(len(pairs), int(max_rows))
    pairs = pairs[:limit]
    score = score[:limit]
    entropy = entropy[:limit]
    disagreement = disagreement[:limit]
    severity = severity[:limit]
    proposal_probability = proposal_probability[:limit]
    for position, pair in enumerate(pairs):
        state_idx, line_idx = int(pair[0]), int(pair[1])
        rows.append(
            {
                "query_round": int(query_round),
                "acquisition_mode": mode,
                "subset_state_index": state_idx,
                "source_state_index": int(original_indices[state_idx]),
                "line_index": line_idx,
                "line_label": str(line_labels[line_idx]),
                "queried_label": int(y[state_idx, line_idx]),
                "acquisition_score": float(score[position]),
                "predictive_entropy": float(entropy[position]),
                "ensemble_disagreement": float(disagreement[position]),
                "physics_severity": float(severity[position]),
                "proposal_probability": float(proposal_probability[position]),
            }
        )


def _label_budget_schedule(
    args: argparse.Namespace,
    num_available_training_labels: int,
) -> list[int]:
    if args.label_budgets is not None:
        budgets = [int(value) for value in args.label_budgets]
    elif args.label_budget_fractions is not None:
        fractions = [float(value) for value in args.label_budget_fractions]
        if any(value <= 0.0 or value > 1.0 for value in fractions):
            raise ValueError("--label-budget-fractions values must be in (0, 1].")
        budgets = [
            max(1, int(round(value * num_available_training_labels)))
            for value in fractions
        ]
    else:
        budgets = [
            min(
                num_available_training_labels,
                int(args.initial_labels + active_round * args.query_batch_size),
            )
            for active_round in range(int(args.rounds))
        ]
        budgets = list(dict.fromkeys(budgets))
    if not budgets or any(value <= 0 for value in budgets):
        raise ValueError("The cumulative label-budget schedule must be non-empty and positive.")
    if budgets != sorted(set(budgets)):
        raise ValueError("Cumulative label budgets must be unique and strictly increasing.")
    if budgets[-1] > num_available_training_labels:
        raise ValueError(
            f"Label budget {budgets[-1]} exceeds the {num_available_training_labels} "
            "available training labels."
        )
    return budgets


def _prior_corrected_positive_weight(
    base_weight: float,
    reference_positive_prior: float,
    queried_positive_ratio: float,
) -> float:
    if base_weight <= 0.0:
        raise ValueError("Positive class weight must be positive.")
    if reference_positive_prior <= 0.0 or queried_positive_ratio <= 0.0:
        return float(base_weight)
    return float(
        np.clip(
            base_weight * reference_positive_prior / queried_positive_ratio,
            1.0,
            base_weight,
        )
    )


def _checkpoint_fingerprint(
    args: argparse.Namespace,
    original_indices: np.ndarray,
    budget_schedule: list[int],
    *,
    sample_order_digest: str,
    input_content_digests: dict[str, str | None] | None = None,
) -> str:
    content_digests = (
        _input_content_digests(args)
        if input_content_digests is None
        else dict(input_content_digests)
    )
    payload = {
        "dataset_npz": str(args.dataset_npz.resolve()),
        "input_content_sha256": content_digests,
        "subset_indices_sha256": hashlib.sha256(
            np.asarray(original_indices, dtype=np.int64).tobytes()
        ).hexdigest(),
        "subset_sample_order_sha256": str(sample_order_digest),
        "acquisition_mode": str(args.acquisition_mode),
        "label_budget_schedule": budget_schedule,
        "epochs_per_round": int(args.epochs_per_round),
        "ensemble_members": int(args.ensemble_members),
        "physics_fraction": float(args.physics_fraction),
        "initial_pool_multiplier": int(args.initial_pool_multiplier),
        "shortlist_multiplier": int(args.shortlist_multiplier),
        "max_diversity_selections": int(args.max_diversity_selections),
        "lure_exploration_mass": float(args.lure_exploration_mass),
        "lure_utility_power": float(args.lure_utility_power),
        "lure_loss_mix": float(args.lure_loss_mix),
        "lure_uncertainty_weight": float(args.lure_uncertainty_weight),
        "lure_risk_weight": float(args.lure_risk_weight),
        "lure_physics_weight": float(args.lure_physics_weight),
        "low_fidelity_target_npz": (
            str(args.low_fidelity_target_npz.resolve())
            if args.low_fidelity_target_npz is not None
            else None
        ),
        "low_fidelity_pretrain_epochs": int(args.low_fidelity_pretrain_epochs),
        "low_fidelity_target_mode": str(args.low_fidelity_target_mode),
        "low_fidelity_overload_threshold": float(
            args.low_fidelity_overload_threshold
        ),
        "low_fidelity_upper_quantile": float(
            args.low_fidelity_upper_quantile
        ),
        "low_fidelity_positive_weight": float(
            args.low_fidelity_positive_weight
        ),
        "batch_size": int(args.batch_size),
        "learning_rate": float(args.learning_rate),
        "positive_weight": float(args.positive_weight),
        "k_gcn": int(args.k_gcn),
        "first_layer_channels": int(args.first_layer_channels),
        "second_layer_channels": int(args.second_layer_channels),
        "random_seed": int(args.random_seed),
        "risk_alpha": float(args.risk_alpha),
        "reinitialize_each_round": bool(args.reinitialize_each_round),
        "search_eval_dataset_npz": (
            str(args.search_eval_dataset_npz.resolve())
            if args.search_eval_dataset_npz is not None
            else None
        ),
        "search_fulltruth_csv": (
            str(args.search_fulltruth_csv.resolve())
            if args.search_fulltruth_csv is not None
            else None
        ),
        "search_first_step_summary_csv": (
            str(args.search_first_step_summary_csv.resolve())
            if args.search_first_step_summary_csv is not None
            else None
        ),
        "search_feature_normalizer_json": (
            str(args.search_feature_normalizer_json.resolve())
            if args.search_feature_normalizer_json is not None
            else None
        ),
        "search_test_seed": int(args.search_test_seed),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_checkpoint(torch: Any, path: Path) -> dict[str, Any]:
    try:
        return torch.load(path, map_location="cpu", weights_only=False)
    except TypeError:  # pragma: no cover - compatibility with older torch.
        return torch.load(path, map_location="cpu")


def _save_checkpoint(
    torch: Any,
    path: Path,
    *,
    fingerprint: str,
    next_active_round: int,
    query_mask: np.ndarray,
    member_states: list[dict[str, Any] | None],
    round_rows: list[dict[str, Any]],
    training_log_rows: list[dict[str, Any]],
    retrieval_rows: list[dict[str, Any]],
    query_log_rows: list[dict[str, Any]],
    final_probability: np.ndarray,
    reference_positive_prior: float,
    acquisition_position: np.ndarray,
    acquisition_probability: np.ndarray,
) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "fingerprint": fingerprint,
            "next_active_round": int(next_active_round),
            "query_mask": np.asarray(query_mask, dtype=bool),
            "member_states": member_states,
            "round_rows": round_rows,
            "training_log_rows": training_log_rows,
            "retrieval_rows": retrieval_rows,
            "query_log_rows": query_log_rows,
            "final_probability": np.asarray(final_probability, dtype=np.float32),
            "reference_positive_prior": float(reference_positive_prior),
            "acquisition_position": np.asarray(
                acquisition_position,
                dtype=np.int64,
            ),
            "acquisition_probability": np.asarray(
                acquisition_probability,
                dtype=np.float64,
            ),
        },
        temporary,
    )
    temporary.replace(path)


def _load_low_fidelity_targets(
    path: Path,
    *,
    original_indices: np.ndarray,
    full_shape: tuple[int, int],
    expected_line_labels: np.ndarray,
    expected_seed: np.ndarray,
    expected_split: np.ndarray,
    expected_sample_type: np.ndarray,
    expected_active_first_line: np.ndarray,
    split: np.ndarray,
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing local IEEE118 low-fidelity target file: {path}. "
            "Run build_ieee118_dc_lodf_low_fidelity_targets.py first; "
            "active replay will not regenerate cascade truth."
        )
    low_fidelity = np.load(path, allow_pickle=True)
    required = {
        "proxy_score",
        "proxy_mask",
        "line_labels",
        "seed",
        "split",
        "sample_type",
        "active_first_line",
    }
    missing = sorted(required - set(low_fidelity.files))
    if missing:
        raise ValueError(
            f"Low-fidelity target NPZ is missing arrays: {missing}"
        )
    if low_fidelity["proxy_score"].shape != full_shape:
        raise ValueError(
            "Low-fidelity proxy score shape does not match the source GCN dataset."
        )
    if low_fidelity["proxy_mask"].shape != full_shape:
        raise ValueError(
            "Low-fidelity proxy mask shape does not match the source GCN dataset."
        )
    if not np.array_equal(
        low_fidelity["line_labels"].astype(str),
        expected_line_labels.astype(str),
    ):
        raise ValueError(
            "Low-fidelity line labels do not match the source GCN dataset."
        )
    expected_identity = {
        "seed": np.asarray(expected_seed),
        "split": np.asarray(expected_split).astype(str),
        "sample_type": np.asarray(expected_sample_type).astype(str),
        "active_first_line": np.asarray(expected_active_first_line).astype(str),
    }
    for name, expected in expected_identity.items():
        actual = np.asarray(low_fidelity[name])
        if actual.dtype.kind in {"U", "S", "O"}:
            actual = actual.astype(str)
        if not np.array_equal(actual, expected):
            raise ValueError(
                f"Low-fidelity {name} sample order does not match the source GCN dataset."
            )
    score = low_fidelity["proxy_score"][original_indices].astype(np.float32)
    mask = (
        low_fidelity["proxy_mask"][original_indices].astype(bool)
        & np.isfinite(score)
    )
    target, threshold = binary_low_fidelity_target(
        score,
        mask,
        split,
        mode=str(args.low_fidelity_target_mode),
        overload_threshold=float(args.low_fidelity_overload_threshold),
        upper_quantile=float(args.low_fidelity_upper_quantile),
    )
    train_mask = mask & (split == "train")[:, None]
    validation_mask = mask & (split == "validation")[:, None]
    metadata = {
        "target_npz": str(path),
        "target_mode": str(args.low_fidelity_target_mode),
        "frozen_training_proxy_threshold": float(threshold),
        "num_training_proxy_labels": int(train_mask.sum()),
        "num_training_proxy_positive": int(target[train_mask].sum()),
        "training_proxy_positive_ratio": float(target[train_mask].mean()),
        "num_validation_proxy_labels": int(validation_mask.sum()),
        "num_validation_proxy_positive": int(
            target[validation_mask].sum()
        ),
        "validation_proxy_positive_ratio": float(
            target[validation_mask].mean()
        ),
    }
    return target, mask, metadata


def replay(args: argparse.Namespace) -> dict[str, Any]:
    require_dataset(args.dataset_npz)
    if args.initial_labels <= 0:
        raise ValueError("--initial-labels must be positive.")
    if args.query_batch_size < 0:
        raise ValueError("--query-batch-size must be non-negative.")
    if args.rounds <= 0 or args.epochs_per_round <= 0 or args.ensemble_members <= 0:
        raise ValueError("rounds, epochs-per-round, and ensemble-members must be positive.")
    if not 0.0 < args.risk_alpha < 1.0:
        raise ValueError("--risk-alpha must be in (0, 1).")
    if args.positive_weight <= 0.0:
        raise ValueError("--positive-weight must be positive.")
    if args.max_query_log_rows < 0:
        raise ValueError("--max-query-log-rows must be non-negative.")
    if args.low_fidelity_pretrain_epochs < 0:
        raise ValueError("--low-fidelity-pretrain-epochs must be non-negative.")
    if args.low_fidelity_positive_weight <= 0.0:
        raise ValueError("--low-fidelity-positive-weight must be positive.")
    if args.low_fidelity_pretrain_epochs > 0 and args.low_fidelity_target_npz is None:
        raise ValueError(
            "--low-fidelity-pretrain-epochs requires "
            "--low-fidelity-target-npz."
        )
    if args.reinitialize_each_round and args.low_fidelity_pretrain_epochs > 0:
        raise ValueError(
            "Low-fidelity pretraining is incompatible with "
            "--reinitialize-each-round."
        )
    if not 0.0 < args.lure_exploration_mass <= 1.0:
        raise ValueError("--lure-exploration-mass must be in (0, 1].")
    if args.lure_utility_power <= 0.0:
        raise ValueError("--lure-utility-power must be positive.")
    if not 0.0 <= args.lure_loss_mix <= 1.0:
        raise ValueError("--lure-loss-mix must be in [0, 1].")
    lure_utility_weights = (
        args.lure_uncertainty_weight,
        args.lure_risk_weight,
        args.lure_physics_weight,
    )
    if min(lure_utility_weights) < 0.0 or sum(lure_utility_weights) <= 0.0:
        raise ValueError(
            "LURE utility weights must be non-negative with a positive sum."
        )
    lure_mode = args.acquisition_mode in {
        "lure_entropy",
        "pg_lure",
        "pg_lure_blend",
        "pg_lure_unweighted",
    }
    search_paths = (
        args.search_eval_dataset_npz,
        args.search_fulltruth_csv,
        args.search_first_step_summary_csv,
    )
    if any(path is not None for path in search_paths) and not all(
        path is not None for path in search_paths
    ):
        raise ValueError(
            "Formal search evaluation requires --search-eval-dataset-npz, "
            "--search-fulltruth-csv, and --search-first-step-summary-csv together."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.dataset_npz, allow_pickle=True)
    _validate_data(data)
    full_split = data["split"].astype(str)
    original_indices = _subset_indices(full_split, args)
    x = data["x_gcn"][original_indices].astype(np.float32)
    y = data["y_gcn"][original_indices].astype(np.int64)
    valid_mask = data["loss_mask"][original_indices].astype(bool)
    split = full_split[original_indices]
    sample_type = data["sample_type"][original_indices].astype(str)
    feature_names = data["feature_names"].astype(str)
    line_labels = data["line_labels"].astype(str)
    train_candidate_mask = valid_mask & (split == "train")[:, None]
    num_available_training_labels = int(train_candidate_mask.sum())
    if num_available_training_labels == 0:
        raise ValueError("Selected replay subset contains no valid training labels.")
    budget_schedule = _label_budget_schedule(
        args,
        num_available_training_labels,
    )
    low_fidelity_target = None
    low_fidelity_mask = None
    low_fidelity_metadata: dict[str, Any] = {
        "enabled": False,
        "pretrain_epochs": 0,
    }
    if args.low_fidelity_pretrain_epochs > 0:
        low_fidelity_target, low_fidelity_mask, loaded_metadata = (
            _load_low_fidelity_targets(
                args.low_fidelity_target_npz,
                original_indices=original_indices,
                full_shape=tuple(data["y_gcn"].shape),
                expected_line_labels=line_labels,
                expected_seed=data["seed"],
                expected_split=data["split"],
                expected_sample_type=data["sample_type"],
                expected_active_first_line=data["active_first_line"],
                split=split,
                args=args,
            )
        )
        low_fidelity_metadata = {
            "enabled": True,
            "pretrain_epochs": int(args.low_fidelity_pretrain_epochs),
            "positive_weight": float(args.low_fidelity_positive_weight),
            **loaded_metadata,
        }

    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]
    adjacency = build_branch_graph_adjacency_from_endpoints(
        data["branch_from_bus"],
        data["branch_to_bus"],
    )
    adjacency_powers = torch.tensor(
        build_adjacency_powers(adjacency, int(args.k_gcn)),
        dtype=torch.float32,
    )
    search_context = None
    if args.search_eval_dataset_npz is not None:
        search_context = load_active_replay_search_context(
            eval_dataset_npz=args.search_eval_dataset_npz,
            fulltruth_csv=args.search_fulltruth_csv,
            first_step_summary_csv=args.search_first_step_summary_csv,
            feature_normalizer_json=args.search_feature_normalizer_json,
            expected_line_labels=line_labels,
            expected_branch_from_bus=data["branch_from_bus"],
            expected_branch_to_bus=data["branch_to_bus"],
            test_seed=args.search_test_seed,
        )

    checkpoint_path = args.output_dir / "active_label_replay_checkpoint.pt"
    input_content_digests = _input_content_digests(args)
    subset_sample_order_digest = sample_order_sha256(data, original_indices)
    checkpoint_fingerprint = _checkpoint_fingerprint(
        args,
        original_indices,
        budget_schedule,
        sample_order_digest=subset_sample_order_digest,
        input_content_digests=input_content_digests,
    )
    query_mask = np.zeros_like(valid_mask, dtype=bool)
    acquisition_position = np.full(query_mask.shape, -1, dtype=np.int64)
    acquisition_probability = np.zeros(query_mask.shape, dtype=np.float64)
    round_rows: list[dict[str, Any]] = []
    training_log_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    query_log_rows: list[dict[str, Any]] = []
    final_probability = np.zeros_like(y, dtype=np.float32)
    member_states: list[dict[str, Any] | None] = [None] * int(args.ensemble_members)
    reference_positive_prior = 0.0
    start_active_round = 0
    resumed_from_checkpoint = False
    query_log_rows_per_round = (
        (int(args.max_query_log_rows) + len(budget_schedule) - 1)
        // len(budget_schedule)
    )
    if args.resume and checkpoint_path.exists():
        checkpoint = _load_checkpoint(torch, checkpoint_path)
        if checkpoint.get("fingerprint") != checkpoint_fingerprint:
            raise ValueError(
                "Active-label replay checkpoint configuration does not match this run. "
                "Use the original arguments or a different output directory."
            )
        query_mask = np.asarray(checkpoint["query_mask"], dtype=bool)
        if query_mask.shape != valid_mask.shape:
            raise ValueError("Active-label replay checkpoint query mask has the wrong shape.")
        if lure_mode:
            if not {
                "acquisition_position",
                "acquisition_probability",
            }.issubset(checkpoint):
                raise ValueError(
                    "LURE checkpoint is missing its recorded acquisition propensities."
                )
            acquisition_position = np.asarray(
                checkpoint["acquisition_position"],
                dtype=np.int64,
            )
            acquisition_probability = np.asarray(
                checkpoint["acquisition_probability"],
                dtype=np.float64,
            )
            if (
                acquisition_position.shape != valid_mask.shape
                or acquisition_probability.shape != valid_mask.shape
            ):
                raise ValueError("LURE checkpoint acquisition history has the wrong shape.")
        member_states = checkpoint["member_states"]
        round_rows = list(checkpoint["round_rows"])
        training_log_rows = list(checkpoint["training_log_rows"])
        retrieval_rows = list(checkpoint["retrieval_rows"])
        query_log_rows = list(checkpoint["query_log_rows"])
        final_probability = np.asarray(
            checkpoint["final_probability"],
            dtype=np.float32,
        )
        reference_positive_prior = float(
            checkpoint.get(
                "reference_positive_prior",
                y[query_mask & train_candidate_mask].sum()
                / max((query_mask & train_candidate_mask).sum(), 1),
            )
        )
        start_active_round = int(checkpoint["next_active_round"])
        if not 0 <= start_active_round <= len(budget_schedule):
            raise ValueError("Active-label replay checkpoint next round is out of range.")
        if len(member_states) != int(args.ensemble_members):
            raise ValueError("Active-label replay checkpoint has the wrong ensemble size.")
        resumed_from_checkpoint = True
        print(
            "[active-label-replay] "
            f"resumed next_round={start_active_round}/{len(budget_schedule)} "
            f"labels={int(query_mask[split == 'train'].sum())}",
            flush=True,
        )
    else:
        if low_fidelity_target is not None and low_fidelity_mask is not None:
            pretrain_query_mask = (
                low_fidelity_mask
                & (split == "train")[:, None]
            )
            pretrain_best_ap: list[float] = []
            for member in range(args.ensemble_members):
                member_seed = int(args.random_seed + member)
                model, logs = _fit_one_model(
                    x,
                    low_fidelity_target,
                    pretrain_query_mask,
                    low_fidelity_mask,
                    split,
                    adjacency_powers,
                    symbols,
                    args,
                    member_seed=member_seed,
                    positive_weight_override=float(
                        args.low_fidelity_positive_weight
                    ),
                    epochs_override=int(args.low_fidelity_pretrain_epochs),
                )
                member_states[member] = {
                    name: value.detach().cpu().clone()
                    for name, value in model.state_dict().items()
                }
                for row in logs:
                    row["active_round"] = -1
                    row["training_stage"] = "low_fidelity_pretrain"
                    training_log_rows.append(row)
                pretrain_best_ap.append(
                    max(
                        float(row["validation_average_precision"])
                        for row in logs
                    )
                )
            low_fidelity_metadata[
                "validation_proxy_ap_best_member_mean"
            ] = float(np.mean(pretrain_best_ap))
            print(
                "[active-label-replay] "
                f"low_fidelity_pretrain epochs={args.low_fidelity_pretrain_epochs} "
                f"threshold={low_fidelity_metadata['frozen_training_proxy_threshold']:.6f} "
                f"validation_proxy_ap={np.mean(pretrain_best_ap):.6f}",
                flush=True,
            )
        if lure_mode:
            initial_pairs = candidate_pairs(train_candidate_mask)
            initial = sample_propensity_batch(
                initial_pairs,
                np.ones(len(initial_pairs), dtype=np.float64),
                budget_schedule[0],
                exploration_mass=1.0,
                random_seed=args.random_seed,
            )
            initial_pair_values = initial.pairs()
            acquisition_position[
                initial_pair_values[:, 0],
                initial_pair_values[:, 1],
            ] = np.arange(initial.size, dtype=np.int64)
            acquisition_probability[
                initial_pair_values[:, 0],
                initial_pair_values[:, 1],
            ] = initial.proposal_probability
        elif args.acquisition_mode in {
            "random",
            "entropy",
            "pmf_quota",
            "pmf_hybrid",
            "pmf_hybrid_prior_corrected",
        }:
            initial = select_random_batch(
                train_candidate_mask,
                budget_schedule[0],
                random_seed=args.random_seed,
            )
        else:
            initial = select_initial_batch(
                x,
                train_candidate_mask,
                feature_names,
                budget_schedule[0],
                physics_fraction=args.physics_fraction,
                pool_multiplier=args.initial_pool_multiplier,
                max_diversity_selections=args.max_diversity_selections,
                random_seed=args.random_seed,
            )
        query_mask = update_query_mask(
            query_mask,
            initial.pairs() if isinstance(initial, PropensityQueryBatch) else initial,
        )
        _append_query_log(
            query_log_rows,
            initial,
            y,
            original_indices,
            line_labels,
            query_round=0,
            mode=f"{args.acquisition_mode}_initial",
            max_rows=query_log_rows_per_round,
        )
        initial_train_query = query_mask & train_candidate_mask
        reference_positive_prior = float(
            y[initial_train_query].sum() / max(initial_train_query.sum(), 1)
        )

    for active_round in range(start_active_round, len(budget_schedule)):
        target_budget = budget_schedule[active_round]
        current_budget = int(query_mask[split == "train"].sum())
        if current_budget != target_budget:
            raise RuntimeError(
                f"Active round {active_round} expected {target_budget} queried labels, "
                f"but query mask contains {current_budget}."
            )
        current_positive_ratio = float(
            y[query_mask & train_candidate_mask].sum() / max(current_budget, 1)
        )
        effective_positive_weight = float(args.positive_weight)
        if (
            args.acquisition_mode == "pmf_hybrid_prior_corrected"
        ):
            effective_positive_weight = _prior_corrected_positive_weight(
                args.positive_weight,
                reference_positive_prior,
                current_positive_ratio,
            )
        label_weight = None
        lure_weight = None
        if lure_mode:
            lure_weight = lure_weight_matrix(
                acquisition_position,
                acquisition_probability,
                pool_size=num_available_training_labels,
                num_acquired=current_budget,
            )
            lure_loss_mix = (
                0.0
                if args.acquisition_mode == "pg_lure_unweighted"
                else args.lure_loss_mix
                if args.acquisition_mode == "pg_lure_blend"
                else 1.0
            )
            if lure_loss_mix > 0.0:
                label_weight = (
                    lure_loss_mix * lure_weight
                    + (1.0 - lure_loss_mix) * query_mask.astype(np.float32)
                )
        member_probability: list[np.ndarray] = []
        member_eval_probability: list[np.ndarray] = []
        for member in range(args.ensemble_members):
            warm_state = (
                {
                    name: value.detach().cpu().clone()
                    for name, value in member_states[member].items()
                }
                if member_states[member] is not None
                and not args.reinitialize_each_round
                else None
            )
            member_seed = int(
                args.random_seed
                + member
                + (active_round * 1000 if args.reinitialize_each_round else 0)
            )
            model, logs = _fit_one_model(
                x,
                y,
                query_mask,
                valid_mask,
                split,
                adjacency_powers,
                symbols,
                args,
                member_seed=member_seed,
                initial_state=warm_state,
                positive_weight_override=effective_positive_weight,
                label_weight=label_weight,
            )
            member_states[member] = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
            for row in logs:
                row["active_round"] = int(active_round)
                row["training_stage"] = "high_fidelity_active"
                training_log_rows.append(row)
            member_probability.append(
                predict_probability(model, x, adjacency_powers, torch)
            )
            if search_context is not None:
                member_eval_probability.append(
                    predict_probability(
                        model,
                        search_context.x_eval,
                        adjacency_powers,
                        torch,
                    )
                )
        probability_stack = np.stack(member_probability)
        final_probability = probability_stack.mean(axis=0)
        train_rows = split == "train"
        validation_rows = split == "validation"
        test_rows = split == "test"
        queried_train_labels = int(query_mask[train_rows].sum())
        queried_positive = int(y[query_mask].sum())
        validation_metrics = split_metrics(
            y[validation_rows],
            final_probability[validation_rows],
            valid_mask[validation_rows],
        )
        test_metrics = (
            split_metrics(
                y[test_rows],
                final_probability[test_rows],
                valid_mask[test_rows],
            )
            if test_rows.any()
            else {}
        )
        calibration = calibrate_missed_positive_risk(
            final_probability[validation_rows],
            y[validation_rows],
            valid_mask[validation_rows],
            alpha=args.risk_alpha,
        )
        round_row = {
            "active_round": int(active_round),
            "queried_training_labels": queried_train_labels,
            "queried_training_label_fraction": queried_train_labels
            / max(num_available_training_labels, 1),
            "queried_positive_labels": queried_positive,
            "queried_positive_label_ratio": queried_positive
            / max(queried_train_labels, 1),
            "validation_average_precision": float(validation_metrics["average_precision"]),
            "validation_recall_at_0_5": float(validation_metrics["recall"]),
            "test_average_precision": float(test_metrics.get("average_precision", 0.0)),
            "test_recall_at_0_5": float(test_metrics.get("recall", 0.0)),
            "risk_alpha": float(args.risk_alpha),
            "risk_calibration_threshold": float(calibration.threshold),
            "risk_calibration_feasible": bool(calibration.feasible),
            "risk_calibration_upper_risk": float(calibration.crc_upper_risk),
            "reference_positive_prior": reference_positive_prior,
            "effective_positive_weight": effective_positive_weight,
        }
        if lure_weight is not None:
            selected_lure_weight = lure_weight[query_mask & train_candidate_mask]
            round_row.update(
                {
                    "lure_training_correction_enabled": (
                        lure_loss_mix > 0.0
                    ),
                    "lure_loss_mix": float(lure_loss_mix),
                    "lure_weight_min": float(selected_lure_weight.min()),
                    "lure_weight_mean": float(selected_lure_weight.mean()),
                    "lure_weight_max": float(selected_lure_weight.max()),
                    "lure_weight_effective_sample_size": effective_sample_size(
                        selected_lure_weight
                    ),
                    "lure_weight_effective_sample_fraction": (
                        effective_sample_size(selected_lure_weight)
                        / max(len(selected_lure_weight), 1)
                    ),
                }
            )
        for split_name, split_rows in (
            ("validation", validation_rows),
            ("test", test_rows),
        ):
            for state_type in ("S0", "S1"):
                typed_rows = split_rows & (sample_type == state_type)
                if typed_rows.any():
                    typed_metrics = split_metrics(
                        y[typed_rows],
                        final_probability[typed_rows],
                        valid_mask[typed_rows],
                    )
                    round_row[
                        f"{split_name}_{state_type.lower()}_average_precision"
                    ] = float(typed_metrics["average_precision"])
        if search_context is not None:
            s0_candidates = np.where(
                (split == "test")
                & (sample_type == "S0")
                & (data["seed"][original_indices].astype(np.int64) == args.search_test_seed)
            )[0]
            if len(s0_candidates) != 1:
                raise ValueError(
                    "Formal search evaluation requires exactly one S0 test state for "
                    f"seed {args.search_test_seed}; found {len(s0_candidates)}."
                )
            round_row.update(
                active_replay_search_thresholds(
                    search_context,
                    s0_probability=final_probability[int(s0_candidates[0])],
                    s1_probability=np.stack(member_eval_probability).mean(axis=0),
                )
            )
        if test_rows.any():
            test_selected = selected_for_physical_verification(
                final_probability[test_rows],
                valid_mask[test_rows],
                calibration,
            )
            test_truth = y[test_rows].astype(bool) & valid_mask[test_rows]
            test_positive = int(test_truth.sum())
            test_hit = int((test_truth & test_selected).sum())
            test_risk = missed_positive_fraction_by_unit(
                y[test_rows],
                test_selected,
                valid_mask[test_rows],
            )
            round_row.update(
                {
                    "test_verification_candidates": int(test_selected.sum()),
                    "test_verification_budget_ratio": float(
                        test_selected.sum() / max(valid_mask[test_rows].sum(), 1)
                    ),
                    "test_verification_positive_hits": test_hit,
                    "test_verification_positive_recall": float(
                        test_hit / max(test_positive, 1)
                    ),
                    "test_mean_missed_positive_fraction": float(test_risk.mean()),
                }
            )
        round_rows.append(round_row)
        retrieval_rows.extend(
            {
                **row,
                "active_round": int(active_round),
            }
            for row in _retrieval_rows(
                y[validation_rows],
                final_probability[validation_rows],
                valid_mask[validation_rows],
                split_name="validation",
            )
        )
        if test_rows.any():
            retrieval_rows.extend(
                {
                    **row,
                    "active_round": int(active_round),
                }
                for row in _retrieval_rows(
                    y[test_rows],
                    final_probability[test_rows],
                    valid_mask[test_rows],
                    split_name="test",
                )
            )
        print(
            "[active-label-replay] "
            f"round={active_round + 1}/{len(budget_schedule)} mode={args.acquisition_mode} "
            f"labels={queried_train_labels}/{num_available_training_labels} "
            f"positive={queried_positive} val_ap={validation_metrics['average_precision']:.6f} "
            f"test_ap={test_metrics.get('average_precision', 0.0):.6f}",
            flush=True,
        )
        if active_round + 1 < len(budget_schedule):
            next_batch_size = budget_schedule[active_round + 1] - queried_train_labels
            if lure_mode:
                remaining_pairs = candidate_pairs(
                    train_candidate_mask,
                    query_mask,
                )
                utility, entropy, disagreement, severity = (
                    physics_guided_lure_utility(
                        probability_stack,
                        x,
                        remaining_pairs,
                        feature_names,
                        mode=(
                            "entropy"
                            if args.acquisition_mode == "lure_entropy"
                            else "physics_guided"
                        ),
                        uncertainty_weight=args.lure_uncertainty_weight,
                        risk_weight=args.lure_risk_weight,
                        physics_weight=args.lure_physics_weight,
                    )
                )
                new_batch: AcquisitionBatch | PropensityQueryBatch | np.ndarray = (
                    sample_propensity_batch(
                        remaining_pairs,
                        utility,
                        next_batch_size,
                        exploration_mass=args.lure_exploration_mass,
                        random_seed=args.random_seed + active_round + 1,
                        utility_power=args.lure_utility_power,
                        predictive_entropy=entropy,
                        disagreement=disagreement,
                        physics_severity=severity,
                    )
                )
                new_pairs = new_batch.pairs()
                acquisition_position[
                    new_pairs[:, 0],
                    new_pairs[:, 1],
                ] = queried_train_labels + np.arange(
                    new_batch.size,
                    dtype=np.int64,
                )
                acquisition_probability[
                    new_pairs[:, 0],
                    new_pairs[:, 1],
                ] = new_batch.proposal_probability
            elif args.acquisition_mode == "random":
                new_batch = select_random_batch(
                    train_candidate_mask,
                    next_batch_size,
                    queried_mask=query_mask,
                    random_seed=args.random_seed + active_round + 1,
                )
            elif args.acquisition_mode == "entropy":
                new_batch = _top_entropy_batch(
                    final_probability,
                    train_candidate_mask,
                    query_mask,
                    next_batch_size,
                )
            elif args.acquisition_mode == "physics_kcenter":
                new_batch = _physics_kcenter_batch(
                    probability_stack,
                    x,
                    train_candidate_mask,
                    query_mask,
                    feature_names,
                    args,
                    next_batch_size,
                )
            elif args.acquisition_mode == "pmf_bal":
                new_batch = select_active_query_batch(
                    probability_stack,
                    x,
                    train_candidate_mask,
                    query_mask,
                    feature_names,
                    next_batch_size,
                    shortlist_multiplier=args.shortlist_multiplier,
                    max_diversity_selections=args.max_diversity_selections,
                )
            elif args.acquisition_mode == "pmf_quota":
                new_batch = select_quota_active_query_batch(
                    probability_stack,
                    x,
                    train_candidate_mask,
                    query_mask,
                    feature_names,
                    next_batch_size,
                    shortlist_multiplier=args.shortlist_multiplier,
                    max_diversity_selections=args.max_diversity_selections,
                )
            else:
                new_batch = select_quota_active_query_batch(
                    probability_stack,
                    x,
                    train_candidate_mask,
                    query_mask,
                    feature_names,
                    next_batch_size,
                    risk_fraction=0.15,
                    uncertainty_fraction=0.25,
                    random_fraction=0.50,
                    shortlist_multiplier=args.shortlist_multiplier,
                    max_diversity_selections=args.max_diversity_selections,
                    random_seed=args.random_seed + active_round + 1,
                )
            query_mask = update_query_mask(
                query_mask,
                new_batch.pairs()
                if isinstance(new_batch, PropensityQueryBatch)
                else new_batch,
            )
            _append_query_log(
                query_log_rows,
                new_batch,
                y,
                original_indices,
                line_labels,
                query_round=active_round + 1,
                mode=args.acquisition_mode,
                max_rows=query_log_rows_per_round,
            )
        _save_checkpoint(
            torch,
            checkpoint_path,
            fingerprint=checkpoint_fingerprint,
            next_active_round=active_round + 1,
            query_mask=query_mask,
            member_states=member_states,
            round_rows=round_rows,
            training_log_rows=training_log_rows,
            retrieval_rows=retrieval_rows,
            query_log_rows=query_log_rows,
            final_probability=final_probability,
            reference_positive_prior=reference_positive_prior,
            acquisition_position=acquisition_position,
            acquisition_probability=acquisition_probability,
        )

    round_table = pd.DataFrame(round_rows)
    training_log = pd.DataFrame(training_log_rows)
    retrieval_table = pd.DataFrame(retrieval_rows)
    query_log = pd.DataFrame(query_log_rows)
    round_table.to_csv(
        args.output_dir / "active_label_replay_round_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    training_log.to_csv(
        args.output_dir / "active_label_replay_training_log.csv",
        index=False,
        encoding="utf-8-sig",
    )
    retrieval_table.to_csv(
        args.output_dir / "active_label_replay_retrieval_metrics.csv",
        index=False,
        encoding="utf-8-sig",
    )
    query_log.head(args.max_query_log_rows).to_csv(
        args.output_dir / "active_label_replay_query_sample.csv",
        index=False,
        encoding="utf-8-sig",
    )
    np.savez_compressed(
        args.output_dir / "active_label_replay_local_checkpoint.npz",
        subset_source_state_indices=original_indices,
        query_mask=query_mask,
        mean_probability=final_probability,
        acquisition_position=acquisition_position,
        acquisition_probability=acquisition_probability,
    )

    final_round = round_rows[-1]
    best_round = max(
        round_rows,
        key=lambda row: float(row["validation_average_precision"]),
    )
    final_search = {
        name: value
        for name, value in final_round.items()
        if name.startswith("search_")
    }
    high_fidelity_costs = high_fidelity_data_cost_summary(
        query_mask,
        valid_mask,
        split,
        formal_search_audit_label_count=(
            len(search_context.truth) if search_context is not None else 0
        ),
    )
    summary = {
        "status": "complete",
        "research_stage": (
            "Phase 3 DC/LODF multi-fidelity active-label evaluation"
            if low_fidelity_metadata["enabled"]
            else "Phase 3 propensity-debiased retrospective search evaluation"
            if lure_mode
            else "Phase 2 retrospective label-efficiency and formal search evaluation"
            if search_context is not None
            else "Phase 1 retrospective hidden-label replay"
        ),
        "acquisition_mode": str(args.acquisition_mode),
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "model_core_modified": False,
        "hidden_outcome_labels_used_as_features": False,
        "low_fidelity_pretraining": low_fidelity_metadata,
        "dataset_npz": str(args.dataset_npz),
        "num_subset_states": int(len(x)),
        "num_train_states": int((split == "train").sum()),
        "num_validation_states": int((split == "validation").sum()),
        "num_test_states": int((split == "test").sum()),
        "num_available_training_oracle_labels": num_available_training_labels,
        "num_queried_training_oracle_labels": int(final_round["queried_training_labels"]),
        "queried_training_oracle_fraction": float(final_round["queried_training_label_fraction"]),
        "num_queried_positive_labels": int(final_round["queried_positive_labels"]),
        "high_fidelity_label_costs": high_fidelity_costs,
        "label_budget_schedule": budget_schedule,
        "resumed_from_checkpoint": resumed_from_checkpoint,
        "input_integrity": {
            "content_sha256": input_content_digests,
            "subset_sample_order_sha256": subset_sample_order_digest,
            "checkpoint_fingerprint": checkpoint_fingerprint,
        },
        "formal_search_evaluation_enabled": search_context is not None,
        "final_formal_search_thresholds": final_search,
        "final_validation_average_precision": float(final_round["validation_average_precision"]),
        "final_test_average_precision": float(final_round["test_average_precision"]),
        "best_active_round_by_validation_ap": int(best_round["active_round"]),
        "best_validation_average_precision": float(best_round["validation_average_precision"]),
        "test_average_precision_at_best_validation_round": float(
            best_round["test_average_precision"]
        ),
        "final_risk_control": {
            "alpha": float(final_round["risk_alpha"]),
            "calibration_threshold": float(final_round["risk_calibration_threshold"]),
            "calibration_feasible": bool(final_round["risk_calibration_feasible"]),
            "calibration_upper_risk": float(final_round["risk_calibration_upper_risk"]),
            "test_verification_candidates": int(
                final_round.get("test_verification_candidates", 0)
            ),
            "test_verification_budget_ratio": float(
                final_round.get("test_verification_budget_ratio", 0.0)
            ),
            "test_verification_positive_recall": float(
                final_round.get("test_verification_positive_recall", 0.0)
            ),
            "test_mean_missed_positive_fraction": float(
                final_round.get("test_mean_missed_positive_fraction", 0.0)
            ),
        },
        "train_config": {
            "epochs_per_round": int(args.epochs_per_round),
            "ensemble_members": int(args.ensemble_members),
            "batch_size": int(args.batch_size),
            "learning_rate": float(args.learning_rate),
            "positive_weight": float(args.positive_weight),
            "adaptive_prior_correction": (
                args.acquisition_mode == "pmf_hybrid_prior_corrected"
            ),
            "initial_pool_multiplier": int(args.initial_pool_multiplier),
            "shortlist_multiplier": int(args.shortlist_multiplier),
            "max_diversity_selections": int(args.max_diversity_selections),
            "lure_training_correction_enabled": (
                lure_mode
                and (
                    args.acquisition_mode != "pg_lure_unweighted"
                    and (
                        args.acquisition_mode != "pg_lure_blend"
                        or args.lure_loss_mix > 0.0
                    )
                )
            ),
            "lure_exploration_mass": float(args.lure_exploration_mass),
            "lure_utility_power": float(args.lure_utility_power),
            "lure_loss_mix": float(
                0.0
                if args.acquisition_mode == "pg_lure_unweighted"
                else args.lure_loss_mix
                if args.acquisition_mode == "pg_lure_blend"
                else 1.0
                if lure_mode
                else 0.0
            ),
            "lure_uncertainty_weight": float(args.lure_uncertainty_weight),
            "lure_risk_weight": float(args.lure_risk_weight),
            "lure_physics_weight": float(args.lure_physics_weight),
            "low_fidelity_pretraining_enabled": bool(
                low_fidelity_metadata["enabled"]
            ),
            "low_fidelity_pretrain_epochs": int(
                args.low_fidelity_pretrain_epochs
            ),
            "low_fidelity_target_mode": str(
                args.low_fidelity_target_mode
            ),
            "low_fidelity_positive_weight": float(
                args.low_fidelity_positive_weight
            ),
            "k_gcn": int(args.k_gcn),
            "first_layer_channels": int(args.first_layer_channels),
            "second_layer_channels": int(args.second_layer_channels),
            "random_seed": int(args.random_seed),
            "warm_start_between_rounds": not bool(args.reinitialize_each_round),
        },
        "phase_boundary": (
            "This replay estimates label efficiency using labels that were already generated in the past. "
            "The low-fidelity proxy uses no N-2 outcomes, but a prospective run "
            "must still call the physical cascade oracle only for selected "
            "high-fidelity candidates."
        ),
        "output_files": {
            "round_metrics": "active_label_replay_round_metrics.csv",
            "training_log": "active_label_replay_training_log.csv",
            "retrieval_metrics": "active_label_replay_retrieval_metrics.csv",
            "query_sample": "active_label_replay_query_sample.csv",
            "local_checkpoint_not_for_git": "active_label_replay_local_checkpoint.npz",
            "per_round_resume_checkpoint_not_for_git": "active_label_replay_checkpoint.pt",
        },
    }
    (args.output_dir / "active_label_replay_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "active_label_replay_readme.md").write_text(
        "# IEEE118 Active Label Replay\n\n"
        "This is a hidden-label retrospective experiment. It reuses the unchanged RTS-79 "
        "`PaperStyleRts79Gcn` and trains only on queried high-fidelity labels.\n\n"
        f"- Acquisition mode: `{args.acquisition_mode}`\n"
        f"- Queried labels: {summary['num_queried_training_oracle_labels']} / "
        f"{summary['num_available_training_oracle_labels']} "
        f"({100.0 * summary['queried_training_oracle_fraction']:.4f}%)\n"
        f"- Complete validation labels used for model selection/calibration: "
        f"{high_fidelity_costs['num_validation_model_selection_labels']}\n"
        f"- Unique development high-fidelity labels: "
        f"{high_fidelity_costs['num_unique_development_high_fidelity_labels']}\n"
        f"- Test labels used only for retrospective audit: "
        f"{high_fidelity_costs['num_test_audit_labels']}\n"
        f"- Formal path-ranking truth rows used only for retrospective audit: "
        f"{high_fidelity_costs['num_formal_search_audit_path_labels']}\n"
        f"- Validation AP: {summary['final_validation_average_precision']:.6f}\n"
        f"- Test AP: {summary['final_test_average_precision']:.6f}\n"
        f"- DC/LODF low-fidelity pretraining: "
        f"{'enabled' if low_fidelity_metadata['enabled'] else 'disabled'}\n\n"
        "This smoke/replay result is not yet evidence that a prospective physical-oracle run "
        "will achieve the same savings.\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    args = parse_args()
    print(json.dumps(replay(args), indent=2))


if __name__ == "__main__":
    main()
