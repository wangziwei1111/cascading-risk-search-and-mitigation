from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS, F_BUS, PF, T_BUS
from pypower.idx_bus import PD


ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECKPOINT_VERSION = 1
CHECKPOINT_DIRNAME = "paper_gcn_checkpoint_shards"
CHECKPOINT_PROGRESS_NAME = "ieee118_paper_gcn_checkpoint.json"

from build_ieee118_step2_state_dataset import build_edge_features, build_node_features
from case_adapter import build_case_adapter, run_sequential_outages_for_case
from convert_ieee118_step2_to_rts79_gcn_format import PAPER_FEATURE_NAMES, build_x_from_json, fit_normalizer, normalize_x
from generate_ieee118_ordered_n2_fulltruth import apply_thermal_limit_mode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build paper-aligned IEEE118 S0+S1 GCN training states.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[20260701, 20260702, 20260703, 20260708])
    parser.add_argument("--num-load-scenarios", type=int, default=None)
    parser.add_argument("--samples-per-scenario", type=int, default=None)
    parser.add_argument("--target-state-samples", type=int, default=200)
    parser.add_argument("--load-scale", type=float, default=1.1)
    parser.add_argument("--load-random-low", type=float, default=0.9)
    parser.add_argument("--load-random-high", type=float, default=1.1)
    parser.add_argument("--limit-mode", choices=["original_rate_a", "flow_scaled"], default="flow_scaled")
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--first-step-critical-policy", choices=["skip", "expand"], default="skip")
    parser.add_argument("--feature-mode", choices=["paper", "physics"], default="paper")
    parser.add_argument("--sample-seed", type=int, default=20260708)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--train-seeds", type=int, nargs="*", default=None)
    parser.add_argument("--validation-seeds", type=int, nargs="*", default=None)
    parser.add_argument("--test-seeds", type=int, nargs="*", default=[20260708])
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_training",
    )
    return parser.parse_args()


def apply_load_scenario(case: dict, *, seed: int, load_scale: float, low: float, high: float) -> dict:
    scenario = {key: value.copy() if hasattr(value, "copy") else value for key, value in case.items()}
    bus = scenario["bus"].copy()
    rng = np.random.default_rng(seed)
    bus[:, PD] = bus[:, PD] * load_scale * rng.uniform(low, high, size=bus.shape[0])
    scenario["bus"] = bus
    return scenario


def bool_critical(state: dict) -> bool:
    return float(state.get("island_load_shed_mw", 0.0)) + float(state.get("redispatch_load_shed_mw", 0.0)) > 1e-7


def final_outage_set(state: dict) -> set[str]:
    labels = state.get("final_outage_labels", ())
    if isinstance(labels, str):
        return {token.strip() for token in labels.split(",") if token.strip()}
    return {str(label) for label in labels}


def state_features(case: dict, adapter: Any, current_outages: set[str], feature_mode: str, beta: float, security_limit: float) -> tuple[np.ndarray, list[str], np.ndarray, np.ndarray]:
    first = next(iter(current_outages), "")
    node_json = json.dumps(build_node_features(case), separators=(",", ":"), sort_keys=True)
    edge_json = json.dumps(build_edge_features(case, adapter, first_line=first, second_line=""), separators=(",", ":"), sort_keys=True)
    return build_x_from_json(edge_json, node_json, beta=beta, security_limit=security_limit, feature_mode=feature_mode)


def split_seed_sets(args: argparse.Namespace) -> tuple[set[int], set[int], set[int]]:
    seeds = [int(seed) for seed in args.seeds]
    test = set(int(seed) for seed in (args.test_seeds or []))
    remaining = [seed for seed in seeds if seed not in test]
    if args.train_seeds is not None or args.validation_seeds is not None:
        train = set(int(seed) for seed in (args.train_seeds or []))
        validation = set(int(seed) for seed in (args.validation_seeds or []))
    else:
        validation = {remaining[-1]} if len(remaining) > 1 else set()
        train = set(remaining[:-1] if validation else remaining)
    overlap = (train & validation) | (train & test) | (validation & test)
    if overlap:
        raise ValueError(f"Seed leakage across train/validation/test splits: {sorted(overlap)}")
    return train, validation, test


def split_name(seed: int, train: set[int], validation: set[int], test: set[int]) -> str:
    if seed in train:
        return "train"
    if seed in validation:
        return "validation"
    if seed in test:
        return "test"
    return "unused"


def append_sample(
    rows: list[dict[str, Any]],
    x_raw: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    *,
    seed: int,
    sample_type: str,
    split: str,
    current_outages: set[str],
    line_labels: list[str],
    active_first_line: str = "",
) -> None:
    rows.append(
        {
            "sample_index": len(rows),
            "seed": int(seed),
            "split": split,
            "sample_type": sample_type,
            "active_first_line": str(active_first_line),
            "current_outage_labels": ",".join(sorted(current_outages)),
            "x_raw": x_raw,
            "y": y.astype(np.int64),
            "loss_mask": mask.astype(bool),
            "num_candidate_labels": int(mask.sum()),
            "num_positive_labels": int(y[mask].sum()),
            "line_labels": line_labels,
        }
    )


def generation_fingerprint(
    args: argparse.Namespace,
    seeds: list[int],
    train_seeds: set[int],
    validation_seeds: set[int],
    test_seeds: set[int],
) -> dict[str, Any]:
    return {
        "checkpoint_version": CHECKPOINT_VERSION,
        "seeds": [int(value) for value in seeds],
        "train_seeds": sorted(int(value) for value in train_seeds),
        "validation_seeds": sorted(int(value) for value in validation_seeds),
        "test_seeds": sorted(int(value) for value in test_seeds),
        "samples_per_scenario": args.samples_per_scenario,
        "target_state_samples": int(args.target_state_samples),
        "load_scale": float(args.load_scale),
        "load_random_low": float(args.load_random_low),
        "load_random_high": float(args.load_random_high),
        "limit_mode": str(args.limit_mode),
        "flow_limit_scale": float(args.flow_limit_scale),
        "min_rate_a": float(args.min_rate_a),
        "beta": float(args.beta),
        "security_limit": float(args.security_limit),
        "first_step_critical_policy": str(args.first_step_critical_policy),
        "feature_mode": str(args.feature_mode),
        "sample_seed": int(args.sample_seed),
    }


def checkpoint_row_arrays(rows: list[dict[str, Any]]) -> dict[str, np.ndarray]:
    return {
        "x_raw": np.stack([row["x_raw"] for row in rows]).astype(np.float32),
        "y": np.stack([row["y"] for row in rows]).astype(np.int64),
        "loss_mask": np.stack([row["loss_mask"] for row in rows]).astype(bool),
        "seed": np.asarray([row["seed"] for row in rows], dtype=np.int64),
        "split": np.asarray([row["split"] for row in rows], dtype=str),
        "sample_type": np.asarray([row["sample_type"] for row in rows], dtype=str),
        "active_first_line": np.asarray([row["active_first_line"] for row in rows], dtype=str),
        "current_outage_labels": np.asarray([row["current_outage_labels"] for row in rows], dtype=str),
    }


def load_checkpoint_rows(path: Path, rows: list[dict[str, Any]], line_labels: list[str]) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint progress references missing shard: {path}")
    data = np.load(path, allow_pickle=False)
    required = {
        "x_raw",
        "y",
        "loss_mask",
        "seed",
        "split",
        "sample_type",
        "active_first_line",
        "current_outage_labels",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Checkpoint shard {path} is missing arrays: {missing}")
    for idx in range(len(data["seed"])):
        append_sample(
            rows,
            data["x_raw"][idx],
            data["y"][idx],
            data["loss_mask"][idx],
            seed=int(data["seed"][idx]),
            sample_type=str(data["sample_type"][idx]),
            split=str(data["split"][idx]),
            current_outages={
                token.strip()
                for token in str(data["current_outage_labels"][idx]).split(",")
                if token.strip()
            },
            line_labels=line_labels,
            active_first_line=str(data["active_first_line"][idx]),
        )


def load_checkpoint(
    output_dir: Path,
    fingerprint: dict[str, Any],
    line_labels: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    progress_path = output_dir / CHECKPOINT_PROGRESS_NAME
    if not progress_path.exists():
        return [], {"shards": [], "completed_seeds": []}
    progress = json.loads(progress_path.read_text(encoding="utf-8"))
    if progress.get("generation_fingerprint") != fingerprint:
        raise ValueError(
            "Checkpoint configuration does not match this run. Use the original arguments or a new output directory."
        )
    rows: list[dict[str, Any]] = []
    checkpoint_dir = output_dir / CHECKPOINT_DIRNAME
    for shard_name in progress.get("shards", []):
        load_checkpoint_rows(checkpoint_dir / str(shard_name), rows, line_labels)
    expected = int(progress.get("num_state_samples", len(rows)))
    if len(rows) != expected:
        raise ValueError(f"Checkpoint restored {len(rows)} rows but progress records {expected}.")
    return rows, progress


def flush_checkpoint(
    output_dir: Path,
    rows: list[dict[str, Any]],
    pending_start: int,
    progress: dict[str, Any],
    fingerprint: dict[str, Any],
    completed_seeds: set[int],
    *,
    status: str,
) -> int:
    checkpoint_dir = output_dir / CHECKPOINT_DIRNAME
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    shards = [str(value) for value in progress.get("shards", [])]
    if pending_start < len(rows):
        existing_ids = []
        for path in checkpoint_dir.glob("checkpoint_*.npz"):
            try:
                existing_ids.append(int(path.stem.rsplit("_", 1)[1]))
            except ValueError:
                continue
        shard_id = max(existing_ids, default=0) + 1
        shard_name = f"checkpoint_{shard_id:06d}.npz"
        shard_path = checkpoint_dir / shard_name
        temp_path = checkpoint_dir / f"checkpoint_{shard_id:06d}.tmp.npz"
        np.savez_compressed(temp_path, **checkpoint_row_arrays(rows[pending_start:]))
        temp_path.replace(shard_path)
        shards.append(shard_name)

    updated = {
        "checkpoint_version": CHECKPOINT_VERSION,
        "status": status,
        "generation_fingerprint": fingerprint,
        "num_state_samples": int(len(rows)),
        "completed_seeds": sorted(int(value) for value in completed_seeds),
        "shards": shards,
    }
    progress_path = output_dir / CHECKPOINT_PROGRESS_NAME
    temp_progress = output_dir / f"{CHECKPOINT_PROGRESS_NAME}.tmp"
    temp_progress.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    temp_progress.replace(progress_path)
    progress.clear()
    progress.update(updated)
    return len(rows)


def build_dataset(args: argparse.Namespace) -> dict[str, Any]:
    if args.feature_mode != "paper":
        raise ValueError("The formal paper-aligned dataset must use --feature-mode paper.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = build_case_adapter("ieee118")
    seeds = [int(seed) for seed in args.seeds[: args.num_load_scenarios] if args.num_load_scenarios] or [int(seed) for seed in args.seeds]
    train_seeds, validation_seeds, test_seeds = split_seed_sets(argparse.Namespace(**{**vars(args), "seeds": seeds}))
    fingerprint = generation_fingerprint(args, seeds, train_seeds, validation_seeds, test_seeds)
    progress_path = args.output_dir / CHECKPOINT_PROGRESS_NAME
    if progress_path.exists() and not args.resume:
        raise FileExistsError(
            f"Checkpoint already exists at {progress_path}. Pass --resume or choose a new output directory."
        )
    metadata_path = args.output_dir / "ieee118_paper_gcn_dataset_metadata.json"
    final_dataset_path = args.output_dir / "ieee118_paper_gcn_dataset.npz"
    if args.resume and metadata_path.exists() and final_dataset_path.exists():
        existing_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if (
            existing_metadata.get("generation_fingerprint") == fingerprint
            and int(existing_metadata.get("num_state_samples", 0)) >= int(args.target_state_samples)
        ):
            return existing_metadata

    line_labels = [str(value) for value in adapter.line_labels]
    branch_from_bus = adapter.case["branch"][:, F_BUS].astype(np.int64)
    branch_to_bus = adapter.case["branch"][:, T_BUS].astype(np.int64)
    rows, checkpoint_progress = (
        load_checkpoint(args.output_dir, fingerprint, line_labels)
        if args.resume
        else ([], {"shards": [], "completed_seeds": []})
    )
    completed_seeds = {int(value) for value in checkpoint_progress.get("completed_seeds", [])}
    pending_checkpoint_start = len(rows)
    first_step_critical_labels = sum(
        int(row["y"][row["loss_mask"]].sum()) for row in rows if row["sample_type"] == "S0"
    )
    valid_n2_positive_labels = sum(
        int(row["y"][row["loss_mask"]].sum()) for row in rows if row["sample_type"] == "S1"
    )
    if rows:
        print(
            f"[paper-gcn-dataset] resumed {len(rows)} states from {len(checkpoint_progress.get('shards', []))} shards; "
            f"completed_seeds={len(completed_seeds)}",
            flush=True,
        )

    for seed in seeds:
        if len(rows) >= args.target_state_samples:
            break
        if seed in completed_seeds:
            print(f"[paper-gcn-dataset] seed={seed} already checkpointed; skipping", flush=True)
            continue
        print(f"[paper-gcn-dataset] seed={seed} start, current_states={len(rows)}/{args.target_state_samples}", flush=True)
        scenario_case = apply_load_scenario(
            adapter.case,
            seed=seed,
            load_scale=args.load_scale,
            low=args.load_random_low,
            high=args.load_random_high,
        )
        scenario_case = apply_thermal_limit_mode(
            scenario_case,
            limit_mode=args.limit_mode,
            flow_limit_scale=args.flow_limit_scale,
            min_rate_a=args.min_rate_a,
        )
        split = split_name(seed, train_seeds, validation_seeds, test_seeds)
        x_s0, labels, from_bus, to_bus = state_features(scenario_case, adapter, set(), args.feature_mode, args.beta, args.security_limit)
        if labels != line_labels:
            raise ValueError("IEEE118 line-label order changed across load scenarios.")
        if not np.array_equal(from_bus, branch_from_bus) or not np.array_equal(to_bus, branch_to_bus):
            raise ValueError("IEEE118 branch endpoints changed across load scenarios.")
        y_s0 = np.zeros(len(labels), dtype=np.int64)
        mask_s0 = scenario_case["branch"][:, BR_STATUS].astype(int) == 1
        noncritical_first_lines: list[str] = []
        first_states: dict[str, dict] = {}
        for idx, label in enumerate(labels):
            if not mask_s0[idx]:
                continue
            state = run_sequential_outages_for_case(scenario_case, adapter, [label], beta=args.beta, security_limit=args.security_limit)
            first_states[label] = state
            if bool_critical(state):
                y_s0[idx] = 1
            else:
                noncritical_first_lines.append(label)
        seed_rows = [row for row in rows if int(row["seed"]) == seed]
        has_s0 = any(row["sample_type"] == "S0" for row in seed_rows)
        if not has_s0:
            append_sample(
                rows,
                x_s0,
                y_s0,
                mask_s0,
                seed=seed,
                sample_type="S0",
                split=split,
                current_outages=set(),
                line_labels=labels,
            )
            first_step_critical_labels += int(y_s0[mask_s0].sum())
        print(
            f"[paper-gcn-dataset] seed={seed} S0 done, first_step_positive={int(y_s0[mask_s0].sum())}, "
            f"noncritical_first_lines={len(noncritical_first_lines)}, current_states={len(rows)}/{args.target_state_samples}",
            flush=True,
        )
        if len(rows) >= args.target_state_samples:
            break

        seed_rng = np.random.default_rng(np.random.SeedSequence([int(args.sample_seed), int(seed)]))
        seed_rng.shuffle(noncritical_first_lines)
        scenario_cap = args.samples_per_scenario if args.samples_per_scenario is not None else len(noncritical_first_lines)
        processed_first_lines = {
            str(row["active_first_line"])
            for row in seed_rows
            if row["sample_type"] == "S1" and str(row["active_first_line"])
        }
        for first_line in noncritical_first_lines[:scenario_cap]:
            if len(rows) >= args.target_state_samples:
                break
            if first_line in processed_first_lines:
                continue
            first_state = first_states[first_line]
            current_outages = final_outage_set(first_state) | {first_line}
            x_s1, _, _, _ = state_features(first_state["case"], adapter, current_outages, args.feature_mode, args.beta, args.security_limit)
            y_s1 = np.zeros(len(labels), dtype=np.int64)
            status = first_state["case"]["branch"][:, BR_STATUS].astype(int)
            mask_s1 = np.asarray([status[idx] == 1 and label not in current_outages for idx, label in enumerate(labels)], dtype=bool)
            for idx, second_line in enumerate(labels):
                if not mask_s1[idx]:
                    continue
                state2 = run_sequential_outages_for_case(first_state["case"], adapter, [second_line], beta=args.beta, security_limit=args.security_limit)
                if bool_critical(state2):
                    y_s1[idx] = 1
            append_sample(
                rows,
                x_s1,
                y_s1,
                mask_s1,
                seed=seed,
                sample_type="S1",
                split=split,
                current_outages=current_outages,
                line_labels=labels,
                active_first_line=first_line,
            )
            valid_n2_positive_labels += int(y_s1[mask_s1].sum())
            if args.checkpoint_every > 0 and len(rows) - pending_checkpoint_start >= args.checkpoint_every:
                pending_checkpoint_start = flush_checkpoint(
                    args.output_dir,
                    rows,
                    pending_checkpoint_start,
                    checkpoint_progress,
                    fingerprint,
                    completed_seeds,
                    status="running",
                )
            if len(rows) % 25 == 0 or len(rows) >= args.target_state_samples:
                print(
                    f"[paper-gcn-dataset] seed={seed} current_states={len(rows)}/{args.target_state_samples}, "
                    f"last_first_line={first_line}, last_s1_positive={int(y_s1[mask_s1].sum())}",
                    flush=True,
                )

        selected_first_lines = set(noncritical_first_lines[:scenario_cap])
        now_processed = processed_first_lines | {
            str(row["active_first_line"])
            for row in rows
            if int(row["seed"]) == seed and row["sample_type"] == "S1" and str(row["active_first_line"])
        }
        if selected_first_lines.issubset(now_processed):
            completed_seeds.add(seed)
        if args.checkpoint_every > 0:
            pending_checkpoint_start = flush_checkpoint(
                args.output_dir,
                rows,
                pending_checkpoint_start,
                checkpoint_progress,
                fingerprint,
                completed_seeds,
                status="target_reached" if len(rows) >= args.target_state_samples else "running",
            )

    if not rows:
        raise ValueError("No paper-aligned IEEE118 samples were generated.")
    if args.checkpoint_every > 0:
        pending_checkpoint_start = flush_checkpoint(
            args.output_dir,
            rows,
            pending_checkpoint_start,
            checkpoint_progress,
            fingerprint,
            completed_seeds,
            status="complete" if len(rows) >= args.target_state_samples else "seed_list_exhausted",
        )
    x_raw = np.stack([row["x_raw"] for row in rows]).astype(np.float32)
    y = np.stack([row["y"] for row in rows]).astype(np.int64)
    mask = np.stack([row["loss_mask"] for row in rows]).astype(bool)
    splits = np.asarray([row["split"] for row in rows], dtype=str)
    train_mask = splits == "train"
    if not train_mask.any():
        train_mask = np.ones(len(rows), dtype=bool)
    normalizer = fit_normalizer(x_raw[train_mask], PAPER_FEATURE_NAMES)
    x = normalize_x(x_raw, normalizer, PAPER_FEATURE_NAMES).astype(np.float32)
    np.savez(
        args.output_dir / "ieee118_paper_gcn_dataset.npz",
        x_gcn=x,
        physics_raw_features=x_raw,
        y_gcn=y,
        y_critical=y,
        loss_mask=mask,
        seed=np.asarray([row["seed"] for row in rows], dtype=np.int64),
        split=splits,
        sample_type=np.asarray([row["sample_type"] for row in rows], dtype=str),
        active_first_line=np.asarray([row["active_first_line"] for row in rows], dtype=str),
        current_outage_labels=np.asarray([row["current_outage_labels"] for row in rows], dtype=str),
        line_labels=np.asarray(line_labels, dtype=str),
        branch_from_bus=branch_from_bus,
        branch_to_bus=branch_to_bus,
        feature_names=np.asarray(PAPER_FEATURE_NAMES, dtype=str),
    )
    summary = pd.DataFrame(
        [
            {
                "sample_index": row["sample_index"],
                "seed": row["seed"],
                "split": row["split"],
                "sample_type": row["sample_type"],
                "active_first_line": row["active_first_line"],
                "current_outage_labels": row["current_outage_labels"],
                "num_candidate_labels": row["num_candidate_labels"],
                "num_positive_labels": row["num_positive_labels"],
            }
            for row in rows
        ]
    )
    summary.to_csv(args.output_dir / "ieee118_paper_gcn_sample_summary.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_paper_gcn_feature_normalizer.json").write_text(json.dumps(normalizer, indent=2), encoding="utf-8")
    metadata = write_metadata(
        args,
        summary,
        y,
        mask,
        first_step_critical_labels,
        valid_n2_positive_labels,
        train_seeds,
        validation_seeds,
        test_seeds,
        generation_fingerprint=fingerprint,
    )
    write_schema(args.output_dir)
    write_readme(args.output_dir, metadata)
    return metadata


def write_metadata(
    args: argparse.Namespace,
    summary: pd.DataFrame,
    y: np.ndarray,
    mask: np.ndarray,
    first_step_critical_labels: int,
    valid_n2_positive_labels: int,
    train_seeds: set[int],
    validation_seeds: set[int],
    test_seeds: set[int],
    generation_fingerprint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = mask.astype(bool)
    positive = int(y[active].sum())
    candidates = int(active.sum())
    metadata = {
        "case_name": "ieee118",
        "dataset_npz": str(args.output_dir / "ieee118_paper_gcn_dataset.npz"),
        "feature_mode": args.feature_mode,
        "feature_names": PAPER_FEATURE_NAMES,
        "input_channels": 4,
        "target_state_samples": int(args.target_state_samples),
        "num_state_samples": int(len(summary)),
        "num_s0_samples": int((summary["sample_type"] == "S0").sum()),
        "num_s1_samples": int((summary["sample_type"] == "S1").sum()),
        "num_positive_labels": positive,
        "num_candidate_labels": candidates,
        "positive_label_ratio": positive / max(candidates, 1),
        "num_first_step_critical_labels": int(first_step_critical_labels),
        "num_valid_n2_positive_labels": int(valid_n2_positive_labels),
        "train_seeds": sorted(train_seeds),
        "validation_seeds": sorted(validation_seeds),
        "test_seeds": sorted(test_seeds),
        "num_train_seeds": len(train_seeds),
        "num_validation_seeds": len(validation_seeds),
        "num_test_seeds": len(test_seeds),
        "num_train_state_samples": int((summary["split"] == "train").sum()),
        "num_validation_state_samples": int((summary["split"] == "validation").sum()),
        "num_test_state_samples": int((summary["split"] == "test").sum()),
        "load_scale": args.load_scale,
        "load_random_low": args.load_random_low,
        "load_random_high": args.load_random_high,
        "limit_mode": args.limit_mode,
        "flow_limit_scale": args.flow_limit_scale,
        "min_rate_a": args.min_rate_a,
        "beta": args.beta,
        "security_limit": args.security_limit,
        "first_step_critical_policy": args.first_step_critical_policy,
        "normalizer_fit_split": "train",
        "paper_aligned_target_state_samples": 8000,
        "large_npz_tracked_in_git": False,
        "resume_supported": True,
        "checkpoint_format": "incremental compressed NPZ shards",
        "checkpoint_progress": str(args.output_dir / CHECKPOINT_PROGRESS_NAME),
        "generation_fingerprint": generation_fingerprint,
    }
    (args.output_dir / "ieee118_paper_gcn_dataset_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def write_schema(output_dir: Path) -> None:
    (output_dir / "ieee118_paper_gcn_dataset_schema.md").write_text(
        "# IEEE118 Paper-Aligned GCN Dataset Schema\n\n"
        "- `x_gcn`: state x branch x 4 paper-style features (`x_t`, `x_p`, `x_b`, `x_l`).\n"
        "- `y_gcn`: branch vulnerability labels for the current state.\n"
        "- `loss_mask`: valid candidate branches for each current state.\n"
        "- `sample_type`: `S0` base states and `S1` first-outage states.\n"
        "- `active_first_line`: the active first outage for S1; empty for S0.\n"
        "- Splits are assigned by load-scenario seed to avoid leakage.\n",
        encoding="utf-8",
    )


def write_readme(output_dir: Path, metadata: dict[str, Any]) -> None:
    (output_dir / "ieee118_paper_gcn_readme.md").write_text(
        "# IEEE118 Paper-Aligned Multi-State GCN Training Dataset\n\n"
        "This dataset adds S0 base-state samples and S1 first-outage samples for the original RTS-79 "
        "`PaperStyleRts79Gcn`. The committed metadata is compact; the NPZ dataset should stay local.\n\n"
        f"- State samples: {metadata['num_state_samples']}\n"
        f"- S0 samples: {metadata['num_s0_samples']}\n"
        f"- S1 samples: {metadata['num_s1_samples']}\n"
        f"- Positive label ratio: {metadata['positive_label_ratio']:.6f}\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    metadata = build_dataset(args)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
