from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
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

from active_replay_search_metrics import load_active_replay_search_context
from mechanism_aware_gcn import (
    MechanismAwareTrainingWrapper,
    masked_positive_severity_loss,
    primary_protected_pcgrad,
)
from tail_aware_gcn_loss import (
    hard_bipartite_tail_ranking_loss,
    masked_focal_cross_entropy,
)
from train_ieee118_tail_aware_gcn import (
    DEFAULT_DATASET,
    DEFAULT_EVAL_DIR,
    DEFAULT_NORMALIZER,
    DEFAULT_TRUTH_DIR,
    _evaluate_models,
    _new_model,
    critical_retrieval_k,
)
from train_ieee118_paper_aligned_gcn import predict_probability, split_metrics
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
)
from train_rts79_paper_gcn import (
    PaperStyleRts79Gcn,
    _build_adjacency_powers,
)


FORMAL_MODEL_CLASS = PaperStyleRts79Gcn
DEFAULT_TAIL_CHECKPOINT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_tail_critical_gcn"
    / "tail_active_005_k95select"
    / "ieee118_tail_aware_gcn_checkpoint.pt"
)
DEFAULT_MECHANISM_TARGETS = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_mechanism_aware_gcn"
    / "targets_full"
    / "ieee118_mechanism_targets.npz"
)
DEFAULT_OUTPUT = (
    ROOT / "results" / "gcn_search" / "ieee118_mechanism_aware_gcn" / "training"
)


@dataclass(frozen=True)
class AuxiliaryObjective:
    name: str
    relay_weight: float
    island_weight: float
    severity_weight: float


OBJECTIVES = {
    "relay_severity": AuxiliaryObjective("relay_severity", 0.05, 0.0, 0.0),
    "relay_island_severity": AuxiliaryObjective(
        "relay_island_severity", 0.05, 0.02, 0.0
    ),
    "all_mechanisms": AuxiliaryObjective("all_mechanisms", 0.05, 0.02, 0.02),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Fine-tune the unchanged PaperStyleRts79Gcn backbone with "
            "training-only relay, island, and load-shed auxiliary heads."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--mechanism-targets-npz", type=Path, default=DEFAULT_MECHANISM_TARGETS
    )
    parser.add_argument(
        "--tail-checkpoint", type=Path, default=DEFAULT_TAIL_CHECKPOINT
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--objectives", nargs="+", choices=sorted(OBJECTIVES), default=list(OBJECTIVES)
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--critical-positive-weight", type=float, default=2.284862667102052)
    parser.add_argument("--tail-pairwise-weight", type=float, default=0.25)
    parser.add_argument("--pairwise-margin", type=float, default=0.05)
    parser.add_argument(
        "--gradient-mode",
        choices=["weighted_sum", "pcgrad_primary"],
        default="weighted_sum",
    )
    parser.add_argument("--random-seed", type=int, default=20260801)
    parser.add_argument("--max-train-states", type=int, default=None)
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
        "--search-feature-normalizer-json", type=Path, default=DEFAULT_NORMALIZER
    )
    parser.add_argument("--search-test-seed", type=int, default=20260708)
    return parser.parse_args(argv)


def _require(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing local {label}: {path}")


def _fit_member(
    *,
    initial_state: dict[str, Any],
    x: np.ndarray,
    y: np.ndarray,
    query_mask: np.ndarray,
    valid_mask: np.ndarray,
    split: np.ndarray,
    relay_severity_target: np.ndarray,
    island_severity_target: np.ndarray,
    shed_target: np.ndarray,
    mechanism_mask: np.ndarray,
    adjacency_powers: torch.Tensor,
    objective: AuxiliaryObjective,
    args: argparse.Namespace,
    member_seed: int,
) -> tuple[PaperStyleRts79Gcn, list[dict[str, Any]]]:
    torch.manual_seed(int(member_seed))
    train_rows = np.flatnonzero((split == "train") & query_mask.any(axis=1))
    if args.max_train_states is not None:
        train_rows = train_rows[: int(args.max_train_states)]
    validation_rows = split == "validation"
    primary = _new_model(
        copy.deepcopy(initial_state), input_channels=x.shape[2], seed=member_seed
    )
    wrapper = MechanismAwareTrainingWrapper(primary, hidden_channels=4)
    optimizer = torch.optim.Adam(wrapper.parameters(), lr=float(args.learning_rate))
    class_weight = torch.tensor(
        [1.0, float(args.critical_positive_weight)], dtype=torch.float32
    )
    generator = torch.Generator().manual_seed(int(member_seed))
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x[train_rows], dtype=torch.float32),
            torch.tensor(y[train_rows], dtype=torch.long),
            torch.tensor(query_mask[train_rows], dtype=torch.bool),
            torch.tensor(relay_severity_target[train_rows], dtype=torch.float32),
            torch.tensor(island_severity_target[train_rows], dtype=torch.float32),
            torch.tensor(shed_target[train_rows], dtype=torch.float32),
            torch.tensor(mechanism_mask[train_rows], dtype=torch.bool),
        ),
        batch_size=int(args.batch_size),
        shuffle=True,
        generator=generator,
    )
    baseline_probability = predict_probability(
        primary, x[validation_rows], adjacency_powers, torch
    )
    baseline_metrics = split_metrics(
        y[validation_rows], baseline_probability, valid_mask[validation_rows]
    )
    best_ap = float(baseline_metrics["average_precision"])
    best_k95 = critical_retrieval_k(
        baseline_probability,
        y[validation_rows],
        valid_mask[validation_rows],
        0.95,
    )
    best_state = copy.deepcopy(primary.state_dict())
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
        wrapper.train()
        totals = {"loss": 0.0, "critical": 0.0, "relay": 0.0, "island": 0.0, "severity": 0.0}
        gradient_conflicts = 0
        gradient_cosine = 0.0
        batches = 0
        for xb, yb, qb, rb, ib, sb, mb in loader:
            optimizer.zero_grad()
            output = wrapper(xb, adjacency_powers)
            critical_loss = masked_focal_cross_entropy(
                output["critical_logits"], yb, qb, class_weight, gamma=0.0
            )
            pairwise_loss = hard_bipartite_tail_ranking_loss(
                output["critical_logits"],
                yb,
                qb,
                margin=float(args.pairwise_margin),
                max_hard_positives=8,
                max_hard_negatives=16,
            )
            critical_loss = critical_loss + float(args.tail_pairwise_weight) * pairwise_loss
            relay_loss = masked_positive_severity_loss(
                output["log1p_relay_trips"], rb, mb
            )
            island_loss = masked_positive_severity_loss(
                output["log1p_island_shed"], ib, mb
            )
            severity_loss = masked_positive_severity_loss(
                output["log1p_load_shed"], sb, mb
            )
            auxiliary_loss = (
                objective.relay_weight * relay_loss
                + objective.island_weight * island_loss
                + objective.severity_weight * severity_loss
            )
            loss = critical_loss + auxiliary_loss
            if args.gradient_mode == "pcgrad_primary":
                parameters = list(wrapper.parameters())
                shared_ids = {
                    id(parameter)
                    for module in (primary.graph_1, primary.graph_2)
                    for parameter in module.parameters()
                }
                primary_gradients = list(
                    torch.autograd.grad(
                        critical_loss,
                        parameters,
                        retain_graph=True,
                        allow_unused=True,
                    )
                )
                auxiliary_gradients = list(
                    torch.autograd.grad(
                        auxiliary_loss,
                        parameters,
                        allow_unused=True,
                    )
                )
                combined, gradient_audit = primary_protected_pcgrad(
                    primary_gradients,
                    auxiliary_gradients,
                    [id(parameter) in shared_ids for parameter in parameters],
                )
                for parameter, gradient in zip(parameters, combined):
                    parameter.grad = gradient
                gradient_conflicts += int(gradient_audit["gradient_conflict"])
                gradient_cosine += float(
                    gradient_audit["primary_auxiliary_cosine"]
                )
            else:
                loss.backward()
            optimizer.step()
            for name, value in (
                ("loss", loss),
                ("critical", critical_loss),
                ("relay", relay_loss),
                ("island", island_loss),
                ("severity", severity_loss),
            ):
                totals[name] += float(value.detach())
            batches += 1
        probability = predict_probability(
            primary, x[validation_rows], adjacency_powers, torch
        )
        validation = split_metrics(
            y[validation_rows], probability, valid_mask[validation_rows]
        )
        ap = float(validation["average_precision"])
        k95 = critical_retrieval_k(
            probability,
            y[validation_rows],
            valid_mask[validation_rows],
            0.95,
        )
        selected = (k95, -ap) < (best_k95, -best_ap)
        if selected:
            best_k95 = int(k95)
            best_ap = ap
            best_state = copy.deepcopy(primary.state_dict())
        logs.append(
            {
                "objective": objective.name,
                "member_seed": int(member_seed),
                "epoch": int(epoch),
                "validation_average_precision": ap,
                "validation_K95": int(k95),
                "selected": bool(selected),
                **{
                    f"train_{name}_loss": value / max(batches, 1)
                    for name, value in totals.items()
                },
                "gradient_conflict_ratio": gradient_conflicts / max(batches, 1),
                "mean_primary_auxiliary_cosine": gradient_cosine
                / max(batches, 1),
            }
        )
    primary.load_state_dict(best_state)
    return primary.eval(), logs


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.dataset_npz, "training dataset"),
        (args.mechanism_targets_npz, "mechanism targets"),
        (args.tail_checkpoint, "tail GCN checkpoint"),
        (args.search_eval_dataset_npz, "formal search dataset"),
        (args.search_fulltruth_csv, "formal full truth"),
        (args.search_first_step_summary_csv, "first-step summary"),
        (args.search_feature_normalizer_json, "feature normalizer"),
    ):
        _require(path, label)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.dataset_npz, allow_pickle=False)
    target = np.load(args.mechanism_targets_npz, allow_pickle=False)
    if not bool(target["complete"]):
        raise ValueError("Mechanism target dataset is incomplete; resume its builder.")
    for name in (
        "query_mask",
        "mechanism_known_mask",
        "relay_cascade_target",
        "island_shed_target",
        "log1p_relay_trip_target",
        "log1p_island_shed_target",
        "log1p_load_shed_target",
    ):
        if target[name].shape != data["y_gcn"].shape:
            raise ValueError(f"Mechanism array {name} does not align with dataset.")
    checkpoint = torch.load(
        args.tail_checkpoint, map_location="cpu", weights_only=False
    )
    if checkpoint.get("model_class") != "PaperStyleRts79Gcn":
        raise ValueError("Tail checkpoint is not the original RTS-79 GCN class.")
    x = data["x_gcn"].astype(np.float32)
    y = data["y_gcn"].astype(np.int64)
    valid = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
    seed = data["seed"].astype(np.int64)
    sample_type = data["sample_type"].astype(str)
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
        expected_line_labels=data["line_labels"].astype(str),
        expected_branch_from_bus=data["branch_from_bus"],
        expected_branch_to_bus=data["branch_to_bus"],
        test_seed=int(args.search_test_seed),
    )
    baseline_models = [
        _new_model(state, input_channels=x.shape[2], seed=args.random_seed + index)
        .eval()
        for index, state in enumerate(checkpoint["member_states"])
    ]
    results = [
        _evaluate_models(
            name="tail_hard_pairwise_checkpoint",
            models=baseline_models,
            x=x,
            y=y,
            valid_mask=valid,
            split=split,
            seed=seed,
            sample_type=sample_type,
            adjacency_powers=adjacency_powers,
            search_context=search_context,
            search_seed=args.search_test_seed,
        )
    ]
    logs: list[dict[str, Any]] = []
    states_by_objective: dict[str, list[dict[str, Any]]] = {}
    for objective_name in args.objectives:
        base_objective = OBJECTIVES[objective_name]
        result_name = f"{objective_name}_{args.gradient_mode}"
        objective = AuxiliaryObjective(
            result_name,
            base_objective.relay_weight,
            base_objective.island_weight,
            base_objective.severity_weight,
        )
        models = []
        states = []
        for member, initial_state in enumerate(checkpoint["member_states"]):
            model, member_logs = _fit_member(
                initial_state=initial_state,
                x=x,
                y=y,
                query_mask=target["query_mask"].astype(bool),
                valid_mask=valid,
                split=split,
                relay_severity_target=target["log1p_relay_trip_target"].astype(
                    np.float32
                ),
                island_severity_target=target[
                    "log1p_island_shed_target"
                ].astype(np.float32),
                shed_target=target["log1p_load_shed_target"].astype(np.float32),
                mechanism_mask=target["mechanism_known_mask"].astype(bool),
                adjacency_powers=adjacency_powers,
                objective=objective,
                args=args,
                member_seed=int(args.random_seed) + member,
            )
            models.append(model)
            states.append(copy.deepcopy(model.state_dict()))
            logs.extend(member_logs)
        states_by_objective[result_name] = states
        results.append(
            _evaluate_models(
                name=result_name,
                models=models,
                x=x,
                y=y,
                valid_mask=valid,
                split=split,
                seed=seed,
                sample_type=sample_type,
                adjacency_powers=adjacency_powers,
                search_context=search_context,
                search_seed=args.search_test_seed,
            )
        )
    best = min(
        results,
        key=lambda row: (
            int(row["validation_K95"]),
            -float(row["validation_average_precision"]),
        ),
    )
    best_name = str(best["objective"])
    selected_states = (
        checkpoint["member_states"]
        if best_name == "tail_hard_pairwise_checkpoint"
        else states_by_objective[best_name]
    )
    selected_objective = (
        {"name": best_name, "auxiliary_training_accepted": False}
        if best_name == "tail_hard_pairwise_checkpoint"
        else {
            "name": best_name,
            "gradient_mode": str(args.gradient_mode),
            "auxiliary_training_accepted": True,
        }
    )
    torch.save(
        {
            "model_class": "PaperStyleRts79Gcn",
            "model_core_modified": False,
            "training_wrapper": "MechanismAwareTrainingWrapper",
            "auxiliary_heads_deployed": False,
            "objective": selected_objective,
            "member_states": selected_states,
        },
        args.output_dir / "ieee118_mechanism_aware_gcn_checkpoint.pt",
    )
    pd.DataFrame(logs).to_csv(
        args.output_dir / "ieee118_mechanism_aware_training_log.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "training_wrapper": "MechanismAwareTrainingWrapper",
        "auxiliary_heads_deployed": False,
        "label_leakage": False,
        "best_validation_objective": best_name,
        "gradient_mode": str(args.gradient_mode),
        "num_mechanism_known_labels": int(target["mechanism_known_mask"].sum()),
        "num_relay_positive": int(target["relay_cascade_target"].sum()),
        "num_island_positive": int(target["island_shed_target"].sum()),
        "results": results,
        "selection_rule": "Minimum validation K95, then maximum validation AP.",
        "formal_seed_20260708_used_for_training_or_selection": False,
    }
    (args.output_dir / "ieee118_mechanism_aware_gcn_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    summary = run(parse_args(argv))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
