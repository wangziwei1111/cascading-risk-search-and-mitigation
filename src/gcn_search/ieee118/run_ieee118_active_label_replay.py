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

from simulation_efficient_active_learning import (
    AcquisitionBatch,
    assert_no_label_leakage,
    binary_entropy,
    candidate_pairs,
    select_active_query_batch,
    select_initial_batch,
    select_random_batch,
    update_query_mask,
)
from risk_controlled_selective_verification import (
    calibrate_missed_positive_risk,
    missed_positive_fraction_by_unit,
    selected_for_physical_verification,
)
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
        choices=["random", "entropy", "physics_kcenter", "pmf_bal"],
        default="pmf_bal",
    )
    parser.add_argument("--initial-labels", type=int, default=1000)
    parser.add_argument("--query-batch-size", type=int, default=1000)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--epochs-per-round", type=int, default=5)
    parser.add_argument("--ensemble-members", type=int, default=3)
    parser.add_argument("--physics-fraction", type=float, default=0.5)
    parser.add_argument("--initial-pool-multiplier", type=int, default=10)
    parser.add_argument("--shortlist-multiplier", type=int, default=10)
    parser.add_argument("--max-diversity-selections", type=int, default=500)
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
        "split",
        "sample_type",
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
    config = PaperGcnTrainConfig(
        epochs=int(args.epochs_per_round),
        batch_size=int(args.batch_size),
        learning_rate=float(args.learning_rate),
        k_gcn=int(args.k_gcn),
        first_layer_channels=int(args.first_layer_channels),
        second_layer_channels=int(args.second_layer_channels),
        positive_weight=float(args.positive_weight),
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
        for xb, yb, mb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            loss_matrix = loss_fn(logits.reshape(-1, 2), yb.reshape(-1)).reshape_as(yb)
            loss = loss_matrix[mb].mean()
            loss.backward()
            optimizer.step()
            count = int(mb.sum())
            total_loss += float(loss.detach()) * count
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
) -> AcquisitionBatch:
    return select_active_query_batch(
        member_probability,
        x,
        valid_mask,
        query_mask,
        feature_names,
        args.query_batch_size,
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
    batch: AcquisitionBatch | np.ndarray,
    y: np.ndarray,
    original_indices: np.ndarray,
    line_labels: np.ndarray,
    *,
    query_round: int,
    mode: str,
) -> None:
    pairs = batch.pairs() if isinstance(batch, AcquisitionBatch) else np.asarray(batch, dtype=np.int64)
    score = (
        batch.acquisition_score
        if isinstance(batch, AcquisitionBatch)
        else np.full(len(pairs), np.nan)
    )
    entropy = (
        batch.predictive_entropy
        if isinstance(batch, AcquisitionBatch)
        else np.full(len(pairs), np.nan)
    )
    disagreement = (
        batch.ensemble_disagreement
        if isinstance(batch, AcquisitionBatch)
        else np.full(len(pairs), np.nan)
    )
    severity = (
        batch.physics_severity
        if isinstance(batch, AcquisitionBatch)
        else np.full(len(pairs), np.nan)
    )
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
            }
        )


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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.dataset_npz, allow_pickle=True)
    _validate_data(data)
    full_split = data["split"].astype(str)
    original_indices = _subset_indices(full_split, args)
    x = data["x_gcn"][original_indices].astype(np.float32)
    y = data["y_gcn"][original_indices].astype(np.int64)
    valid_mask = data["loss_mask"][original_indices].astype(bool)
    split = full_split[original_indices]
    feature_names = data["feature_names"].astype(str)
    line_labels = data["line_labels"].astype(str)
    train_candidate_mask = valid_mask & (split == "train")[:, None]
    num_available_training_labels = int(train_candidate_mask.sum())
    if num_available_training_labels == 0:
        raise ValueError("Selected replay subset contains no valid training labels.")

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

    query_mask = np.zeros_like(valid_mask, dtype=bool)
    if args.acquisition_mode in {"random", "entropy"}:
        initial = select_random_batch(
            train_candidate_mask,
            args.initial_labels,
            random_seed=args.random_seed,
        )
    else:
        initial = select_initial_batch(
            x,
            train_candidate_mask,
            feature_names,
            args.initial_labels,
            physics_fraction=args.physics_fraction,
            pool_multiplier=args.initial_pool_multiplier,
            max_diversity_selections=args.max_diversity_selections,
            random_seed=args.random_seed,
        )
    query_mask = update_query_mask(query_mask, initial)
    query_log_rows: list[dict[str, Any]] = []
    _append_query_log(
        query_log_rows,
        initial,
        y,
        original_indices,
        line_labels,
        query_round=0,
        mode=f"{args.acquisition_mode}_initial",
    )

    round_rows: list[dict[str, Any]] = []
    training_log_rows: list[dict[str, Any]] = []
    retrieval_rows: list[dict[str, Any]] = []
    final_probability = np.zeros_like(y, dtype=np.float32)
    member_models: list[Any | None] = [None] * int(args.ensemble_members)
    for active_round in range(args.rounds):
        member_probability: list[np.ndarray] = []
        for member in range(args.ensemble_members):
            warm_model = member_models[member]
            warm_state = (
                {
                    name: value.detach().cpu().clone()
                    for name, value in warm_model.state_dict().items()
                }
                if warm_model is not None and not args.reinitialize_each_round
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
            )
            member_models[member] = model
            for row in logs:
                row["active_round"] = int(active_round)
                training_log_rows.append(row)
            member_probability.append(
                predict_probability(model, x, adjacency_powers, torch)
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
        }
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
            f"round={active_round + 1}/{args.rounds} mode={args.acquisition_mode} "
            f"labels={queried_train_labels}/{num_available_training_labels} "
            f"positive={queried_positive} val_ap={validation_metrics['average_precision']:.6f} "
            f"test_ap={test_metrics.get('average_precision', 0.0):.6f}",
            flush=True,
        )
        if active_round + 1 == args.rounds:
            break
        if args.acquisition_mode == "random":
            new_batch: AcquisitionBatch | np.ndarray = select_random_batch(
                train_candidate_mask,
                args.query_batch_size,
                queried_mask=query_mask,
                random_seed=args.random_seed + active_round + 1,
            )
        elif args.acquisition_mode == "entropy":
            new_batch = _top_entropy_batch(
                final_probability,
                train_candidate_mask,
                query_mask,
                args.query_batch_size,
            )
        elif args.acquisition_mode == "physics_kcenter":
            new_batch = _physics_kcenter_batch(
                probability_stack,
                x,
                train_candidate_mask,
                query_mask,
                feature_names,
                args,
            )
        else:
            new_batch = select_active_query_batch(
                probability_stack,
                x,
                train_candidate_mask,
                query_mask,
                feature_names,
                args.query_batch_size,
                shortlist_multiplier=args.shortlist_multiplier,
                max_diversity_selections=args.max_diversity_selections,
            )
        query_mask = update_query_mask(query_mask, new_batch)
        _append_query_log(
            query_log_rows,
            new_batch,
            y,
            original_indices,
            line_labels,
            query_round=active_round + 1,
            mode=args.acquisition_mode,
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
    )

    final_round = round_rows[-1]
    best_round = max(
        round_rows,
        key=lambda row: float(row["validation_average_precision"]),
    )
    summary = {
        "status": "complete",
        "research_stage": "Phase 1 retrospective hidden-label replay",
        "acquisition_mode": str(args.acquisition_mode),
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py",
        "model_core_modified": False,
        "hidden_outcome_labels_used_as_features": False,
        "dataset_npz": str(args.dataset_npz),
        "num_subset_states": int(len(x)),
        "num_train_states": int((split == "train").sum()),
        "num_validation_states": int((split == "validation").sum()),
        "num_test_states": int((split == "test").sum()),
        "num_available_training_oracle_labels": num_available_training_labels,
        "num_queried_training_oracle_labels": int(final_round["queried_training_labels"]),
        "queried_training_oracle_fraction": float(final_round["queried_training_label_fraction"]),
        "num_queried_positive_labels": int(final_round["queried_positive_labels"]),
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
            "initial_pool_multiplier": int(args.initial_pool_multiplier),
            "shortlist_multiplier": int(args.shortlist_multiplier),
            "max_diversity_selections": int(args.max_diversity_selections),
            "k_gcn": int(args.k_gcn),
            "first_layer_channels": int(args.first_layer_channels),
            "second_layer_channels": int(args.second_layer_channels),
            "random_seed": int(args.random_seed),
            "warm_start_between_rounds": not bool(args.reinitialize_each_round),
        },
        "phase_boundary": (
            "This replay estimates label efficiency using labels that were already generated in the past. "
            "A prospective run must call the physical cascade oracle only for selected candidates."
        ),
        "output_files": {
            "round_metrics": "active_label_replay_round_metrics.csv",
            "training_log": "active_label_replay_training_log.csv",
            "retrieval_metrics": "active_label_replay_retrieval_metrics.csv",
            "query_sample": "active_label_replay_query_sample.csv",
            "local_checkpoint_not_for_git": "active_label_replay_local_checkpoint.npz",
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
        f"- Validation AP: {summary['final_validation_average_precision']:.6f}\n"
        f"- Test AP: {summary['final_test_average_precision']:.6f}\n\n"
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
