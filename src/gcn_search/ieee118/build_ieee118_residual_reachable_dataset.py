from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_paper_aligned_training_scaleup"
    / "pilot_2000"
    / "ieee118_paper_gcn_dataset.npz"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_reachable_gcn"
    / "pilot_2000_dataset"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert IEEE118 paper-aligned data to N-1-masked residual reachable labels.")
    parser.add_argument("--source-dataset-npz", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--source-normalizer-json",
        type=Path,
        default=None,
        help="Defaults to ieee118_paper_gcn_feature_normalizer.json beside the source NPZ.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. Generate the local paper-aligned pilot dataset first; "
            "this converter will not rerun OPA."
        )


def split_labels(value: str) -> list[str]:
    return [token.strip().upper() for token in str(value).split(",") if token.strip()]


def infer_active_first_lines(
    sample_type: np.ndarray,
    current_outage_labels: np.ndarray,
    explicit: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    active = np.full(len(sample_type), "", dtype="U16")
    source = np.full(len(sample_type), "unknown", dtype="U24")
    if explicit is not None:
        explicit = explicit.astype(str)
        known = (sample_type == "S1") & (np.char.str_len(explicit) > 0)
        active[known] = explicit[known]
        source[known] = "explicit"
    for idx, kind in enumerate(sample_type):
        if kind != "S1" or active[idx]:
            continue
        labels = split_labels(str(current_outage_labels[idx]))
        if len(labels) == 1:
            active[idx] = labels[0]
            source[idx] = "single_outage_inferred"
    source[sample_type == "S0"] = "not_applicable"
    return active, source


def validate_seed_splits(seed: np.ndarray, split: np.ndarray) -> None:
    for value in np.unique(seed):
        names = set(split[seed == value].astype(str).tolist())
        if len(names) > 1:
            raise ValueError(f"Seed {int(value)} appears in multiple splits: {sorted(names)}")


def n1_mask_by_seed(
    y_source: np.ndarray,
    source_mask: np.ndarray,
    seed: np.ndarray,
    sample_type: np.ndarray,
) -> dict[int, np.ndarray]:
    result: dict[int, np.ndarray] = {}
    for value in np.unique(seed):
        indices = np.where((seed == value) & (sample_type == "S0"))[0]
        if len(indices) == 0:
            raise ValueError(f"Seed {int(value)} has no S0 sample; N-1 critical mask cannot be constructed.")
        result[int(value)] = np.any((y_source[indices] == 1) & source_mask[indices], axis=0)
    return result


def build_residual_labels(data: Any) -> dict[str, np.ndarray]:
    required = {
        "x_gcn",
        "y_gcn",
        "loss_mask",
        "seed",
        "split",
        "sample_type",
        "current_outage_labels",
        "line_labels",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Source paper GCN NPZ missing required arrays: {missing}")

    y_source = data["y_gcn"].astype(np.int64)
    source_mask = data["loss_mask"].astype(bool)
    seed = data["seed"].astype(np.int64)
    split = data["split"].astype(str)
    sample_type = data["sample_type"].astype(str)
    current_outages = data["current_outage_labels"].astype(str)
    line_labels = data["line_labels"].astype(str)
    explicit = data["active_first_line"] if "active_first_line" in data.files else None
    active_first_line, active_source = infer_active_first_lines(sample_type, current_outages, explicit)
    validate_seed_splits(seed, split)
    label_to_index = {label: idx for idx, label in enumerate(line_labels)}
    n1_by_seed = n1_mask_by_seed(y_source, source_mask, seed, sample_type)

    y_residual = np.zeros_like(y_source, dtype=np.int64)
    residual_mask = np.zeros_like(source_mask, dtype=bool)
    repeated_n1_mask = np.zeros_like(source_mask, dtype=bool)
    known_s0_labels = np.zeros_like(source_mask, dtype=bool)

    # S1 keeps the original path outcome label, but known N-1-critical second lines are not residual candidates.
    for idx in np.where(sample_type == "S1")[0]:
        n1_mask = n1_by_seed[int(seed[idx])]
        repeated_n1_mask[idx] = n1_mask
        residual_mask[idx] = source_mask[idx] & ~n1_mask
        y_residual[idx] = y_source[idx]

    # Existing pilot files before this stage did not always store active_first_line. Only unambiguous S1 states
    # contribute S0 reachable labels; unknown lines remain masked instead of being silently labeled negative.
    s0_target_by_seed: dict[int, dict[str, int]] = {}
    for idx in np.where(sample_type == "S1")[0]:
        first_line = str(active_first_line[idx])
        if not first_line:
            continue
        if first_line not in label_to_index:
            raise ValueError(f"Unknown active_first_line {first_line} in source dataset.")
        line_idx = label_to_index[first_line]
        n1_mask = n1_by_seed[int(seed[idx])]
        if n1_mask[line_idx]:
            continue
        reachable = int(np.any((y_residual[idx] == 1) & residual_mask[idx]))
        targets = s0_target_by_seed.setdefault(int(seed[idx]), {})
        if first_line in targets and targets[first_line] != reachable:
            raise ValueError(f"Conflicting residual reachable labels for seed={int(seed[idx])}, first_line={first_line}")
        targets[first_line] = reachable

    for idx in np.where(sample_type == "S0")[0]:
        n1_mask = n1_by_seed[int(seed[idx])]
        repeated_n1_mask[idx] = n1_mask
        for first_line, reachable in s0_target_by_seed.get(int(seed[idx]), {}).items():
            line_idx = label_to_index[first_line]
            if source_mask[idx, line_idx] and not n1_mask[line_idx]:
                residual_mask[idx, line_idx] = True
                known_s0_labels[idx, line_idx] = True
                y_residual[idx, line_idx] = int(reachable)

    return {
        "y_residual_reachable": y_residual,
        "loss_mask": residual_mask,
        "n1_critical_mask": repeated_n1_mask,
        "known_s0_labels": known_s0_labels,
        "active_first_line": active_first_line,
        "active_first_line_source": active_source,
    }


def subset_counts(
    y: np.ndarray,
    mask: np.ndarray,
    sample_type: np.ndarray,
    split: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for split_name in ("train", "validation", "test", "all"):
        for sample_name in ("S0", "S1", "all"):
            selected = np.ones(len(y), dtype=bool)
            if split_name != "all":
                selected &= split == split_name
            if sample_name != "all":
                selected &= sample_type == sample_name
            active = mask[selected]
            labels = y[selected]
            candidates = int(active.sum())
            positives = int(labels[active].sum()) if candidates else 0
            rows.append(
                {
                    "split": split_name,
                    "sample_type": sample_name,
                    "num_state_samples": int(selected.sum()),
                    "num_candidate_labels": candidates,
                    "num_positive_labels": positives,
                    "positive_ratio": positives / max(candidates, 1),
                }
            )
    return rows


def convert(args: argparse.Namespace) -> dict[str, Any]:
    require_file(args.source_dataset_npz, "source paper-aligned IEEE118 dataset NPZ")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = np.load(args.source_dataset_npz, allow_pickle=True)
    converted = build_residual_labels(data)
    y = converted["y_residual_reachable"]
    mask = converted["loss_mask"]
    sample_type = data["sample_type"].astype(str)
    split = data["split"].astype(str)
    seed = data["seed"].astype(np.int64)

    output_npz = args.output_dir / "ieee118_residual_reachable_gcn_dataset.npz"
    payload = {name: data[name] for name in data.files if name not in {"y_gcn", "y_critical", "loss_mask", "active_first_line"}}
    payload.update(
        {
            "y_gcn": y,
            "y_residual_reachable": y,
            "source_y_gcn": data["y_gcn"].astype(np.int64),
            "source_loss_mask": data["loss_mask"].astype(bool),
            "loss_mask": mask,
            "n1_critical_mask": converted["n1_critical_mask"],
            "known_s0_labels": converted["known_s0_labels"],
            "active_first_line": converted["active_first_line"],
            "active_first_line_source": converted["active_first_line_source"],
        }
    )
    np.savez(output_npz, **payload)

    rows = []
    for idx in range(len(y)):
        active = mask[idx]
        rows.append(
            {
                "sample_index": idx,
                "seed": int(seed[idx]),
                "split": str(split[idx]),
                "sample_type": str(sample_type[idx]),
                "active_first_line": str(converted["active_first_line"][idx]),
                "active_first_line_source": str(converted["active_first_line_source"][idx]),
                "current_outage_labels": str(data["current_outage_labels"][idx]),
                "num_n1_critical_lines": int(converted["n1_critical_mask"][idx].sum()),
                "num_residual_candidate_labels": int(active.sum()),
                "num_residual_positive_labels": int(y[idx][active].sum()),
            }
        )
    sample_summary = pd.DataFrame(rows)
    sample_summary.to_csv(
        args.output_dir / "ieee118_residual_reachable_sample_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    count_rows = subset_counts(y, mask, sample_type, split)
    pd.DataFrame(count_rows).to_csv(
        args.output_dir / "ieee118_residual_reachable_label_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    source_normalizer = args.source_normalizer_json or args.source_dataset_npz.with_name(
        "ieee118_paper_gcn_feature_normalizer.json"
    )
    output_normalizer: str | None = None
    if source_normalizer.exists():
        output_path = args.output_dir / "ieee118_residual_reachable_feature_normalizer.json"
        output_path.write_text(source_normalizer.read_text(encoding="utf-8"), encoding="utf-8")
        output_normalizer = str(output_path)

    active_known = (sample_type == "S1") & (np.char.str_len(converted["active_first_line"].astype(str)) > 0)
    s0 = sample_type == "S0"
    s1 = sample_type == "S1"
    metadata: dict[str, Any] = {
        "status": "complete",
        "source_dataset_npz": str(args.source_dataset_npz),
        "dataset_npz": str(output_npz),
        "feature_normalizer_json": output_normalizer,
        "model_contract": "Original RTS-79 PaperStyleRts79Gcn; labels change by active depth, model structure does not.",
        "target_semantics": {
            "S0": "candidate first line can reach a residual critical N-2 outcome",
            "S1": "candidate second line is critical after masking S0 N-1-critical lines",
        },
        "num_state_samples": int(len(y)),
        "num_s0_samples": int(s0.sum()),
        "num_s1_samples": int(s1.sum()),
        "num_known_s0_candidate_labels": int(converted["known_s0_labels"].sum()),
        "num_positive_s0_reachable_labels": int(y[s0][mask[s0]].sum()),
        "num_residual_s1_candidate_labels": int(mask[s1].sum()),
        "num_residual_s1_positive_labels": int(y[s1][mask[s1]].sum()),
        "num_s1_active_first_line_known": int(active_known.sum()),
        "num_s1_active_first_line_unknown": int(s1.sum() - active_known.sum()),
        "active_first_line_policy": "explicit when stored; otherwise infer only from a single outage label; ambiguous samples remain unknown",
        "unknown_s0_policy": "mask unknown; never fill unknown reachable labels with zero",
        "train_seeds": sorted(int(value) for value in np.unique(seed[split == "train"])),
        "validation_seeds": sorted(int(value) for value in np.unique(seed[split == "validation"])),
        "test_seeds": sorted(int(value) for value in np.unique(seed[split == "test"])),
        "large_npz_tracked_in_git": False,
        "label_summary": count_rows,
    }
    (args.output_dir / "ieee118_residual_reachable_dataset_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_residual_reachable_dataset_schema.md").write_text(
        "# IEEE118 Residual Reachable Dataset Schema\n\n"
        "- `x_gcn`: unchanged paper-style state features.\n"
        "- `y_gcn` / `y_residual_reachable`: S0 residual-reachable labels and S1 residual critical labels.\n"
        "- `loss_mask`: excludes invalid candidates and N-1-critical second lines.\n"
        "- `n1_critical_mask`: per-sample copy of the same-seed S0 N-1 critical line mask.\n"
        "- `known_s0_labels`: distinguishes observed S0 reachable labels from unknown candidates.\n"
        "- `active_first_line`: explicit active outage when known; never inferred from ambiguous passive outages.\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    args = parse_args()
    print(json.dumps(convert(args), indent=2))


if __name__ == "__main__":
    main()
