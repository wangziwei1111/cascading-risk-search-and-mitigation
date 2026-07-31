from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
for path in (IEEE118_DIR, LEGACY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from active_replay_search_metrics import (  # noqa: E402
    active_replay_search_thresholds,
    load_active_replay_search_context,
)
from run_ieee118_active_label_replay import DEFAULT_DATASET  # noqa: E402
from tail_aware_gcn_loss import (  # noqa: E402
    hard_bipartite_tail_ranking_loss,
    masked_focal_cross_entropy,
)
from tail_active_acquisition import select_tail_disagreement_batch  # noqa: E402
from train_ieee118_paper_aligned_gcn import (  # noqa: E402
    predict_probability,
    split_metrics,
)
from train_ieee118_with_original_rts79_gcn import (  # noqa: E402
    build_branch_graph_adjacency_from_endpoints,
)
from train_rts79_paper_gcn import (  # noqa: E402
    PaperGcnTrainConfig,
    PaperStyleRts79Gcn,
    _build_adjacency_powers,
)


FORMAL_MODEL_CLASS = PaperStyleRts79Gcn
DEFAULT_PHASE3 = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_mf_all_candidates_perstate95_e1_w5_curve"
    / "pmf_hybrid_prior_corrected_seed_20260730"
    / "active_label_replay_checkpoint.pt"
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
    / "ieee118_tail_critical_gcn"
)
DEFAULT_LOW_FIDELITY = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_dc_lodf_low_fidelity_all_candidates"
    / "ieee118_dc_lodf_low_fidelity_targets.npz"
)


@dataclass(frozen=True)
class Objective:
    name: str
    focal_gamma: float
    tail_pairwise_weight: float


OBJECTIVES = {
    "ce_continue": Objective("ce_continue", 0.0, 0.0),
    "focal": Objective("focal", 2.0, 0.0),
    "hard_pairwise": Objective("hard_pairwise", 0.0, 0.25),
    "focal_hard_pairwise": Objective("focal_hard_pairwise", 2.0, 0.25),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fine-tune the unchanged RTS-79 PaperStyleRts79Gcn for difficult "
            "IEEE118 critical-path ranking."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--phase3-checkpoint", type=Path, default=DEFAULT_PHASE3)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--objectives",
        nargs="+",
        choices=sorted(OBJECTIVES),
        default=list(OBJECTIVES),
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument(
        "--positive-weight",
        type=float,
        default=2.284862667102052,
        help="Phase-3 final prior-corrected positive weight.",
    )
    parser.add_argument(
        "--focal-gamma-override",
        type=float,
        default=None,
        help="Optional ablation override for objectives that use focal loss.",
    )
    parser.add_argument(
        "--tail-pairwise-weight-override",
        type=float,
        default=None,
        help="Optional ablation override for objectives that use tail ranking.",
    )
    parser.add_argument("--pairwise-margin", type=float, default=0.05)
    parser.add_argument("--max-hard-positives", type=int, default=8)
    parser.add_argument("--max-hard-negatives", type=int, default=16)
    parser.add_argument("--random-seed", type=int, default=20260731)
    parser.add_argument(
        "--selection-metric",
        choices=["validation_ap", "validation_k95"],
        default="validation_k95",
    )
    parser.add_argument("--max-train-states", type=int, default=None)
    parser.add_argument(
        "--tail-acquisition-fraction",
        type=float,
        default=0.0,
        help="Additional label-free tail query budget as a fraction of train candidates.",
    )
    parser.add_argument(
        "--low-fidelity-target-npz", type=Path, default=DEFAULT_LOW_FIDELITY
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
    return parser.parse_args(argv)


def _require(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. Large data are not regenerated.")


def _model_config(seed: int, input_channels: int) -> PaperGcnTrainConfig:
    return PaperGcnTrainConfig(
        epochs=0,
        batch_size=64,
        learning_rate=0.001,
        k_gcn=6,
        first_layer_channels=16,
        second_layer_channels=4,
        positive_weight=20.0,
        validation_fraction=0.0,
        random_seed=int(seed),
    )


def _resolved_objective(
    objective: Objective, args: argparse.Namespace
) -> Objective:
    gamma = objective.focal_gamma
    pairwise = objective.tail_pairwise_weight
    if gamma > 0.0 and args.focal_gamma_override is not None:
        gamma = float(args.focal_gamma_override)
    if pairwise > 0.0 and args.tail_pairwise_weight_override is not None:
        pairwise = float(args.tail_pairwise_weight_override)
    if gamma < 0.0 or pairwise < 0.0:
        raise ValueError("Focal gamma and tail pairwise weight must be non-negative.")
    return Objective(objective.name, gamma, pairwise)


def critical_retrieval_k(
    probability: Any,
    labels: Any,
    mask: Any,
    recall_target: float,
) -> int:
    """Return candidates needed to retrieve a target fraction of positives."""

    score = np.asarray(probability, dtype=float)
    truth = np.asarray(labels, dtype=int)
    valid = np.asarray(mask, dtype=bool)
    if score.shape != truth.shape or truth.shape != valid.shape:
        raise ValueError("Retrieval arrays must align.")
    if not 0.0 < recall_target <= 1.0:
        raise ValueError("recall_target must be in (0, 1].")
    flat_score = score[valid]
    flat_truth = truth[valid].astype(bool)
    positives = int(flat_truth.sum())
    if positives == 0:
        return 0
    order = np.argsort(-flat_score, kind="stable")
    cumulative = np.cumsum(flat_truth[order])
    target = int(np.ceil(float(recall_target) * positives))
    return int(np.flatnonzero(cumulative >= target)[0] + 1)


def _new_model(
    state: dict[str, Any], *, input_channels: int, seed: int
) -> PaperStyleRts79Gcn:
    model = FORMAL_MODEL_CLASS(input_channels, _model_config(seed, input_channels))
    model.load_state_dict(state)
    return model


def _fit_member(
    *,
    initial_state: dict[str, Any],
    x: np.ndarray,
    y: np.ndarray,
    query_mask: np.ndarray,
    valid_mask: np.ndarray,
    split: np.ndarray,
    adjacency_powers: torch.Tensor,
    objective: Objective,
    args: argparse.Namespace,
    member_seed: int,
) -> tuple[PaperStyleRts79Gcn, list[dict[str, Any]]]:
    torch.manual_seed(int(member_seed))
    train_rows = np.flatnonzero((split == "train") & query_mask.any(axis=1))
    if args.max_train_states is not None:
        train_rows = train_rows[: int(args.max_train_states)]
    validation_rows = split == "validation"
    model = _new_model(
        copy.deepcopy(initial_state), input_channels=x.shape[2], seed=member_seed
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=float(args.learning_rate))
    class_weight = torch.tensor(
        [1.0, float(args.positive_weight)], dtype=torch.float32
    )
    generator = torch.Generator().manual_seed(int(member_seed))
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_rows], dtype=torch.float32),
            torch.tensor(y[train_rows], dtype=torch.long),
            torch.tensor(query_mask[train_rows], dtype=torch.bool),
        ),
        batch_size=int(args.batch_size),
        shuffle=True,
        generator=generator,
    )
    best_state = copy.deepcopy(initial_state)
    baseline_probability = predict_probability(
        model, x[validation_rows], adjacency_powers, torch
    )
    best_ap = float(
        split_metrics(
            y[validation_rows],
            baseline_probability,
            valid_mask[validation_rows],
        )["average_precision"]
    )
    best_k95 = critical_retrieval_k(
        baseline_probability,
        y[validation_rows],
        valid_mask[validation_rows],
        0.95,
    )
    logs = [
        {
            "objective": objective.name,
            "member_seed": int(member_seed),
            "epoch": 0,
            "validation_average_precision": best_ap,
            "validation_K95": int(best_k95),
            "selected": True,
        }
    ]
    for epoch in range(1, int(args.epochs) + 1):
        model.train()
        total = 0.0
        batches = 0
        for xb, yb, mb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            classification = masked_focal_cross_entropy(
                logits,
                yb,
                mb,
                class_weight,
                gamma=objective.focal_gamma,
            )
            tail = hard_bipartite_tail_ranking_loss(
                logits,
                yb,
                mb,
                margin=float(args.pairwise_margin),
                max_hard_positives=int(args.max_hard_positives),
                max_hard_negatives=int(args.max_hard_negatives),
            )
            loss = classification + objective.tail_pairwise_weight * tail
            loss.backward()
            optimizer.step()
            total += float(loss.detach())
            batches += 1
        probability = predict_probability(
            model, x[validation_rows], adjacency_powers, torch
        )
        validation = split_metrics(
            y[validation_rows],
            probability,
            valid_mask[validation_rows],
        )
        ap = float(validation["average_precision"])
        k95 = critical_retrieval_k(
            probability,
            y[validation_rows],
            valid_mask[validation_rows],
            0.95,
        )
        selected = (
            ap > best_ap
            if args.selection_metric == "validation_ap"
            else (k95, -ap) < (best_k95, -best_ap)
        )
        if selected:
            best_ap = ap
            best_k95 = k95
            best_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
        logs.append(
            {
                "objective": objective.name,
                "member_seed": int(member_seed),
                "epoch": int(epoch),
                "train_loss": total / max(batches, 1),
                "validation_average_precision": ap,
                "validation_K95": int(k95),
                "selected": bool(selected),
            }
        )
    model.load_state_dict(best_state)
    return model.eval(), logs


def _evaluate_models(
    *,
    name: str,
    models: list[PaperStyleRts79Gcn],
    x: np.ndarray,
    y: np.ndarray,
    valid_mask: np.ndarray,
    split: np.ndarray,
    seed: np.ndarray,
    sample_type: np.ndarray,
    adjacency_powers: torch.Tensor,
    search_context: Any,
    search_seed: int,
) -> dict[str, Any]:
    probability = np.stack(
        [predict_probability(model, x, adjacency_powers, torch) for model in models]
    ).mean(axis=0)
    validation_rows = split == "validation"
    test_rows = split == "test"
    validation = split_metrics(
        y[validation_rows], probability[validation_rows], valid_mask[validation_rows]
    )
    test = split_metrics(y[test_rows], probability[test_rows], valid_mask[test_rows])
    eval_probability = np.stack(
        [
            predict_probability(model, search_context.x_eval, adjacency_powers, torch)
            for model in models
        ]
    ).mean(axis=0)
    s0_rows = np.flatnonzero(
        test_rows & (sample_type == "S0") & (seed.astype(np.int64) == int(search_seed))
    )
    if len(s0_rows) != 1:
        raise ValueError(
            f"Expected one held-out S0 state for seed {search_seed}; found {len(s0_rows)}."
        )
    formal = active_replay_search_thresholds(
        search_context,
        s0_probability=probability[int(s0_rows[0])],
        s1_probability=eval_probability,
    )
    return {
        "objective": name,
        "model_class": FORMAL_MODEL_CLASS.__name__,
        "validation_average_precision": float(validation["average_precision"]),
        "validation_K90": critical_retrieval_k(
            probability[validation_rows], y[validation_rows], valid_mask[validation_rows], 0.90
        ),
        "validation_K95": critical_retrieval_k(
            probability[validation_rows], y[validation_rows], valid_mask[validation_rows], 0.95
        ),
        "validation_K99": critical_retrieval_k(
            probability[validation_rows], y[validation_rows], valid_mask[validation_rows], 0.99
        ),
        "test_average_precision": float(test["average_precision"]),
        "test_K95": critical_retrieval_k(
            probability[test_rows], y[test_rows], valid_mask[test_rows], 0.95
        ),
        **formal,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.dataset_npz, "training dataset"),
        (args.phase3_checkpoint, "Phase-3 checkpoint"),
        (args.search_eval_dataset_npz, "formal search dataset"),
        (args.search_fulltruth_csv, "formal full truth"),
        (args.search_first_step_summary_csv, "first-step summary"),
        (args.search_feature_normalizer_json, "feature normalizer"),
    ):
        _require(path, label)
    if args.epochs <= 0:
        raise ValueError("--epochs must be positive.")
    if not 0.0 <= args.tail_acquisition_fraction <= 0.05:
        raise ValueError("--tail-acquisition-fraction must be between 0 and 0.05.")
    if args.tail_acquisition_fraction > 0.0:
        _require(args.low_fidelity_target_npz, "low-fidelity target dataset")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.dataset_npz, allow_pickle=False)
    x = data["x_gcn"].astype(np.float32)
    y = data["y_gcn"].astype(np.int64)
    valid_mask = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
    seed = data["seed"].astype(np.int64)
    sample_type = data["sample_type"].astype(str)
    line_labels = data["line_labels"].astype(str)
    checkpoint = torch.load(
        args.phase3_checkpoint, map_location="cpu", weights_only=False
    )
    original_query_mask = np.asarray(checkpoint["query_mask"], dtype=bool)
    query_mask = original_query_mask.copy()
    member_states = checkpoint["member_states"]
    if query_mask.shape != y.shape:
        raise ValueError("Phase-3 query mask does not match the training dataset.")
    adjacency = build_branch_graph_adjacency_from_endpoints(
        data["branch_from_bus"], data["branch_to_bus"]
    )
    adjacency_powers = torch.tensor(
        _build_adjacency_powers(adjacency, 6), dtype=torch.float32
    )
    search_context = load_active_replay_search_context(
        eval_dataset_npz=args.search_eval_dataset_npz,
        fulltruth_csv=args.search_fulltruth_csv,
        first_step_summary_csv=args.search_first_step_summary_csv,
        feature_normalizer_json=args.search_feature_normalizer_json,
        expected_line_labels=line_labels,
        expected_branch_from_bus=data["branch_from_bus"],
        expected_branch_to_bus=data["branch_to_bus"],
        test_seed=int(args.search_test_seed),
    )

    baseline_models = [
        _new_model(state, input_channels=x.shape[2], seed=args.random_seed + idx)
        .eval()
        for idx, state in enumerate(member_states)
    ]
    acquisition_rows: list[dict[str, Any]] = []
    if args.tail_acquisition_fraction > 0.0:
        low_fidelity = np.load(args.low_fidelity_target_npz, allow_pickle=False)
        for name in ("proxy_score", "proxy_mask", "line_labels", "seed", "split"):
            if name not in low_fidelity:
                raise ValueError(f"Low-fidelity target dataset is missing {name}.")
        if not np.array_equal(low_fidelity["line_labels"].astype(str), line_labels):
            raise ValueError("Low-fidelity and training line labels do not align.")
        if not np.array_equal(low_fidelity["seed"].astype(np.int64), seed) or not np.array_equal(
            low_fidelity["split"].astype(str), split
        ):
            raise ValueError("Low-fidelity and training sample order does not align.")
        baseline_stack = np.stack(
            [predict_probability(model, x, adjacency_powers, torch) for model in baseline_models]
        )
        train_pool = (
            (split == "train")[:, None]
            & valid_mask
            & low_fidelity["proxy_mask"].astype(bool)
            & ~query_mask
        )
        batch_size = int(
            round(
                float(args.tail_acquisition_fraction)
                * int(valid_mask[split == "train"].sum())
            )
        )
        batch_size = min(max(batch_size, 1), int(train_pool.sum()))
        selected = select_tail_disagreement_batch(
            baseline_stack.mean(axis=0),
            baseline_stack.std(axis=0),
            low_fidelity["proxy_score"].astype(np.float64),
            train_pool,
            batch_size=batch_size,
        )
        query_mask[selected[:, 0], selected[:, 1]] = True
        for rank, (state_index, line_index) in enumerate(selected, start=1):
            acquisition_rows.append(
                {
                    "selection_rank": rank,
                    "state_index": int(state_index),
                    "seed": int(seed[state_index]),
                    "sample_type": str(sample_type[state_index]),
                    "line_label": str(line_labels[line_index]),
                    "gcn_probability_before_query": float(
                        baseline_stack[:, state_index, line_index].mean()
                    ),
                    "ensemble_std_before_query": float(
                        baseline_stack[:, state_index, line_index].std()
                    ),
                    "low_fidelity_proxy_score": float(
                        low_fidelity["proxy_score"][state_index, line_index]
                    ),
                    "revealed_critical_after_selection": int(y[state_index, line_index]),
                }
            )
        pd.DataFrame(acquisition_rows).head(500).to_csv(
            args.output_dir / "ieee118_tail_acquisition_sample.csv", index=False
        )
    metric_rows = [
        _evaluate_models(
            name="phase3_checkpoint",
            models=baseline_models,
            x=x,
            y=y,
            valid_mask=valid_mask,
            split=split,
            seed=seed,
            sample_type=sample_type,
            adjacency_powers=adjacency_powers,
            search_context=search_context,
            search_seed=args.search_test_seed,
        )
    ]
    training_logs: list[dict[str, Any]] = []
    trained_states: dict[str, list[dict[str, Any]]] = {}
    for objective_name in args.objectives:
        objective = _resolved_objective(OBJECTIVES[objective_name], args)
        models = []
        states = []
        for member, initial_state in enumerate(member_states):
            model, logs = _fit_member(
                initial_state=initial_state,
                x=x,
                y=y,
                query_mask=query_mask,
                valid_mask=valid_mask,
                split=split,
                adjacency_powers=adjacency_powers,
                objective=objective,
                args=args,
                member_seed=int(args.random_seed + member),
            )
            models.append(model)
            states.append(
                {
                    name: value.detach().cpu().clone()
                    for name, value in model.state_dict().items()
                }
            )
            training_logs.extend(logs)
        trained_states[objective_name] = states
        metric_rows.append(
            _evaluate_models(
                name=objective_name,
                models=models,
                x=x,
                y=y,
                valid_mask=valid_mask,
                split=split,
                seed=seed,
                sample_type=sample_type,
                adjacency_powers=adjacency_powers,
                search_context=search_context,
                search_seed=args.search_test_seed,
            )
        )
    metrics = pd.DataFrame(metric_rows)
    metrics.to_csv(
        args.output_dir / "ieee118_tail_aware_gcn_ablation.csv", index=False
    )
    pd.DataFrame(training_logs).to_csv(
        args.output_dir / "ieee118_tail_aware_gcn_training_log.csv", index=False
    )
    selection_columns = (
        ["validation_average_precision"]
        if args.selection_metric == "validation_ap"
        else ["validation_K95", "validation_average_precision"]
    )
    selection_ascending = (
        [False] if args.selection_metric == "validation_ap" else [True, False]
    )
    best_name = str(
        metrics.sort_values(selection_columns, ascending=selection_ascending)
        .iloc[0]["objective"]
    )
    if best_name != "phase3_checkpoint":
        torch.save(
            {
                "model_class": FORMAL_MODEL_CLASS.__name__,
                "model_core_modified": False,
                "objective": asdict(
                    _resolved_objective(OBJECTIVES[best_name], args)
                ),
                "member_states": trained_states[best_name],
                "source_phase3_checkpoint": str(args.phase3_checkpoint),
            },
            args.output_dir / "ieee118_tail_aware_gcn_checkpoint.pt",
        )
    summary = {
        "status": "complete",
        "model_class": FORMAL_MODEL_CLASS.__name__,
        "model_core_modified": False,
        "label_leakage": False,
        "num_available_training_labels": int(valid_mask[split == "train"].sum()),
        "num_queried_training_labels": int(query_mask[split == "train"].sum()),
        "num_queried_training_positives": int(
            y[(split == "train")[:, None] & query_mask].sum()
        ),
        "best_validation_objective": best_name,
        "num_original_query_labels": int(original_query_mask.sum()),
        "num_additional_tail_queries": int(
            (query_mask & ~original_query_mask).sum()
        ),
        "num_additional_tail_positive": int(
            y[query_mask & ~original_query_mask].sum()
        ),
        "tail_acquisition_fraction": float(args.tail_acquisition_fraction),
        "results": metrics.to_dict(orient="records"),
        "selection_rule": (
            "Maximum validation average precision"
            if args.selection_metric == "validation_ap"
            else "Minimum validation K95 with validation AP tie-break"
        ) + "; formal seed 20260708 truth is audit-only.",
        "prospective_seed_20260709_used_for_training_or_selection": False,
    }
    (args.output_dir / "ieee118_tail_aware_gcn_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    (args.output_dir / "ieee118_tail_aware_gcn_config.json").write_text(
        json.dumps(
            {
                "dataset_npz": str(args.dataset_npz),
                "phase3_checkpoint": str(args.phase3_checkpoint),
                "objectives": args.objectives,
                "epochs": int(args.epochs),
                "batch_size": int(args.batch_size),
                "learning_rate": float(args.learning_rate),
                "positive_weight": float(args.positive_weight),
                "focal_gamma_override": args.focal_gamma_override,
                "tail_pairwise_weight_override": args.tail_pairwise_weight_override,
                "pairwise_margin": float(args.pairwise_margin),
                "max_hard_positives": int(args.max_hard_positives),
                "max_hard_negatives": int(args.max_hard_negatives),
                "random_seed": int(args.random_seed),
                "selection_metric": str(args.selection_metric),
                "tail_acquisition_fraction": float(args.tail_acquisition_fraction),
                "low_fidelity_target_npz": str(args.low_fidelity_target_npz),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
