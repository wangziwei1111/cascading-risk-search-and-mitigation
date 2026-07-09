from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_ieee118_first_line_fragility_dataset import (
    infer_unique_first_line,
    load_fulltruth_fragility,
    require_file,
)


DEFAULT_BASE = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
DEFAULT_PILOT = DEFAULT_BASE / "pilot_2000"
DEFAULT_EARLYSTOP = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
DEFAULT_PATH_INDEX = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
DEFAULT_OUTPUT = DEFAULT_BASE / "strict_fragility_targets"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build non-degenerate strict IEEE118 first-line fragility targets.")
    parser.add_argument("--paper-gcn-dataset-npz", type=Path, default=DEFAULT_PILOT / "ieee118_paper_gcn_dataset.npz")
    parser.add_argument("--paper-gcn-dataset-metadata-json", type=Path, default=DEFAULT_PILOT / "ieee118_paper_gcn_dataset_metadata.json")
    parser.add_argument("--fulltruth-csv", type=Path, default=DEFAULT_EARLYSTOP / "ieee118_fulltruth_summary.csv")
    parser.add_argument("--path-index-csv", type=Path, default=DEFAULT_PATH_INDEX / "ieee118_rts79_gcn_path_index.csv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--heldout-test-seed", type=int, default=20260708)
    parser.add_argument(
        "--target-modes",
        nargs="+",
        default=["critical_count_topq", "relay_count_topq", "max_shed_topq", "composite_topq"],
    )
    parser.add_argument("--top-quantiles", type=float, nargs="+", default=[0.10, 0.20, 0.30])
    return parser.parse_args()


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    std = float(numeric.std(ddof=0))
    if std <= 1e-12:
        return pd.Series(np.zeros(len(numeric)), index=values.index)
    return (numeric - float(numeric.mean())) / std


def topq_labels(values: pd.Series, q: float, mask: pd.Series) -> pd.Series:
    labels = pd.Series(0, index=values.index, dtype=np.int64)
    active = values.loc[mask].astype(float)
    if active.empty:
        return labels
    top_n = max(1, int(np.ceil(len(active) * float(q))))
    order = active.sort_values(ascending=False, kind="mergesort")
    labels.loc[order.index[:top_n]] = 1
    return labels


def target_name(mode: str, q: float) -> str:
    return f"{mode.replace('_topq', '')}_top{int(round(q * 100)):02d}"


def build_sampled_stats(data: Any, s0_index: int, line_labels: list[str]) -> pd.DataFrame:
    y = data["y_gcn"].astype(np.int64)
    mask = data["loss_mask"].astype(bool)
    sample_type = data["sample_type"].astype(str)
    seed_array = data["seed"].astype(np.int64)
    current_outages = data["current_outage_labels"].astype(str)
    seed = int(seed_array[s0_index])
    direct = (y[s0_index].astype(int) == 1) & mask[s0_index]
    rows = []
    for line_idx, line in enumerate(line_labels):
        rows.append(
            {
                "seed": seed,
                "line_label": line,
                "line_index": line_idx,
                "first_step_critical": bool(direct[line_idx]),
                "first_step_direct_shed_label": int(direct[line_idx]),
                "loss_mask": False,
                "critical_count": 0,
                "relay_cascade_count": 0,
                "max_load_shed_mw": 0.0,
                "sum_load_shed_mw": 0.0,
                "mean_load_shed_mw": 0.0,
                "max_p_second_for_critical_paths": 0.0,
                "mean_p_second_for_critical_paths": 0.0,
                "num_valid_second_paths": 0,
                "source": "sampled_s1",
            }
        )
    by_line = {row["line_label"]: row for row in rows}
    s1_indices = np.where((seed_array == seed) & (sample_type == "S1"))[0]
    for sample_idx in s1_indices:
        first_line = infer_unique_first_line(str(current_outages[sample_idx]), line_labels)
        if first_line is None:
            continue
        row = by_line[first_line]
        if row["first_step_critical"]:
            continue
        active = mask[sample_idx]
        positives = y[sample_idx].astype(int) & active.astype(int)
        row["loss_mask"] = True
        row["num_valid_second_paths"] = int(active.sum())
        row["critical_count"] = int(positives.sum())
        # The pilot-2000 sampled dataset stores critical labels but not relay-specific labels or load shed.
        row["relay_cascade_count"] = int(positives.sum())
        row["max_p_second_for_critical_paths"] = float(positives.max()) if int(positives.sum()) else 0.0
        row["mean_p_second_for_critical_paths"] = float(positives[active].mean()) if int(active.sum()) else 0.0
    return pd.DataFrame(rows)


def build_fulltruth_stats(fulltruth_csv: Path, path_index_csv: Path, line_labels: list[str], heldout_seed: int) -> pd.DataFrame | None:
    if not fulltruth_csv.exists() or not path_index_csv.exists():
        return None
    truth = pd.read_csv(fulltruth_csv)
    path_index = pd.read_csv(path_index_csv)
    merged = path_index[["seed", "path", "first_line", "second_line"]].rename(columns={"seed": "path_seed"}).merge(
        truth,
        on=["path", "first_line", "second_line"],
        how="left",
    )
    merged["seed"] = pd.to_numeric(merged["path_seed"], errors="coerce")
    merged = merged.loc[merged["seed"].eq(int(heldout_seed))].copy()
    if merged.empty:
        return None
    merged["critical"] = coerce_bool(merged["critical"])
    merged["relay_cascade"] = coerce_bool(merged.get("relay_cascade", pd.Series(False, index=merged.index)))
    merged["total_load_shed_mw"] = pd.to_numeric(merged.get("total_load_shed_mw", 0.0), errors="coerce").fillna(0.0)
    merged["first_step_critical"] = coerce_bool(merged.get("first_step_critical", pd.Series(False, index=merged.index)))
    rows = []
    for line_idx, line in enumerate(line_labels):
        group = merged.loc[merged["first_line"].astype(str).eq(line)]
        first_step = bool(group["first_step_critical"].any()) if not group.empty else False
        critical = group.loc[group["critical"]]
        rows.append(
            {
                "seed": int(heldout_seed),
                "line_label": line,
                "line_index": line_idx,
                "first_step_critical": first_step,
                "first_step_direct_shed_label": int(first_step),
                "loss_mask": bool((not first_step) and len(group) > 0),
                "critical_count": int(group["critical"].sum()) if len(group) else 0,
                "relay_cascade_count": int(group["relay_cascade"].sum()) if len(group) else 0,
                "max_load_shed_mw": float(group["total_load_shed_mw"].max()) if len(group) else 0.0,
                "sum_load_shed_mw": float(group["total_load_shed_mw"].sum()) if len(group) else 0.0,
                "mean_load_shed_mw": float(group.loc[group["critical"], "total_load_shed_mw"].mean()) if len(critical) else 0.0,
                "max_p_second_for_critical_paths": 0.0,
                "mean_p_second_for_critical_paths": 0.0,
                "num_valid_second_paths": int(len(group)),
                "source": "fulltruth",
            }
        )
    return pd.DataFrame(rows)


def add_ratios_and_composite(stats: pd.DataFrame) -> pd.DataFrame:
    out = stats.copy()
    denom = pd.to_numeric(out["num_valid_second_paths"], errors="coerce").replace(0, np.nan)
    out["critical_ratio"] = (out["critical_count"] / denom).fillna(0.0)
    out["relay_ratio"] = (out["relay_cascade_count"] / denom).fillna(0.0)
    out["composite_score"] = 0.0
    for _, group in out.groupby("seed", sort=False):
        active = group["loss_mask"].astype(bool)
        comp = (
            zscore(group.loc[active, "critical_count"])
            + zscore(group.loc[active, "relay_cascade_count"])
            + zscore(group.loc[active, "max_load_shed_mw"])
            + zscore(group.loc[active, "sum_load_shed_mw"])
        )
        out.loc[comp.index, "composite_score"] = comp
    return out


def build_labels(stats: pd.DataFrame, target_modes: list[str], top_quantiles: list[float]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    out = stats.copy()
    summaries = []
    mode_to_metric = {
        "critical_count_topq": "critical_count",
        "relay_count_topq": "relay_cascade_count",
        "max_shed_topq": "max_load_shed_mw",
        "composite_topq": "composite_score",
    }
    for mode in target_modes:
        if mode not in mode_to_metric:
            raise ValueError(f"Unsupported target mode: {mode}")
        metric = mode_to_metric[mode]
        for q in top_quantiles:
            name = target_name(mode, q)
            out[name] = 0
            for _, group in out.groupby("seed", sort=False):
                labels = topq_labels(group[metric], q, group["loss_mask"].astype(bool))
                out.loc[group.index, name] = labels
            active = out["loss_mask"].astype(bool)
            positive = int(out.loc[active, name].sum())
            total = int(active.sum())
            negative = total - positive
            summaries.append(
                {
                    "target_name": name,
                    "target_mode": mode,
                    "top_quantile": float(q),
                    "metric": metric,
                    "num_positive": positive,
                    "num_negative": negative,
                    "positive_ratio": positive / max(total, 1),
                    "num_s0_samples": int(out["seed"].nunique()),
                    "num_known_first_line_labels": total,
                    "num_first_step_critical_excluded": int((out["first_step_critical"].astype(bool) & ~out["loss_mask"].astype(bool)).sum()),
                    "degenerate": bool(positive == 0 or negative == 0),
                    "trainable": bool(positive > 0 and negative > 0),
                }
            )
    return out, summaries


def build_strict_targets(args: argparse.Namespace) -> dict[str, Any]:
    require_file(args.paper_gcn_dataset_npz, "paper GCN dataset NPZ")
    require_file(args.paper_gcn_dataset_metadata_json, "paper GCN dataset metadata JSON")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metadata_in = json.loads(args.paper_gcn_dataset_metadata_json.read_text(encoding="utf-8"))
    data = np.load(args.paper_gcn_dataset_npz, allow_pickle=True)
    line_labels = [str(label) for label in data["line_labels"].tolist()]
    sample_type = data["sample_type"].astype(str)
    s0_indices = np.where(sample_type == "S0")[0]
    frames = []
    fulltruth_stats = build_fulltruth_stats(args.fulltruth_csv, args.path_index_csv, line_labels, args.heldout_test_seed)
    for s0_idx in s0_indices:
        seed = int(data["seed"][s0_idx])
        if fulltruth_stats is not None and seed == int(args.heldout_test_seed):
            frames.append(fulltruth_stats)
        else:
            frames.append(build_sampled_stats(data, int(s0_idx), line_labels))
    stats = add_ratios_and_composite(pd.concat(frames, ignore_index=True))
    labeled, summaries = build_labels(stats, args.target_modes, args.top_quantiles)
    summary = pd.DataFrame(summaries)
    target_names = summary["target_name"].astype(str).tolist()

    seed_to_s0 = {int(data["seed"][idx]): idx for idx in s0_indices}
    x_rows = []
    split_rows = []
    seed_rows = []
    y_targets = np.zeros((len(target_names), len(s0_indices), len(line_labels)), dtype=np.int64)
    loss_masks = np.zeros_like(y_targets, dtype=bool)
    direct = np.zeros((len(s0_indices), len(line_labels)), dtype=np.int64)
    for sample_out_idx, s0_idx in enumerate(s0_indices):
        seed = int(data["seed"][s0_idx])
        group = labeled.loc[labeled["seed"].eq(seed)].sort_values("line_index")
        x_rows.append(data["x_gcn"][s0_idx])
        split_rows.append(str(data["split"][s0_idx]))
        seed_rows.append(seed)
        direct[sample_out_idx] = group["first_step_direct_shed_label"].to_numpy(dtype=np.int64)
        for target_idx, name in enumerate(target_names):
            y_targets[target_idx, sample_out_idx] = group[name].to_numpy(dtype=np.int64)
            loss_masks[target_idx, sample_out_idx] = group["loss_mask"].to_numpy(dtype=bool)
    np.savez(
        args.output_dir / "ieee118_strict_fragility_targets_dataset.npz",
        x_gcn=np.stack(x_rows).astype(np.float32),
        y_targets=y_targets,
        loss_masks=loss_masks,
        first_step_direct_shed_label=direct,
        seed=np.asarray(seed_rows, dtype=np.int64),
        split=np.asarray(split_rows, dtype=str),
        target_names=np.asarray(target_names, dtype=str),
        target_modes=summary["target_mode"].astype(str).to_numpy(),
        top_quantiles=summary["top_quantile"].to_numpy(dtype=np.float32),
        line_labels=np.asarray(line_labels, dtype=str),
        branch_from_bus=data["branch_from_bus"],
        branch_to_bus=data["branch_to_bus"],
        feature_names=data["feature_names"],
    )
    labeled.to_csv(args.output_dir / "ieee118_strict_fragility_line_stats_compact.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(args.output_dir / "ieee118_strict_fragility_target_summary.csv", index=False, encoding="utf-8-sig")
    metadata = {
        "case_name": "ieee118",
        "source_paper_gcn_dataset_npz": str(args.paper_gcn_dataset_npz),
        "source_fulltruth_csv": str(args.fulltruth_csv) if args.fulltruth_csv.exists() else None,
        "source_path_index_csv": str(args.path_index_csv) if args.path_index_csv.exists() else None,
        "dataset_npz": str(args.output_dir / "ieee118_strict_fragility_targets_dataset.npz"),
        "num_s0_samples": int(len(s0_indices)),
        "num_known_first_line_labels": int(labeled["loss_mask"].sum()),
        "num_first_step_critical_excluded": int((labeled["first_step_critical"].astype(bool) & ~labeled["loss_mask"].astype(bool)).sum()),
        "target_modes": args.target_modes,
        "top_quantiles": [float(q) for q in args.top_quantiles],
        "target_summaries": summaries,
        "non_degenerate_targets": summary.loc[~summary["degenerate"], "target_name"].astype(str).tolist(),
        "degenerate_targets": summary.loc[summary["degenerate"], "target_name"].astype(str).tolist(),
        "heldout_test_seed": int(args.heldout_test_seed),
        "heldout_fulltruth_labels_used": fulltruth_stats is not None,
        "feature_mode": metadata_in.get("feature_mode", "paper"),
        "input_channels": int(data["x_gcn"].shape[2]),
        "large_npz_tracked_in_git": False,
    }
    (args.output_dir / "ieee118_strict_fragility_target_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (args.output_dir / "ieee118_strict_fragility_target_schema.md").write_text(
        "# IEEE118 Strict Fragility Target Schema\n\n"
        "- `critical_count_topq`: top quantile by number of critical second outages.\n"
        "- `relay_count_topq`: top quantile by relay-cascade second outages.\n"
        "- `max_shed_topq`: top quantile by maximum load shed.\n"
        "- `composite_topq`: top quantile by z-scored critical count, relay count, max shed, and sum shed.\n"
        "- First-step critical lines are excluded from loss and retained as direct-shed diagnostics.\n"
        "\nNote: sampled train/validation S1 labels from the pilot dataset contain critical labels, "
        "but not relay-specific labels or load-shed severity. The held-out 20260708 seed uses complete "
        "full-truth relay/load-shed fields; sampled relay/load-shed targets should therefore be treated "
        "as pilot diagnostics, not final severity labels.\n",
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_strict_fragility_target_readme.md").write_text(
        "# IEEE118 Strict First-Line Fragility Targets\n\n"
        "This target builder replaces PR #17's degenerate any-critical label with top-quantile targets. "
        "It reuses existing paper-aligned/full-truth artifacts and does not rerun OPA. The generated NPZ is local-only.\n\n"
        "First-step critical lines are excluded from training loss and retained as direct-shed diagnostics. "
        "The sampled pilot S1 data only stores second-step critical labels, so relay/load-shed strict targets "
        "are complete for the held-out full-truth seed and diagnostic for sampled train/validation seeds.\n",
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    print(json.dumps(build_strict_targets(parse_args()), indent=2))


if __name__ == "__main__":
    main()
