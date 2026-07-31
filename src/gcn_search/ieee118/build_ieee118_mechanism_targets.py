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
sys.path.insert(0, str(IEEE118_DIR))
sys.path.insert(0, str(LEGACY_DIR))

from build_ieee118_paper_gcn_training_dataset import apply_load_scenario
from case_adapter import build_case_adapter, run_sequential_outages_for_case
from generate_ieee118_ordered_n2_fulltruth import (
    apply_thermal_limit_mode,
    summarize_state,
)
from tail_active_acquisition import select_tail_disagreement_batch
from train_ieee118_tail_aware_gcn import _new_model
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
)
from train_ieee118_paper_aligned_gcn import predict_probability
from train_rts79_paper_gcn import _build_adjacency_powers


DEFAULT_DATASET = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_gcn_dataset.npz"
)
DEFAULT_PHASE3 = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_mf_all_candidates_perstate95_e1_w5_curve"
    / "pmf_hybrid_prior_corrected_seed_20260730"
    / "active_label_replay_checkpoint.pt"
)
DEFAULT_LOW_FIDELITY = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_dc_lodf_low_fidelity_all_candidates"
    / "ieee118_dc_lodf_low_fidelity_targets.npz"
)
DEFAULT_OUTPUT = (
    ROOT / "results" / "gcn_search" / "ieee118_mechanism_aware_gcn"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Replay only already-queried IEEE118 S1 positives to recover "
            "relay, island, and load-shed auxiliary targets."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--phase3-checkpoint", type=Path, default=DEFAULT_PHASE3)
    parser.add_argument(
        "--low-fidelity-target-npz", type=Path, default=DEFAULT_LOW_FIDELITY
    )
    parser.add_argument("--tail-acquisition-fraction", type=float, default=0.005)
    parser.add_argument("--load-scale", type=float, default=1.1)
    parser.add_argument("--load-random-low", type=float, default=0.9)
    parser.add_argument("--load-random-high", type=float, default=1.1)
    parser.add_argument(
        "--limit-mode",
        choices=["original_rate_a", "flow_scaled"],
        default="flow_scaled",
    )
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--max-positive-simulations", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _require(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing local {label}: {path}")


def _atomic_records(records: list[dict[str, Any]], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    pd.DataFrame(records).to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(path)


def reconstruct_tail_query_mask(
    data: Any,
    phase3_checkpoint: dict[str, Any],
    low_fidelity: Any,
    *,
    tail_acquisition_fraction: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Reproduce the label-free tail acquisition without reading labels."""

    original = np.asarray(phase3_checkpoint["query_mask"], dtype=bool)
    valid = np.asarray(data["loss_mask"], dtype=bool)
    split = np.asarray(data["split"], dtype=str)
    if original.shape != valid.shape:
        raise ValueError("Phase-3 query mask does not match mechanism dataset.")
    for name in ("proxy_score", "proxy_mask", "line_labels", "seed", "split"):
        if name not in low_fidelity:
            raise ValueError(f"Low-fidelity targets are missing {name}.")
    if not np.array_equal(
        np.asarray(low_fidelity["line_labels"], dtype=str),
        np.asarray(data["line_labels"], dtype=str),
    ):
        raise ValueError("Low-fidelity line labels do not align.")
    if not np.array_equal(low_fidelity["seed"], data["seed"]) or not np.array_equal(
        np.asarray(low_fidelity["split"], dtype=str), split
    ):
        raise ValueError("Low-fidelity state order does not align.")

    query = original.copy()
    fraction = float(tail_acquisition_fraction)
    if fraction <= 0.0:
        return query, np.empty((0, 2), dtype=np.int64)
    adjacency = build_branch_graph_adjacency_from_endpoints(
        data["branch_from_bus"], data["branch_to_bus"]
    )
    import torch

    adjacency_powers = torch.tensor(
        _build_adjacency_powers(adjacency, 6), dtype=torch.float32
    )
    models = [
        _new_model(state, input_channels=data["x_gcn"].shape[2], seed=index)
        for index, state in enumerate(phase3_checkpoint["member_states"])
    ]
    member_probability = np.stack(
        [
            predict_probability(
                model,
                data["x_gcn"].astype(np.float32),
                adjacency_powers,
                torch,
            )
            for model in models
        ]
    )
    pool = (
        (split == "train")[:, None]
        & valid
        & np.asarray(low_fidelity["proxy_mask"], dtype=bool)
        & ~query
    )
    batch_size = min(
        max(int(round(fraction * int(valid[split == "train"].sum()))), 1),
        int(pool.sum()),
    )
    selected = select_tail_disagreement_batch(
        member_probability.mean(axis=0),
        member_probability.std(axis=0),
        np.asarray(low_fidelity["proxy_score"], dtype=np.float64),
        pool,
        batch_size=batch_size,
    )
    query[selected[:, 0], selected[:, 1]] = True
    return query, selected


def mechanism_arrays_from_records(
    shape: tuple[int, int],
    known_mask: np.ndarray,
    critical_labels: np.ndarray,
    records: list[dict[str, Any]],
) -> dict[str, np.ndarray]:
    known = np.asarray(known_mask, dtype=bool)
    critical = np.asarray(critical_labels, dtype=np.int64)
    if known.shape != shape or critical.shape != shape:
        raise ValueError("Mechanism target arrays must share the dataset shape.")
    relay = np.zeros(shape, dtype=np.int8)
    island = np.zeros(shape, dtype=np.int8)
    shed = np.zeros(shape, dtype=np.float32)
    island_shed = np.zeros(shape, dtype=np.float32)
    relay_trips = np.zeros(shape, dtype=np.float32)
    replayed = np.zeros(shape, dtype=bool)
    for record in records:
        state_index = int(record["state_index"])
        line_index = int(record["line_index"])
        if not known[state_index, line_index]:
            raise ValueError("A replay record targets an unknown mechanism label.")
        if critical[state_index, line_index] != 1:
            raise ValueError("Only queried positive labels require physical replay.")
        relay[state_index, line_index] = int(bool(record["relay_cascade"]))
        island[state_index, line_index] = int(
            float(record["island_load_shed_mw"]) > 1e-7
        )
        island_shed[state_index, line_index] = float(
            record["island_load_shed_mw"]
        )
        relay_trips[state_index, line_index] = float(
            record.get("num_relay_trips", int(bool(record["relay_cascade"])))
        )
        shed[state_index, line_index] = float(record["total_load_shed_mw"])
        replayed[state_index, line_index] = True
    required_replay = known & (critical == 1)
    complete = bool(np.all(replayed[required_replay]))
    return {
        "mechanism_known_mask": known,
        "relay_cascade_target": relay,
        "island_shed_target": island,
        "log1p_relay_trip_target": np.log1p(relay_trips).astype(np.float32),
        "log1p_island_shed_target": np.log1p(island_shed).astype(np.float32),
        "log1p_load_shed_target": np.log1p(shed).astype(np.float32),
        "positive_replay_mask": replayed,
        "complete": np.asarray(complete),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.dataset_npz, "paper-8000 residual dataset"),
        (args.phase3_checkpoint, "Phase-3 checkpoint"),
        (args.low_fidelity_target_npz, "low-fidelity target dataset"),
    ):
        _require(path, label)
    if not 0.0 <= args.tail_acquisition_fraction <= 0.05:
        raise ValueError("--tail-acquisition-fraction must be between 0 and 0.05.")
    if args.checkpoint_every < 0:
        raise ValueError("--checkpoint-every must be non-negative.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    record_path = args.output_dir / "ieee118_mechanism_replay_records.csv"
    target_path = args.output_dir / "ieee118_mechanism_targets.npz"
    metadata_path = args.output_dir / "ieee118_mechanism_targets_metadata.json"

    data = np.load(args.dataset_npz, allow_pickle=False)
    low_fidelity = np.load(args.low_fidelity_target_npz, allow_pickle=False)
    import torch

    checkpoint = torch.load(
        args.phase3_checkpoint, map_location="cpu", weights_only=False
    )
    query_mask, selected = reconstruct_tail_query_mask(
        data,
        checkpoint,
        low_fidelity,
        tail_acquisition_fraction=float(args.tail_acquisition_fraction),
    )
    split = np.asarray(data["split"], dtype=str)
    sample_type = np.asarray(data["sample_type"], dtype=str)
    valid = np.asarray(data["loss_mask"], dtype=bool)
    critical = np.asarray(data["y_gcn"], dtype=np.int64)
    known = (
        query_mask
        & valid
        & np.isin(split, ["train", "validation"])[:, None]
        & (sample_type == "S1")[:, None]
    )
    positive_positions = np.argwhere(known & (critical == 1))
    if args.max_positive_simulations is not None:
        positive_positions = positive_positions[
            : int(args.max_positive_simulations)
        ]

    records: list[dict[str, Any]] = []
    if args.resume and record_path.exists():
        records = pd.read_csv(record_path).to_dict("records")
    completed = {
        (int(row["state_index"]), int(row["line_index"])) for row in records
    }
    adapter = build_case_adapter("ieee118")
    labels = np.asarray(data["line_labels"], dtype=str)
    scenario_cache: dict[int, dict[str, Any]] = {}
    first_state_cache: dict[tuple[int, str], dict[str, Any]] = {}
    for position, (state_index, line_index) in enumerate(
        positive_positions, start=1
    ):
        key = (int(state_index), int(line_index))
        if key in completed:
            continue
        seed = int(data["seed"][state_index])
        first_line = str(data["active_first_line"][state_index])
        second_line = str(labels[line_index])
        if not first_line:
            raise ValueError(f"S1 state {state_index} has no active first line.")
        if seed not in scenario_cache:
            scenario = apply_load_scenario(
                adapter.case,
                seed=seed,
                load_scale=float(args.load_scale),
                low=float(args.load_random_low),
                high=float(args.load_random_high),
            )
            scenario_cache[seed] = apply_thermal_limit_mode(
                scenario,
                limit_mode=str(args.limit_mode),
                flow_limit_scale=float(args.flow_limit_scale),
                min_rate_a=float(args.min_rate_a),
            )
        first_key = (seed, first_line)
        if first_key not in first_state_cache:
            first_state_cache[first_key] = run_sequential_outages_for_case(
                scenario_cache[seed],
                adapter,
                [first_line],
                beta=float(args.beta),
                security_limit=float(args.security_limit),
            )
        second_state = run_sequential_outages_for_case(
            first_state_cache[first_key]["case"],
            adapter,
            [second_line],
            beta=float(args.beta),
            security_limit=float(args.security_limit),
        )
        summary = summarize_state(second_state, {first_line, second_line})
        if not summary["converged"] or not summary["critical"]:
            raise ValueError(
                "Mechanism replay disagrees with stored critical label for "
                f"state={state_index}, path={first_line}->{second_line}."
            )
        records.append(
            {
                "state_index": int(state_index),
                "line_index": int(line_index),
                "seed": seed,
                "first_line": first_line,
                "second_line": second_line,
                "path": f"{first_line}->{second_line}",
                "relay_cascade": bool(
                    summary["critical_mechanism"] == "relay_cascade"
                ),
                "island_load_shed_mw": float(summary["island_load_shed_mw"]),
                "redispatch_load_shed_mw": float(
                    summary["redispatch_load_shed_mw"]
                ),
                "total_load_shed_mw": float(summary["total_load_shed_mw"]),
                "num_relay_trips": int(summary["num_relay_trips"]),
            }
        )
        if args.checkpoint_every > 0 and len(records) % args.checkpoint_every == 0:
            _atomic_records(records, record_path)
            print(
                f"[mechanism-targets] replayed={len(records)}/"
                f"{len(positive_positions)}",
                flush=True,
            )
    _atomic_records(records, record_path)

    arrays = mechanism_arrays_from_records(
        critical.shape, known, critical, records
    )
    limited = args.max_positive_simulations is not None
    if limited:
        arrays["complete"] = np.asarray(False)
    np.savez_compressed(
        target_path,
        **arrays,
        query_mask=query_mask,
        line_labels=labels,
        seed=data["seed"],
        split=split,
        sample_type=sample_type,
    )
    relay = arrays["relay_cascade_target"]
    island = arrays["island_shed_target"]
    metadata = {
        "status": "complete" if bool(arrays["complete"]) else "partial_smoke",
        "label_leakage": False,
        "fulltruth_input": None,
        "num_original_queries": int(checkpoint["query_mask"].sum()),
        "num_tail_queries": int(len(selected)),
        "num_known_s1_mechanism_labels": int(known.sum()),
        "num_positive_replays_required": int((known & (critical == 1)).sum()),
        "num_positive_replays_completed": int(len(records)),
        "num_relay_cascade_positive": int(relay[known].sum()),
        "num_island_shed_positive": int(island[known].sum()),
        "target_semantics": {
            "relay_cascade_target": "queried path produced overload relay trips and load shed",
            "island_shed_target": "queried path produced positive island load shed",
            "log1p_relay_trip_target": "log1p(number of overload relay trips)",
            "log1p_island_shed_target": "log1p(island load shed MW)",
            "log1p_load_shed_target": "log1p(total load shed MW) for queried paths",
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main(argv: list[str] | None = None) -> int:
    summary = run(parse_args(argv))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
