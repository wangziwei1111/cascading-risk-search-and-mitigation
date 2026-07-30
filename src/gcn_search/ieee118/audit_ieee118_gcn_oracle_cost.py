from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATASET = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_gcn_dataset.npz"
)
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_simulation_efficient_gcn"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit high-fidelity label-oracle cost for an IEEE118 GCN NPZ.")
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def require_dataset(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing local IEEE118 GCN dataset NPZ: {path}. "
            "This audit will not regenerate high-fidelity cascade labels."
        )


def _group_counts(
    split: np.ndarray,
    sample_type: np.ndarray,
    target_mask: np.ndarray,
    source_mask: np.ndarray,
    labels: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split_name in sorted(set(split.tolist())):
        for type_name in sorted(set(sample_type.tolist())):
            state_mask = (split == split_name) & (sample_type == type_name)
            if not state_mask.any():
                continue
            active = target_mask[state_mask]
            source = source_mask[state_mask]
            target = labels[state_mask]
            rows.append(
                {
                    "split": str(split_name),
                    "sample_type": str(type_name),
                    "num_states": int(state_mask.sum()),
                    "num_source_high_fidelity_labels": int(source.sum()),
                    "num_target_high_fidelity_labels": int(active.sum()),
                    "num_positive_target_labels": int(target[active].sum()),
                }
            )
    return rows


def audit(dataset_npz: Path, output_dir: Path | None = None) -> dict[str, Any]:
    require_dataset(dataset_npz)
    data = np.load(dataset_npz, allow_pickle=True)
    required = {"x_gcn", "y_gcn", "loss_mask", "split", "sample_type"}
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Dataset NPZ is missing required arrays: {missing}")
    labels = data["y_gcn"].astype(np.int64)
    target_mask = data["loss_mask"].astype(bool)
    source_mask = (
        data["source_loss_mask"].astype(bool)
        if "source_loss_mask" in data.files
        else target_mask.copy()
    )
    split = data["split"].astype(str)
    sample_type = data["sample_type"].astype(str)
    if labels.shape != target_mask.shape or labels.shape != source_mask.shape:
        raise ValueError("Label and candidate masks do not have matching dimensions.")
    if len(labels) != len(split) or len(labels) != len(sample_type):
        raise ValueError("State metadata does not match label rows.")

    s0 = sample_type == "S0"
    s1 = sample_type == "S1"
    train = split == "train"
    active_labels = int(target_mask.sum())
    active_train_labels = int(target_mask[train].sum())
    summary = {
        "status": "complete",
        "dataset_npz": str(dataset_npz),
        "num_graph_states": int(len(labels)),
        "num_lines": int(labels.shape[1]),
        "num_source_high_fidelity_labels": int(source_mask.sum()),
        "num_active_target_high_fidelity_labels": active_labels,
        "num_active_training_high_fidelity_labels": active_train_labels,
        "num_positive_target_labels": int(labels[target_mask].sum()),
        "positive_target_label_ratio": float(labels[target_mask].mean()),
        "estimated_n1_oracle_calls_for_s0_labels": int(source_mask[s0].sum()),
        "estimated_n2_oracle_calls_for_s1_labels": int(source_mask[s1].sum()),
        "estimated_residual_n2_target_calls": int(target_mask[s1].sum()),
        "ten_percent_training_oracle_budget": int(round(0.10 * active_train_labels)),
        "one_percent_training_oracle_budget": int(round(0.01 * active_train_labels)),
        "counts_by_split_and_sample_type": _group_counts(
            split,
            sample_type,
            target_mask,
            source_mask,
            labels,
        ),
        "interpretation": (
            "Candidate-label entries are high-fidelity physical-oracle targets in the current exhaustive builder. "
            "Retrospective active-learning replay hides these labels and counts only queried entries."
        ),
    }
    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "ieee118_gcn_oracle_cost_audit.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
    return summary


def main() -> None:
    args = parse_args()
    print(json.dumps(audit(args.dataset_npz, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
