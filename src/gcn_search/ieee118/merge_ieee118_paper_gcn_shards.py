from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_INPUT = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_scaleup" / "paper_8000_shards"
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_scaleup" / "paper_8000_source"

from convert_ieee118_step2_to_rts79_gcn_format import PAPER_FEATURE_NAMES, fit_normalizer, normalize_x


REQUIRED_ARRAYS = {
    "physics_raw_features",
    "y_gcn",
    "loss_mask",
    "seed",
    "split",
    "sample_type",
    "active_first_line",
    "current_outage_labels",
    "line_labels",
    "branch_from_bus",
    "branch_to_bus",
    "feature_names",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge IEEE118 paper-GCN seed shards and refit train-only normalization.")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--expected-state-samples", type=int, default=8000)
    return parser.parse_args(argv)


def discover_shards(input_root: Path) -> list[Path]:
    paths = sorted(input_root.glob("*/ieee118_paper_gcn_dataset.npz"))
    if not paths:
        raise FileNotFoundError(f"No completed paper-GCN shard NPZs found under {input_root}")
    return paths


def require_matching(reference: np.ndarray, value: np.ndarray, label: str, path: Path) -> None:
    if not np.array_equal(reference, value):
        raise ValueError(f"Shard {path} has inconsistent {label}.")


def merge(args: argparse.Namespace) -> dict[str, Any]:
    shard_paths = discover_shards(args.input_root)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    chunks: dict[str, list[np.ndarray]] = {
        name: []
        for name in (
            "physics_raw_features",
            "y_gcn",
            "loss_mask",
            "seed",
            "split",
            "sample_type",
            "active_first_line",
            "current_outage_labels",
        )
    }
    reference: dict[str, np.ndarray] = {}
    for path in shard_paths:
        data = np.load(path, allow_pickle=True)
        missing = sorted(REQUIRED_ARRAYS - set(data.files))
        if missing:
            raise ValueError(f"Shard {path} is missing arrays: {missing}")
        for name in chunks:
            chunks[name].append(data[name])
        for name in ("line_labels", "branch_from_bus", "branch_to_bus", "feature_names"):
            if name not in reference:
                reference[name] = data[name]
            else:
                require_matching(reference[name], data[name], name, path)

    merged = {name: np.concatenate(values, axis=0) for name, values in chunks.items()}
    num_states = len(merged["seed"])
    if num_states != int(args.expected_state_samples):
        raise ValueError(f"Merged {num_states} states; expected {args.expected_state_samples}.")
    split = merged["split"].astype(str)
    seed = merged["seed"].astype(np.int64)
    sample_type = merged["sample_type"].astype(str)
    active_first_line = merged["active_first_line"].astype(str)
    split_seeds = {
        name: set(int(value) for value in np.unique(seed[split == name]))
        for name in ("train", "validation", "test")
    }
    overlap = (
        (split_seeds["train"] & split_seeds["validation"])
        | (split_seeds["train"] & split_seeds["test"])
        | (split_seeds["validation"] & split_seeds["test"])
    )
    if overlap:
        raise ValueError(f"Seed leakage across merged splits: {sorted(overlap)}")
    if split_seeds["test"] != {20260708}:
        raise ValueError(f"Merged test split must contain only seed 20260708, found {sorted(split_seeds['test'])}.")
    if not np.all(np.char.str_len(active_first_line[sample_type == "S1"]) > 0):
        raise ValueError("Every merged S1 state must record an explicit active_first_line.")

    keys = [
        (int(seed[idx]), str(sample_type[idx]), str(active_first_line[idx]))
        for idx in range(num_states)
    ]
    if len(set(keys)) != len(keys):
        raise ValueError("Merged shards contain duplicate seed/sample_type/active_first_line states.")

    x_raw = merged["physics_raw_features"].astype(np.float32)
    y = merged["y_gcn"].astype(np.int64)
    mask = merged["loss_mask"].astype(bool)
    train_mask = split == "train"
    if not train_mask.any():
        raise ValueError("Merged dataset has no train split for normalizer fitting.")
    normalizer = fit_normalizer(x_raw[train_mask], PAPER_FEATURE_NAMES)
    x = normalize_x(x_raw, normalizer, PAPER_FEATURE_NAMES).astype(np.float32)
    output_npz = args.output_dir / "ieee118_paper_gcn_dataset.npz"
    np.savez(
        output_npz,
        x_gcn=x,
        physics_raw_features=x_raw,
        y_gcn=y,
        y_critical=y.copy(),
        loss_mask=mask,
        seed=seed,
        split=split,
        sample_type=sample_type,
        active_first_line=active_first_line,
        current_outage_labels=merged["current_outage_labels"].astype(str),
        line_labels=reference["line_labels"].astype(str),
        branch_from_bus=reference["branch_from_bus"].astype(np.int64),
        branch_to_bus=reference["branch_to_bus"].astype(np.int64),
        feature_names=reference["feature_names"].astype(str),
    )

    rows = pd.DataFrame(
        {
            "sample_index": np.arange(num_states, dtype=int),
            "seed": seed,
            "split": split,
            "sample_type": sample_type,
            "active_first_line": active_first_line,
            "current_outage_labels": merged["current_outage_labels"].astype(str),
            "num_candidate_labels": mask.sum(axis=1).astype(int),
            "num_positive_labels": np.asarray([int(y[idx][mask[idx]].sum()) for idx in range(num_states)]),
        }
    )
    rows.to_csv(args.output_dir / "ieee118_paper_gcn_sample_summary.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_paper_gcn_feature_normalizer.json").write_text(
        json.dumps(normalizer, indent=2), encoding="utf-8"
    )
    metadata: dict[str, Any] = {
        "status": "complete",
        "case_name": "ieee118",
        "dataset_role": "formal paper-8000 source for N-1 residual-reachable targets",
        "dataset_npz": str(output_npz),
        "num_state_samples": int(num_states),
        "num_s0_samples": int((sample_type == "S0").sum()),
        "num_s1_samples": int((sample_type == "S1").sum()),
        "num_train_state_samples": int((split == "train").sum()),
        "num_validation_state_samples": int((split == "validation").sum()),
        "num_test_state_samples": int((split == "test").sum()),
        "train_seeds": sorted(split_seeds["train"]),
        "validation_seeds": sorted(split_seeds["validation"]),
        "test_seeds": sorted(split_seeds["test"]),
        "num_candidate_labels": int(mask.sum()),
        "num_positive_labels": int(y[mask].sum()),
        "positive_label_ratio": float(y[mask].mean()),
        "num_s1_active_first_line_unknown": 0,
        "normalizer_fit_split": "train",
        "source_shards": [str(path) for path in shard_paths],
        "large_npz_tracked_in_git": False,
    }
    (args.output_dir / "ieee118_paper_gcn_dataset_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    (args.output_dir / "ieee118_paper_gcn_dataset_schema.md").write_text(
        "# IEEE118 Paper-8000 Source Dataset\n\n"
        "All shards share the paper-aligned four-feature schema. Shard-normalized arrays are discarded; "
        "the merged `x_gcn` is normalized once using only merged train states. Every S1 row stores its "
        "explicit active first outage.\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    args = parse_args()
    print(json.dumps(merge(args), indent=2))


if __name__ == "__main__":
    main()
