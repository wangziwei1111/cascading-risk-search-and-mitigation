from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
DEFAULT_PILOT = DEFAULT_BASE / "pilot_2000"
DEFAULT_EARLYSTOP = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
DEFAULT_PATH_INDEX = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
DEFAULT_OUTPUT = DEFAULT_BASE / "first_line_fragility"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build IEEE118 first-line fragility labels from existing paper-aligned artifacts.")
    parser.add_argument("--paper-gcn-dataset-npz", type=Path, default=DEFAULT_PILOT / "ieee118_paper_gcn_dataset.npz")
    parser.add_argument("--paper-gcn-dataset-metadata-json", type=Path, default=DEFAULT_PILOT / "ieee118_paper_gcn_dataset_metadata.json")
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_EARLYSTOP / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_PATH_INDEX / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--heldout-test-seed", type=int, default=20260708)
    parser.add_argument("--label-mode", choices=["valid_n2_any_critical"], default="valid_n2_any_critical")
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. The fragility builder reuses local paper-aligned/full-truth artifacts "
            "and will not rerun OPA or regenerate large datasets."
        )


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def read_json(path: Path) -> dict[str, Any]:
    require_file(path, "paper GCN dataset metadata JSON")
    return json.loads(path.read_text(encoding="utf-8"))


def split_labels(value: Any) -> list[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    return [token.strip() for token in str(value).split(",") if token.strip()]


def infer_unique_first_line(current_outage_labels: str, line_labels: list[str]) -> str | None:
    labels = split_labels(current_outage_labels)
    if len(labels) == 1 and labels[0] in set(line_labels):
        return labels[0]
    return None


def load_fulltruth_fragility(
    fulltruth_csv: Path,
    path_index_csv: Path,
    *,
    line_labels: list[str],
    heldout_test_seed: int,
) -> dict[int, dict[str, dict[str, Any]]]:
    if not fulltruth_csv.exists() or not path_index_csv.exists():
        return {}
    truth = pd.read_csv(fulltruth_csv)
    path_index = pd.read_csv(path_index_csv)
    if "seed" not in path_index.columns:
        return {}
    if "valid_ordered_n2" in truth.columns:
        truth = truth.loc[coerce_bool(truth["valid_ordered_n2"])].copy()
    merged = path_index[["seed", "path", "first_line", "second_line"]].merge(
        truth,
        on=["path", "first_line", "second_line"],
        how="left",
        suffixes=("", "_truth"),
    )
    if "critical" not in merged.columns:
        return {}
    merged["critical"] = coerce_bool(merged["critical"])
    merged["relay_cascade"] = coerce_bool(merged.get("relay_cascade", pd.Series(False, index=merged.index)))
    merged["total_load_shed_mw"] = pd.to_numeric(merged.get("total_load_shed_mw", 0.0), errors="coerce").fillna(0.0)
    if "first_step_critical" in merged.columns:
        merged["first_step_critical"] = coerce_bool(merged["first_step_critical"])
    else:
        merged["first_step_critical"] = False

    out: dict[int, dict[str, dict[str, Any]]] = {}
    for seed, seed_group in merged.groupby("seed"):
        seed_int = int(seed)
        if seed_int != int(heldout_test_seed):
            continue
        line_rows: dict[str, dict[str, Any]] = {}
        for line in line_labels:
            group = seed_group.loc[seed_group["first_line"].astype(str).eq(line)]
            if group.empty:
                continue
            first_step_critical = bool(group["first_step_critical"].any())
            critical = group.loc[group["critical"]]
            line_rows[line] = {
                "source": "fulltruth",
                "fragility_label": int((not first_step_critical) and len(critical) > 0),
                "loss_mask": bool(not first_step_critical),
                "first_step_direct_shed_label": int(first_step_critical),
                "first_step_critical": bool(first_step_critical),
                "num_valid_second_critical": int(len(critical)),
                "max_second_load_shed_mw": float(critical["total_load_shed_mw"].max()) if len(critical) else 0.0,
                "num_valid_second_relay_cascade": int(group["relay_cascade"].sum()),
            }
        out[seed_int] = line_rows
    return out


def build_sampled_fragility_for_seed(
    *,
    seed: int,
    data: Any,
    s0_index: int,
    line_labels: list[str],
) -> dict[str, dict[str, Any]]:
    y = data["y_gcn"].astype(np.int64)
    loss_mask = data["loss_mask"].astype(bool)
    sample_type = data["sample_type"].astype(str)
    seed_array = data["seed"].astype(np.int64)
    current_outages = data["current_outage_labels"].astype(str)

    direct = (y[s0_index].astype(int) == 1) & loss_mask[s0_index]
    line_rows: dict[str, dict[str, Any]] = {}
    for idx, label in enumerate(line_labels):
        line_rows[label] = {
            "source": "sampled_s1",
            "fragility_label": 0,
            "loss_mask": False,
            "first_step_direct_shed_label": int(direct[idx]),
            "first_step_critical": bool(direct[idx]),
            "num_valid_second_critical": 0,
            "max_second_load_shed_mw": 0.0,
            "num_valid_second_relay_cascade": 0,
        }

    s1_indices = np.where((seed_array == int(seed)) & (sample_type == "S1"))[0]
    label_to_index = {label: idx for idx, label in enumerate(line_labels)}
    for sample_idx in s1_indices:
        first_line = infer_unique_first_line(str(current_outages[sample_idx]), line_labels)
        if first_line is None:
            continue
        first_idx = label_to_index[first_line]
        if direct[first_idx]:
            continue
        positive_count = int(y[sample_idx][loss_mask[sample_idx]].sum())
        row = line_rows[first_line]
        row["loss_mask"] = True
        row["fragility_label"] = int(positive_count > 0)
        row["num_valid_second_critical"] = positive_count
    return line_rows


def rows_to_arrays(
    *,
    data: Any,
    s0_indices: np.ndarray,
    line_labels: list[str],
    fulltruth_by_seed: dict[int, dict[str, dict[str, Any]]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    y_rows = []
    mask_rows = []
    direct_rows = []
    diagnostics: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {"fulltruth": 0, "sampled_s1": 0}
    seed_array = data["seed"].astype(np.int64)

    for output_sample_idx, s0_idx in enumerate(s0_indices):
        seed = int(seed_array[s0_idx])
        if seed in fulltruth_by_seed:
            label_rows = fulltruth_by_seed[seed]
        else:
            label_rows = build_sampled_fragility_for_seed(seed=seed, data=data, s0_index=int(s0_idx), line_labels=line_labels)
        y = np.zeros(len(line_labels), dtype=np.int64)
        mask = np.zeros(len(line_labels), dtype=bool)
        direct = np.zeros(len(line_labels), dtype=np.int64)
        for line_idx, label in enumerate(line_labels):
            row = label_rows.get(label)
            if row is None:
                continue
            y[line_idx] = int(row["fragility_label"])
            mask[line_idx] = bool(row["loss_mask"])
            direct[line_idx] = int(row["first_step_direct_shed_label"])
            source_counts[str(row["source"])] = source_counts.get(str(row["source"]), 0) + 1
            diagnostics.append(
                {
                    "sample_index": output_sample_idx,
                    "seed": seed,
                    "line_label": label,
                    "line_index": line_idx,
                    **row,
                }
            )
        y_rows.append(y)
        mask_rows.append(mask)
        direct_rows.append(direct)
    return (
        np.stack(y_rows).astype(np.int64),
        np.stack(mask_rows).astype(bool),
        np.stack(direct_rows).astype(np.int64),
        np.asarray([data["seed"][idx] for idx in s0_indices], dtype=np.int64),
        diagnostics,
        source_counts,
    )


def build_fragility_dataset(args: argparse.Namespace) -> dict[str, Any]:
    if args.label_mode != "valid_n2_any_critical":
        raise ValueError(f"Unsupported label mode: {args.label_mode}")
    require_file(args.paper_gcn_dataset_npz, "paper GCN dataset NPZ")
    metadata_in = read_json(args.paper_gcn_dataset_metadata_json)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(args.paper_gcn_dataset_npz, allow_pickle=True)
    sample_type = data["sample_type"].astype(str)
    s0_indices = np.where(sample_type == "S0")[0]
    if len(s0_indices) == 0:
        raise ValueError("Paper GCN dataset contains no S0 samples for fragility training.")
    line_labels = [str(label) for label in data["line_labels"].tolist()]
    fulltruth_by_seed = load_fulltruth_fragility(
        args.fulltruth_csv,
        args.path_index_csv,
        line_labels=line_labels,
        heldout_test_seed=args.heldout_test_seed,
    )
    y, mask, direct, s0_seeds, diagnostics, source_counts = rows_to_arrays(
        data=data,
        s0_indices=s0_indices,
        line_labels=line_labels,
        fulltruth_by_seed=fulltruth_by_seed,
    )
    split = data["split"].astype(str)[s0_indices]
    x = data["x_gcn"].astype(np.float32)[s0_indices]
    np.savez(
        args.output_dir / "ieee118_first_line_fragility_dataset.npz",
        x_gcn=x,
        y_gcn=y,
        y_fragile=y,
        loss_mask=mask,
        first_step_direct_shed_label=direct,
        seed=s0_seeds,
        split=split,
        sample_type=np.asarray(["S0"] * len(s0_indices), dtype=str),
        line_labels=np.asarray(line_labels, dtype=str),
        branch_from_bus=data["branch_from_bus"],
        branch_to_bus=data["branch_to_bus"],
        feature_names=data["feature_names"],
    )
    diag = pd.DataFrame(diagnostics)
    diag.to_csv(args.output_dir / "ieee118_first_line_fragility_line_labels_compact.csv", index=False, encoding="utf-8-sig")
    active = mask.astype(bool)
    positive = int(y[active].sum())
    negative = int(active.sum() - positive)
    train_seeds = sorted(set(int(seed) for seed in s0_seeds[split == "train"]))
    validation_seeds = sorted(set(int(seed) for seed in s0_seeds[split == "validation"]))
    test_seeds = sorted(set(int(seed) for seed in s0_seeds[split == "test"]))
    metadata = {
        "case_name": "ieee118",
        "dataset_npz": str(args.output_dir / "ieee118_first_line_fragility_dataset.npz"),
        "source_paper_gcn_dataset_npz": str(args.paper_gcn_dataset_npz),
        "source_paper_gcn_dataset_metadata_json": str(args.paper_gcn_dataset_metadata_json),
        "source_fulltruth_csv": str(args.fulltruth_csv) if args.fulltruth_csv.exists() else None,
        "source_path_index_csv": str(args.path_index_csv) if args.path_index_csv.exists() else None,
        "num_s0_samples": int(len(s0_indices)),
        "num_train_s0_samples": int((split == "train").sum()),
        "num_validation_s0_samples": int((split == "validation").sum()),
        "num_test_s0_samples": int((split == "test").sum()),
        "num_known_first_line_labels": int(active.sum()),
        "num_positive_fragility_labels": positive,
        "num_negative_fragility_labels": negative,
        "fragility_positive_ratio": positive / max(int(active.sum()), 1),
        "num_first_step_critical_excluded": int((direct.astype(bool) & ~mask).sum()),
        "num_direct_shed_labels": int(direct.sum()),
        "train_seeds": train_seeds,
        "validation_seeds": validation_seeds,
        "test_seeds": test_seeds,
        "heldout_test_seed": int(args.heldout_test_seed),
        "feature_mode": metadata_in.get("feature_mode", "paper"),
        "input_channels": int(x.shape[2]),
        "label_mode": args.label_mode,
        "label_sources": source_counts,
        "heldout_fulltruth_labels_used": int(args.heldout_test_seed) in fulltruth_by_seed,
        "large_npz_tracked_in_git": False,
    }
    (args.output_dir / "ieee118_first_line_fragility_dataset_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (args.output_dir / "ieee118_first_line_fragility_dataset_schema.md").write_text(
        "# IEEE118 First-Line Fragility Dataset Schema\n\n"
        "- `x_gcn`: S0 graph features, shape `num_s0_samples x 186 x input_channels`.\n"
        "- `y_fragile` / `y_gcn`: first-line fragility labels. A positive label means the first line is not first-step critical and has at least one valid critical second outage.\n"
        "- `loss_mask`: known non-first-step-critical first-line labels used in fragility loss.\n"
        "- `first_step_direct_shed_label`: direct S0 load-shed labels retained for diagnostics but excluded from fragility loss.\n"
        "- Splits are inherited by seed from the paper-aligned dataset.\n",
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_first_line_fragility_readme.md").write_text(
        "# IEEE118 First-Line Fragility Dataset\n\n"
        "This dataset reuses existing paper-aligned S0 graph features and builds first-line fragility labels without rerunning OPA. "
        "Training/validation labels come from sampled pilot-2000 S1 labels when a unique first line can be inferred. "
        "The held-out seed uses complete full-truth labels when the local full-truth/path-index files are available. "
        "The NPZ is local-only; committed files are compact metadata/schema/diagnostics.\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    args = parse_args()
    print(json.dumps(build_fragility_dataset(args), indent=2))


if __name__ == "__main__":
    main()
