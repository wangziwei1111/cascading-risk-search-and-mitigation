from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_X, PF, RATE_A, TAP


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(IEEE118_DIR))
sys.path.insert(0, str(LEGACY_DIR))

from build_ieee118_paper_gcn_training_dataset import apply_load_scenario
from case_adapter import build_case_adapter
from dc_lodf_low_fidelity import (
    build_dc_lodf_matrix,
    dc_lodf_max_loading_proxy,
)
from generate_ieee118_ordered_n2_fulltruth import apply_thermal_limit_mode
from train_ieee118_paper_aligned_gcn import average_precision


DEFAULT_DATASET = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_gcn_dataset.npz"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "dc_lodf_low_fidelity"
)


def portable_result_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build cheap DC/LODF low-fidelity targets for the unchanged RTS-79 "
            "PaperStyleRts79Gcn. This script does not run N-2 cascades."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
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
    parser.add_argument(
        "--topology-mode",
        choices=["active_first_only", "current_outages"],
        default="active_first_only",
        help=(
            "Use only the active first outage for a 186-topology cache, or use "
            "the exact current outage set for a more expensive offline proxy."
        ),
    )
    return parser.parse_args(argv)


def _require_dataset(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing local IEEE118 GCN dataset: {path}. "
            "The low-fidelity builder will not regenerate cascade truth."
        )


def _feature_index(feature_names: np.ndarray, name: str) -> int:
    matches = np.where(feature_names.astype(str) == name)[0]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {name!r} physics feature.")
    return int(matches[0])


def _scenario_flow_and_limits(
    adapter: Any,
    seeds: np.ndarray,
    args: argparse.Namespace,
) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    result: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    for seed in np.unique(seeds).astype(np.int64):
        scenario = apply_load_scenario(
            adapter.case,
            seed=int(seed),
            load_scale=float(args.load_scale),
            low=float(args.load_random_low),
            high=float(args.load_random_high),
        )
        scenario = apply_thermal_limit_mode(
            scenario,
            limit_mode=str(args.limit_mode),
            flow_limit_scale=float(args.flow_limit_scale),
            min_rate_a=float(args.min_rate_a),
        )
        signed_flow = scenario["branch"][:, PF].astype(np.float64)
        flow_sign = np.where(signed_flow < 0.0, -1.0, 1.0)
        rate_a = scenario["branch"][:, RATE_A].astype(np.float64)
        if np.any(rate_a <= 0.0):
            raise ValueError(
                f"Seed {int(seed)} has non-positive RATE_A values; "
                "the loading proxy is undefined."
            )
        result[int(seed)] = (flow_sign, rate_a)
    return result


def _topology_status(
    *,
    topology_mode: str,
    current_status: np.ndarray,
    active_first_line: str,
    line_position: dict[str, int],
) -> np.ndarray:
    if topology_mode == "current_outages":
        return current_status.copy()
    status = np.ones_like(current_status, dtype=bool)
    if active_first_line:
        if active_first_line not in line_position:
            raise ValueError(
                f"Unknown active_first_line label: {active_first_line!r}"
            )
        status[line_position[active_first_line]] = False
    return status


def _describe(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if len(finite) == 0:
        return {
            "count": 0,
            "mean": float("nan"),
            "p50": float("nan"),
            "p95": float("nan"),
            "p99": float("nan"),
            "max": float("nan"),
        }
    return {
        "count": int(len(finite)),
        "mean": float(np.mean(finite)),
        "p50": float(np.quantile(finite, 0.50)),
        "p95": float(np.quantile(finite, 0.95)),
        "p99": float(np.quantile(finite, 0.99)),
        "max": float(np.max(finite)),
    }


def low_fidelity_cost_disclosure(topology_mode: str) -> dict[str, Any]:
    if topology_mode not in {"active_first_only", "current_outages"}:
        raise ValueError(f"Unsupported topology_mode={topology_mode!r}")
    return {
        "incremental_target_builder_n1_cascade_calls": 0,
        "incremental_target_builder_n2_cascade_calls": 0,
        "source_state_cost_reclaimed": False,
        "source_state_dependency": (
            "The builder reads pre-existing S0/S1 graph states and their branch "
            "flows from --dataset-npz. Its zero N-1/N-2 call count covers only "
            "incremental proxy-target construction and does not reclaim the "
            "historical physical cost of generating those source states."
        ),
    }


def build_targets(args: argparse.Namespace) -> dict[str, Any]:
    _require_dataset(args.dataset_npz)
    if args.beta <= 0.0:
        raise ValueError("--beta must be positive.")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(args.dataset_npz, allow_pickle=True)
    required = {
        "physics_raw_features",
        "feature_names",
        "y_gcn",
        "loss_mask",
        "split",
        "sample_type",
        "seed",
        "line_labels",
        "branch_from_bus",
        "branch_to_bus",
        "active_first_line",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Dataset is missing arrays required by the proxy: {missing}")

    x_raw = data["physics_raw_features"].astype(np.float64)
    feature_names = data["feature_names"].astype(str)
    offline_idx = _feature_index(feature_names, "branch_status_offline")
    abs_flow_idx = _feature_index(feature_names, "abs_flow")
    line_labels = data["line_labels"].astype(str)
    line_position = {
        label: line_idx
        for line_idx, label in enumerate(line_labels.tolist())
    }
    current_status = x_raw[:, :, offline_idx] < 0.5
    abs_flow = x_raw[:, :, abs_flow_idx]
    proxy_mask = current_status & np.isfinite(abs_flow)
    high_fidelity_mask = data["loss_mask"].astype(bool)

    adapter = build_case_adapter("ieee118")
    branch_x = adapter.case["branch"][:, BR_X].astype(np.float64)
    branch_tap = adapter.case["branch"][:, TAP].astype(np.float64)
    scenario_cache = _scenario_flow_and_limits(
        adapter,
        data["seed"].astype(np.int64),
        args,
    )
    topology_cache: dict[bytes, Any] = {}
    proxy_score = np.full(proxy_mask.shape, np.nan, dtype=np.float32)

    for sample_idx in range(len(x_raw)):
        status_for_matrix = _topology_status(
            topology_mode=str(args.topology_mode),
            current_status=current_status[sample_idx],
            active_first_line=str(data["active_first_line"][sample_idx]),
            line_position=line_position,
        )
        topology_key = np.packbits(status_for_matrix).tobytes()
        if topology_key not in topology_cache:
            topology_cache[topology_key] = build_dc_lodf_matrix(
                data["branch_from_bus"],
                data["branch_to_bus"],
                branch_x,
                status_for_matrix,
                branch_tap_ratio=branch_tap,
            )
        flow_sign, rate_a = scenario_cache[int(data["seed"][sample_idx])]
        sample_score = dc_lodf_max_loading_proxy(
            abs_flow[sample_idx],
            flow_sign,
            rate_a,
            current_status[sample_idx],
            topology_cache[topology_key],
            singular_score=float(args.beta),
        )
        proxy_score[sample_idx, proxy_mask[sample_idx]] = sample_score[
            proxy_mask[sample_idx]
        ].astype(np.float32)

    proxy_overload_label = (
        np.isfinite(proxy_score)
        & (proxy_score >= float(args.beta))
    ).astype(np.int64)
    output_npz = args.output_dir / "ieee118_dc_lodf_low_fidelity_targets.npz"
    np.savez_compressed(
        output_npz,
        proxy_score=proxy_score,
        proxy_overload_label=proxy_overload_label,
        proxy_mask=proxy_mask,
        line_labels=line_labels,
        seed=data["seed"].astype(np.int64),
        split=data["split"].astype(str),
        sample_type=data["sample_type"].astype(str),
        active_first_line=data["active_first_line"].astype(str),
    )

    rows = []
    split_name = data["split"].astype(str)
    sample_type = data["sample_type"].astype(str)
    for split_value in ("train", "validation", "test"):
        for state_type in ("S0", "S1"):
            row_mask = (
                (split_name == split_value)
                & (sample_type == state_type)
            )
            candidate_mask = proxy_mask & row_mask[:, None]
            alignment_mask = candidate_mask & high_fidelity_mask
            candidate_truth = data["y_gcn"][alignment_mask].astype(np.int64)
            candidate_score = proxy_score[alignment_mask].astype(np.float64)
            positive_score = candidate_score[candidate_truth == 1]
            negative_score = candidate_score[candidate_truth == 0]
            rows.append(
                {
                    "split": split_value,
                    "sample_type": state_type,
                    "num_state_samples": int(row_mask.sum()),
                    "num_proxy_candidates": int(candidate_mask.sum()),
                    "num_proxy_overload_positive": int(
                        proxy_overload_label[candidate_mask].sum()
                    ),
                    "proxy_overload_positive_ratio": float(
                        proxy_overload_label[candidate_mask].mean()
                    )
                    if candidate_mask.any()
                    else 0.0,
                    "num_high_fidelity_labels_for_alignment": int(
                        alignment_mask.sum()
                    ),
                    "proxy_ap_against_high_fidelity_label": average_precision(
                        candidate_truth,
                        candidate_score,
                    )
                    if candidate_mask.any()
                    else 0.0,
                    "proxy_mean_score_high_fidelity_positive": float(
                        positive_score.mean()
                    )
                    if len(positive_score)
                    else 0.0,
                    "proxy_mean_score_high_fidelity_negative": float(
                        negative_score.mean()
                    )
                    if len(negative_score)
                    else 0.0,
                    "proxy_positive_negative_score_gap": float(
                        positive_score.mean() - negative_score.mean()
                    )
                    if len(positive_score) and len(negative_score)
                    else 0.0,
                }
            )
    label_summary = pd.DataFrame(rows)
    label_summary.to_csv(
        args.output_dir / "ieee118_dc_lodf_low_fidelity_label_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    valid_score = proxy_score[proxy_mask]
    summary = {
        "status": "complete",
        "research_stage": "Phase 3 cheap DC/LODF multi-fidelity target construction",
        "source_dataset_npz": portable_result_path(args.dataset_npz),
        "output_npz_local_not_for_git": portable_result_path(output_npz),
        "num_state_samples": int(len(x_raw)),
        "num_proxy_candidates": int(proxy_mask.sum()),
        "num_proxy_overload_positive": int(proxy_overload_label[proxy_mask].sum()),
        "proxy_overload_positive_ratio": float(
            proxy_overload_label[proxy_mask].mean()
        ),
        "num_unique_load_scenarios": int(len(scenario_cache)),
        "num_cached_dc_topologies": int(len(topology_cache)),
        "num_nonunity_transformer_taps": int(
            np.count_nonzero(
                ~np.isclose(np.where(branch_tap == 0.0, 1.0, branch_tap), 1.0)
            )
        ),
        "topology_mode": str(args.topology_mode),
        "proxy_score_describe": _describe(valid_score),
        "proxy_label_alignment_by_split_and_state": label_summary.to_dict(
            "records"
        ),
        "physics_cost": {
            "base_dcopf_calls": int(len(scenario_cache)),
            "n1_cascade_calls": 0,
            "n2_cascade_calls": 0,
            "topology_linear_algebra_builds": int(len(topology_cache)),
        },
        "cost_disclosure": low_fidelity_cost_disclosure(
            str(args.topology_mode)
        ),
        "configuration": {
            "load_scale": float(args.load_scale),
            "load_random_low": float(args.load_random_low),
            "load_random_high": float(args.load_random_high),
            "limit_mode": str(args.limit_mode),
            "flow_limit_scale": float(args.flow_limit_scale),
            "min_rate_a": float(args.min_rate_a),
            "beta": float(args.beta),
        },
        "outcome_label_leakage": False,
        "interpretation_limit": (
            "The proxy is a DC redistribution screen, not cascade ground truth. "
            "It ignores protection timing, redispatch, island load shedding, and "
            "other nonlinear cascade mechanisms."
        ),
        "output_files": {
            "local_targets_npz_not_for_git": output_npz.name,
            "label_summary": "ieee118_dc_lodf_low_fidelity_label_summary.csv",
            "metadata": "ieee118_dc_lodf_low_fidelity_metadata.json",
            "readme": "ieee118_dc_lodf_low_fidelity_readme.md",
        },
    }
    (args.output_dir / "ieee118_dc_lodf_low_fidelity_metadata.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_dc_lodf_low_fidelity_readme.md").write_text(
        "# IEEE118 DC/LODF Low-Fidelity Targets\n\n"
        "These targets are produced from topology, current branch flow, and "
        "thermal limits. They require one base DCOPF per load scenario and no "
        "additional N-1 or N-2 cascade calls inside this target builder. The "
        "source NPZ already contains S0/S1 graph states, so this incremental "
        "count does not reclaim their historical physical construction cost. "
        "All nine IEEE118 non-unity transformer taps are included in the DC "
        "branch susceptance used by the LODF calculation.\n\n"
        "The target is suitable for pretraining or acquisition guidance only. "
        "It must not replace high-fidelity cascade labels in final evaluation.\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    print(json.dumps(build_targets(parse_args()), indent=2))


if __name__ == "__main__":
    main()
