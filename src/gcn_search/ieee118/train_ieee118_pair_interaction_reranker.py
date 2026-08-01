from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch


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
from pair_interaction_reranker import (  # noqa: E402
    build_pair_interaction_features,
    fit_linear_interaction_head,
    normalized_line_graph_distances,
    predict_linear_interaction_head,
)
from tail_active_acquisition import select_groupwise_dense_batch  # noqa: E402
from train_ieee118_paper_aligned_gcn import predict_probability, split_metrics  # noqa: E402
from train_ieee118_tail_aware_gcn import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_EVAL_DIR,
    DEFAULT_LOW_FIDELITY,
    DEFAULT_NORMALIZER,
    DEFAULT_PHASE3,
    DEFAULT_TRUTH_DIR,
    _new_model,
    critical_retrieval_k,
)
from train_ieee118_with_original_rts79_gcn import (  # noqa: E402
    build_branch_graph_adjacency_from_endpoints,
)
from train_rts79_paper_gcn import _build_adjacency_powers  # noqa: E402


DEFAULT_GCN = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_groupwise_listwise_gcn"
    / "dense005_ablation_e5"
    / "ieee118_tail_aware_gcn_checkpoint.pt"
)
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_pair_interaction_gcn"
MODES = ("gcn_logit", "gcn_candidate", "gcn_pair_relation")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train a relation-aware linear reranker over a frozen RTS-79 GCN."
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--phase3-checkpoint", type=Path, default=DEFAULT_PHASE3)
    parser.add_argument("--low-fidelity-target-npz", type=Path, default=DEFAULT_LOW_FIDELITY)
    parser.add_argument("--gcn-checkpoint", type=Path, default=DEFAULT_GCN)
    parser.add_argument("--tail-acquisition-fraction", type=float, default=0.005)
    parser.add_argument("--positive-weight", type=float, default=2.284862667102052)
    parser.add_argument("--epochs", type=int, default=250)
    parser.add_argument("--learning-rate", type=float, default=0.02)
    parser.add_argument("--weight-decay", type=float, default=0.001)
    parser.add_argument("--random-seed", type=int, default=20260801)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--search-eval-dataset-npz", type=Path, default=DEFAULT_EVAL_DIR / "ieee118_rts79_gcn_dataset.npz")
    parser.add_argument("--search-fulltruth-csv", type=Path, default=DEFAULT_TRUTH_DIR / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--search-first-step-summary-csv", type=Path, default=DEFAULT_TRUTH_DIR / "ieee118_first_step_summary.csv")
    parser.add_argument("--search-feature-normalizer-json", type=Path, default=DEFAULT_NORMALIZER)
    parser.add_argument("--search-test-seed", type=int, default=20260708)
    return parser.parse_args(argv)


def _require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing local pair-interaction input: {path}")


def _ensemble_probability(
    checkpoint_path: Path,
    x: np.ndarray,
    adjacency_powers: torch.Tensor,
) -> np.ndarray:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    models = [
        _new_model(state, input_channels=x.shape[2], seed=100 + idx).eval()
        for idx, state in enumerate(checkpoint["member_states"])
    ]
    return np.stack(
        [predict_probability(model, x, adjacency_powers, torch) for model in models]
    ).mean(axis=0)


def _dense_query_mask(
    data: Any,
    phase3: dict[str, Any],
    low: Any,
    adjacency_powers: torch.Tensor,
    fraction: float,
) -> np.ndarray:
    x = data["x_gcn"].astype(np.float32)
    original = np.asarray(phase3["query_mask"], dtype=bool)
    valid = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
    phase_models = [
        _new_model(state, input_channels=x.shape[2], seed=idx).eval()
        for idx, state in enumerate(phase3["member_states"])
    ]
    members = np.stack(
        [predict_probability(model, x, adjacency_powers, torch) for model in phase_models]
    )
    pool = (
        (split == "train")[:, None]
        & valid
        & low["proxy_mask"].astype(bool)
        & ~original
    )
    budget = min(
        max(int(round(float(fraction) * int(valid[split == "train"].sum()))), 1),
        int(pool.sum()),
    )
    selected = select_groupwise_dense_batch(
        members.mean(axis=0),
        members.std(axis=0),
        low["proxy_score"].astype(np.float64),
        pool,
        batch_size=budget,
        group_ids=data["seed"].astype(np.int64),
    )
    query = original.copy()
    query[selected[:, 0], selected[:, 1]] = True
    return query


def _metrics(
    name: str,
    probability: np.ndarray,
    y: np.ndarray,
    valid: np.ndarray,
    split: np.ndarray,
) -> dict[str, Any]:
    row: dict[str, Any] = {"method": name}
    for partition in ("validation", "test"):
        selected = split == partition
        metric = split_metrics(y[selected], probability[selected], valid[selected])
        row[f"{partition}_average_precision"] = float(metric["average_precision"])
        for recall in (0.90, 0.95, 0.99):
            row[f"{partition}_K{int(recall * 100)}"] = critical_retrieval_k(
                probability[selected], y[selected], valid[selected], recall
            )
    return row


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path in (
        args.dataset_npz,
        args.phase3_checkpoint,
        args.low_fidelity_target_npz,
        args.gcn_checkpoint,
        args.search_eval_dataset_npz,
        args.search_fulltruth_csv,
        args.search_first_step_summary_csv,
        args.search_feature_normalizer_json,
    ):
        _require(path)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.dataset_npz, allow_pickle=False)
    low = np.load(args.low_fidelity_target_npz, allow_pickle=False)
    phase3 = torch.load(args.phase3_checkpoint, map_location="cpu", weights_only=False)
    x = data["x_gcn"].astype(np.float32)
    y = data["y_gcn"].astype(np.int64)
    valid = data["loss_mask"].astype(bool)
    split = data["split"].astype(str)
    active = data["active_first_line"].astype(str)
    line_labels = data["line_labels"].astype(str)
    adjacency = build_branch_graph_adjacency_from_endpoints(
        data["branch_from_bus"], data["branch_to_bus"]
    )
    adjacency_powers = torch.tensor(
        _build_adjacency_powers(adjacency, 6), dtype=torch.float32
    )
    distance = normalized_line_graph_distances(adjacency)
    query = _dense_query_mask(
        data, phase3, low, adjacency_powers, args.tail_acquisition_fraction
    )
    base_probability = _ensemble_probability(args.gcn_checkpoint, x, adjacency_powers)
    train_rows = split == "train"

    search = load_active_replay_search_context(
        eval_dataset_npz=args.search_eval_dataset_npz,
        fulltruth_csv=args.search_fulltruth_csv,
        first_step_summary_csv=args.search_first_step_summary_csv,
        feature_normalizer_json=args.search_feature_normalizer_json,
        expected_line_labels=line_labels,
        expected_branch_from_bus=data["branch_from_bus"],
        expected_branch_to_bus=data["branch_to_bus"],
        test_seed=int(args.search_test_seed),
    )
    eval_probability = _ensemble_probability(
        args.gcn_checkpoint, search.x_eval, adjacency_powers
    )
    seed = data["seed"].astype(np.int64)
    sample_type = data["sample_type"].astype(str)
    s0_rows = np.flatnonzero(
        (split == "test")
        & (sample_type == "S0")
        & (seed == int(args.search_test_seed))
    )
    if len(s0_rows) != 1:
        raise ValueError("Expected one formal S0 state.")

    rows = [_metrics("frozen_dense_gcn", base_probability, y, valid, split)]
    rows[0].update(
        active_replay_search_thresholds(
            search,
            s0_probability=base_probability[int(s0_rows[0])],
            s1_probability=eval_probability,
        )
    )
    head_states: dict[str, dict[str, Any]] = {}
    feature_names: dict[str, tuple[str, ...]] = {}
    for mode in MODES:
        features, known, names = build_pair_interaction_features(
            base_probability, x, active, line_labels, distance, mode=mode
        )
        training_mask = train_rows[:, None] & known[:, None] & query & valid
        state = fit_linear_interaction_head(
            features[training_mask],
            y[training_mask],
            positive_weight=float(args.positive_weight),
            epochs=int(args.epochs),
            learning_rate=float(args.learning_rate),
            weight_decay=float(args.weight_decay),
            random_seed=int(args.random_seed),
        )
        probability = base_probability.copy()
        known_rows = np.flatnonzero(known)
        probability[known_rows] = predict_linear_interaction_head(
            features[known_rows], state
        )
        row = _metrics(mode, probability, y, valid, split)
        eval_features, eval_known, eval_names = build_pair_interaction_features(
            eval_probability,
            search.x_eval,
            search.first_lines,
            line_labels,
            distance,
            mode=mode,
        )
        if not eval_known.all() or names != eval_names:
            raise ValueError("Formal pair interaction features do not align.")
        row.update(
            active_replay_search_thresholds(
                search,
                s0_probability=base_probability[int(s0_rows[0])],
                s1_probability=predict_linear_interaction_head(eval_features, state),
            )
        )
        rows.append(row)
        head_states[mode] = state
        feature_names[mode] = names

    table = pd.DataFrame(rows)
    selected = str(
        table.sort_values(
            ["validation_K95", "validation_average_precision"],
            ascending=[True, False],
        ).iloc[0]["method"]
    )
    table.to_csv(args.output_dir / "ieee118_pair_interaction_ablation.csv", index=False)
    if selected != "frozen_dense_gcn":
        torch.save(
            {
                "model_type": "linear_pair_interaction_head",
                "gcn_core_class": "PaperStyleRts79Gcn",
                "gcn_core_modified": False,
                "source_gcn_checkpoint": str(args.gcn_checkpoint),
                "feature_mode": selected,
                "feature_names": feature_names[selected],
                "line_labels": line_labels,
                "head_state": head_states[selected],
                "positive_weight": float(args.positive_weight),
            },
            args.output_dir / "ieee118_pair_interaction_head.pt",
        )
    summary = {
        "status": "complete",
        "gcn_core_class": "PaperStyleRts79Gcn",
        "gcn_core_modified": False,
        "label_leakage": False,
        "num_queried_s1_training_labels": int(
            ((split == "train")[:, None] & (active != "")[:, None] & query & valid).sum()
        ),
        "selected_method": selected,
        "selection_rule": "Minimum validation K95 with validation AP tie-break.",
        "formal_seed_used_for_selection": False,
        "results": table.to_dict(orient="records"),
    }
    (args.output_dir / "ieee118_pair_interaction_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
