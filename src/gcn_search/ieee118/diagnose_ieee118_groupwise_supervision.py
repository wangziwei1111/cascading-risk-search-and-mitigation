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
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
for path in (IEEE118_DIR, LEGACY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from build_ieee118_mechanism_targets import (  # noqa: E402
    DEFAULT_DATASET,
    DEFAULT_LOW_FIDELITY,
    DEFAULT_PHASE3,
)
from tail_active_acquisition import (  # noqa: E402
    select_groupwise_dense_batch,
    select_tail_disagreement_batch,
)
from train_ieee118_paper_aligned_gcn import predict_probability  # noqa: E402
from train_ieee118_tail_aware_gcn import _new_model  # noqa: E402
from train_ieee118_with_original_rts79_gcn import (  # noqa: E402
    build_branch_graph_adjacency_from_endpoints,
)
from train_rts79_paper_gcn import _build_adjacency_powers  # noqa: E402


DEFAULT_OUTPUT = (
    ROOT / "results" / "gcn_search" / "ieee118_groupwise_listwise_gcn" / "compact"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose scattered versus dense S1 active supervision."
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--phase3-checkpoint", type=Path, default=DEFAULT_PHASE3)
    parser.add_argument("--low-fidelity-target-npz", type=Path, default=DEFAULT_LOW_FIDELITY)
    parser.add_argument("--tail-acquisition-fraction", type=float, default=0.005)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _strategy_row(
    name: str,
    selected: np.ndarray,
    *,
    labels: np.ndarray,
    valid: np.ndarray,
) -> dict[str, Any]:
    mask = np.zeros_like(valid, dtype=bool)
    if len(selected):
        mask[selected[:, 0], selected[:, 1]] = True
    per_state = mask.sum(axis=1)
    return {
        "strategy": name,
        "num_additional_queries": int(mask.sum()),
        "num_states_receiving_queries": int((per_state > 0).sum()),
        "median_queries_per_selected_state": float(
            np.median(per_state[per_state > 0]) if np.any(per_state > 0) else 0.0
        ),
        "max_queries_per_state": int(per_state.max(initial=0)),
        "num_states_with_at_least_128_queries": int((per_state >= 128).sum()),
        "revealed_positives_after_selection": int(labels[mask & valid].sum()),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path in (
        args.dataset_npz,
        args.phase3_checkpoint,
        args.low_fidelity_target_npz,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing local diagnosis input: {path}")
    import torch

    data = np.load(args.dataset_npz, allow_pickle=False)
    low = np.load(args.low_fidelity_target_npz, allow_pickle=False)
    checkpoint = torch.load(args.phase3_checkpoint, map_location="cpu", weights_only=False)
    valid = data["loss_mask"].astype(bool)
    labels = data["y_gcn"].astype(np.int64)
    split = data["split"].astype(str)
    original = np.asarray(checkpoint["query_mask"], dtype=bool)
    adjacency = build_branch_graph_adjacency_from_endpoints(
        data["branch_from_bus"], data["branch_to_bus"]
    )
    adjacency_powers = torch.tensor(
        _build_adjacency_powers(adjacency, 6), dtype=torch.float32
    )
    models = [
        _new_model(state, input_channels=data["x_gcn"].shape[2], seed=index)
        for index, state in enumerate(checkpoint["member_states"])
    ]
    member_probability = np.stack(
        [
            predict_probability(
                model, data["x_gcn"].astype(np.float32), adjacency_powers, torch
            )
            for model in models
        ]
    )
    pool = (
        (split == "train")[:, None]
        & valid
        & low["proxy_mask"].astype(bool)
        & ~original
    )
    budget = min(
        max(int(round(args.tail_acquisition_fraction * int(valid[split == "train"].sum()))), 1),
        int(pool.sum()),
    )
    common = (
        member_probability.mean(axis=0),
        member_probability.std(axis=0),
        low["proxy_score"].astype(np.float64),
        pool,
    )
    scattered = select_tail_disagreement_batch(*common, batch_size=budget)
    dense = select_groupwise_dense_batch(
        *common, batch_size=budget, group_ids=data["seed"].astype(np.int64)
    )
    rows = [
        _strategy_row("scattered_round_robin", scattered, labels=labels, valid=valid),
        _strategy_row("dense_state", dense, labels=labels, valid=valid),
    ]
    train_rows = split == "train"
    original_counts = (original & valid)[train_rows].sum(axis=1)
    summary = {
        "status": "complete",
        "selection_reads_labels": False,
        "labels_used_only_for_post_selection_audit": True,
        "num_train_states": int(train_rows.sum()),
        "num_available_train_candidates": int(valid[train_rows].sum()),
        "num_available_train_positives": int(labels[train_rows][valid[train_rows]].sum()),
        "phase3_num_queried_candidates": int((original & valid)[train_rows].sum()),
        "phase3_median_queries_per_train_state": float(np.median(original_counts)),
        "additional_query_budget": int(budget),
        "strategies": rows,
        "diagnosis": (
            "The scattered selector adds one label to thousands of S1 states, while "
            "deployment ranks a complete candidate list within each S1 state."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(
        args.output_dir / "ieee118_groupwise_supervision_diagnosis.csv", index=False
    )
    (args.output_dir / "ieee118_groupwise_supervision_diagnosis.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
