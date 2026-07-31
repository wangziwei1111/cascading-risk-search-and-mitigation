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
    IterativeRelayProxyResult,
    iterative_dc_lodf_relay_proxy,
)
from generate_ieee118_ordered_n2_fulltruth import apply_thermal_limit_mode
from run_ieee118_active_label_replay import DEFAULT_DATASET


DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_iterative_lodf_n1_proxy"
)
DEFAULT_DEPLOYMENT_FIRST_STEP = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
    / "ieee118_first_step_summary.csv"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Select an iterative DC/LODF N-1 relay-risk proxy on validation "
            "seeds and freeze it before the IEEE118 test-seed audit."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--load-scale", type=float, default=1.1)
    parser.add_argument("--deployment-load-scale", type=float, default=1.0)
    parser.add_argument("--deployment-seed", type=int, default=20260708)
    parser.add_argument(
        "--deployment-first-step-summary-csv",
        type=Path,
        default=DEFAULT_DEPLOYMENT_FIRST_STEP,
    )
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
    parser.add_argument("--max-rounds", type=int, default=20)
    return parser.parse_args(argv)


def _deterministic_average_precision(
    group: pd.DataFrame,
    metric: str,
    *,
    truth_column: str = "n1_critical",
) -> float:
    ranked = group.sort_values(
        [metric, "line_label"],
        ascending=[False, True],
        kind="stable",
    )
    truth = ranked[truth_column].astype(bool).to_numpy()
    if not truth.any():
        return 0.0
    precision_at_hit = np.cumsum(truth) / (np.arange(len(truth)) + 1)
    return float(precision_at_hit[truth].mean())


def _mean_seed_ap(table: pd.DataFrame, metric: str, split: str) -> float:
    rows = table.loc[table["split"].eq(split)]
    values = []
    for _, group in rows.groupby("seed", sort=True):
        values.append(_deterministic_average_precision(group, metric))
    return float(np.mean(values))


def _rank_at_positive_recall(
    group: pd.DataFrame,
    metric: str,
    recall: float,
) -> int:
    ranked = group.sort_values(
        [metric, "line_label"],
        ascending=[False, True],
        kind="stable",
    )
    truth = ranked["n1_critical"].astype(bool).to_numpy()
    required = int(np.ceil(int(truth.sum()) * float(recall)))
    if required <= 0:
        return 0
    positions = np.flatnonzero(np.cumsum(truth) >= required)
    return int(positions[0] + 1) if len(positions) else int(len(ranked))


def prepare_proxy_score_export(
    table: pd.DataFrame,
    selected_metric: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate label-free policy scores from the high-fidelity audit table."""

    required = {"seed", "split", "line_label", "n1_critical", selected_metric}
    missing = sorted(required - set(table))
    if missing:
        raise ValueError(f"Proxy score table is missing fields: {missing}")
    ranked = table.copy()
    ranked["selected_proxy_score"] = pd.to_numeric(
        ranked[selected_metric],
        errors="raise",
    ).astype(float)
    ranked["selected_proxy_metric"] = str(selected_metric)
    ranked = ranked.sort_values(
        ["seed", "selected_proxy_score", "line_label"],
        ascending=[True, False, True],
        kind="stable",
    ).reset_index(drop=True)
    ranked["selected_proxy_rank"] = (
        ranked.groupby("seed", sort=False).cumcount() + 1
    )
    policy_columns = [
        "seed",
        "split",
        "line_label",
        "selected_proxy_score",
        "selected_proxy_metric",
        "selected_proxy_rank",
    ]
    policy = ranked[policy_columns].copy()
    audit = policy.copy()
    audit["n1_critical"] = ranked["n1_critical"].astype(int).to_numpy()
    return policy, audit


def compute_label_free_iterative_proxy_scores(
    *,
    signed_flow: np.ndarray,
    rate_a: np.ndarray,
    line_labels: np.ndarray,
    branch_from_bus: np.ndarray,
    branch_to_bus: np.ndarray,
    branch_x: np.ndarray,
    branch_tap_ratio: np.ndarray,
    beta: float,
    max_rounds: int,
    topology_cache: dict[bytes, Any] | None = None,
) -> pd.DataFrame:
    """Compute deployable N-1 proxy scores without reading cascade labels."""

    labels = np.asarray(line_labels, dtype=str)
    flow = np.asarray(signed_flow, dtype=np.float64)
    limits = np.asarray(rate_a, dtype=np.float64)
    taps = np.asarray(branch_tap_ratio, dtype=np.float64)
    num_lines = len(labels)
    arrays = (
        flow,
        limits,
        np.asarray(branch_from_bus),
        np.asarray(branch_to_bus),
        np.asarray(branch_x),
        taps,
    )
    if any(value.shape != (num_lines,) for value in arrays):
        raise ValueError("Iterative proxy branch arrays and line labels must align.")
    if len(set(labels.tolist())) != num_lines:
        raise ValueError("Iterative proxy line labels must be unique.")

    cache = topology_cache if topology_cache is not None else {}
    records = []
    for line_idx, line_label in enumerate(labels):
        result = iterative_dc_lodf_relay_proxy(
            flow,
            limits,
            np.ones(num_lines, dtype=bool),
            line_idx,
            branch_from_bus=branch_from_bus,
            branch_to_bus=branch_to_bus,
            branch_x=branch_x,
            branch_tap_ratio=taps,
            beta=float(beta),
            max_rounds=int(max_rounds),
            topology_cache=cache,
        )
        records.append(
            {
                "line_label": str(line_label),
                "iterative_num_relay_trips": int(result.num_relay_trips),
                "iterative_max_event_loading_ratio": float(
                    result.max_event_loading_ratio
                ),
                "iterative_num_singular_outages": int(
                    result.num_singular_outages
                ),
            }
        )
    table = pd.DataFrame(records)
    table["iterative_composite_score"] = (
        np.log1p(table["iterative_max_event_loading_ratio"])
        + table["iterative_num_relay_trips"]
        + 5.0 * table["iterative_num_singular_outages"]
    )
    return table


def evaluate_proxy(args: argparse.Namespace) -> dict[str, Any]:
    if not args.dataset_npz.exists():
        raise FileNotFoundError(
            f"Missing local IEEE118 GCN dataset: {args.dataset_npz}. "
            "This proxy audit will not regenerate cascade truth."
        )
    if args.max_rounds <= 0 or args.beta <= 0.0:
        raise ValueError("--max-rounds and --beta must be positive.")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(args.dataset_npz, allow_pickle=True)
    required = {
        "seed",
        "split",
        "sample_type",
        "line_labels",
        "source_y_gcn",
        "source_loss_mask",
        "branch_from_bus",
        "branch_to_bus",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"N-1 proxy dataset is missing arrays: {missing}")
    s0_rows = np.where(
        (data["sample_type"].astype(str) == "S0")
        & np.isin(data["split"].astype(str), ["validation", "test"])
    )[0]
    if not len(s0_rows):
        raise ValueError("No validation/test S0 states are available.")

    adapter = build_case_adapter("ieee118")
    branch_x = adapter.case["branch"][:, BR_X].astype(np.float64)
    branch_tap = adapter.case["branch"][:, TAP].astype(np.float64)
    line_labels = data["line_labels"].astype(str)
    topology_cache: dict[bytes, Any] = {}
    records = []
    for row_idx in s0_rows:
        seed = int(data["seed"][row_idx])
        scenario = apply_load_scenario(
            adapter.case,
            seed=seed,
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
        rate_a = scenario["branch"][:, RATE_A].astype(np.float64)
        status = np.ones(len(line_labels), dtype=bool)
        source_mask = data["source_loss_mask"][row_idx].astype(bool)
        for line_idx, line_label in enumerate(line_labels):
            result = iterative_dc_lodf_relay_proxy(
                signed_flow,
                rate_a,
                status,
                line_idx,
                branch_from_bus=data["branch_from_bus"],
                branch_to_bus=data["branch_to_bus"],
                branch_x=branch_x,
                branch_tap_ratio=branch_tap,
                beta=float(args.beta),
                max_rounds=int(args.max_rounds),
                topology_cache=topology_cache,
            )
            records.append(
                {
                    "seed": seed,
                    "split": str(data["split"][row_idx]),
                    "line_label": str(line_label),
                    "n1_label_available": bool(source_mask[line_idx]),
                    "n1_critical": int(
                        data["source_y_gcn"][row_idx, line_idx]
                    ),
                    "iterative_num_relay_trips": int(
                        result.num_relay_trips
                    ),
                    "iterative_max_event_loading_ratio": float(
                        result.max_event_loading_ratio
                    ),
                    "iterative_num_singular_outages": int(
                        result.num_singular_outages
                    ),
                }
            )
    table = pd.DataFrame(records)
    table["iterative_composite_score"] = (
        np.log1p(table["iterative_max_event_loading_ratio"])
        + table["iterative_num_relay_trips"]
        + 5.0 * table["iterative_num_singular_outages"]
    )
    table = table.loc[table["n1_label_available"]].copy()
    candidate_metrics = [
        "iterative_num_relay_trips",
        "iterative_max_event_loading_ratio",
        "iterative_composite_score",
    ]
    validation_scores = {
        metric: _mean_seed_ap(table, metric, "validation")
        for metric in candidate_metrics
    }
    selected_metric = max(
        candidate_metrics,
        key=lambda metric: (validation_scores[metric], metric),
    )
    validation_policy, validation_audit = prepare_proxy_score_export(
        table.loc[table["split"].eq("validation")],
        selected_metric,
    )
    validation_policy.to_csv(
        args.output_dir
        / "ieee118_iterative_lodf_n1_proxy_validation_scores.csv",
        index=False,
        encoding="utf-8-sig",
    )
    validation_audit.to_csv(
        args.output_dir
        / "ieee118_iterative_lodf_n1_proxy_validation_audit.csv",
        index=False,
        encoding="utf-8-sig",
    )
    test_ap = _mean_seed_ap(table, selected_metric, "test")
    validation_gate_rows = []
    for seed, group in table.loc[
        table["split"].eq("validation")
    ].groupby("seed", sort=True):
        for recall in (0.90, 0.95, 1.00):
            validation_gate_rows.append(
                {
                    "seed": int(seed),
                    "target_n1_recall": float(recall),
                    "required_proxy_gate_size": _rank_at_positive_recall(
                        group,
                        selected_metric,
                        recall,
                    ),
                }
            )
    validation_gate = pd.DataFrame(validation_gate_rows)
    selected_gate_size = int(
        validation_gate.loc[
            validation_gate["target_n1_recall"].eq(1.0),
            "required_proxy_gate_size",
        ].max()
    )
    primary_gate_size = int(
        np.ceil(
            validation_gate.loc[
                validation_gate["target_n1_recall"].eq(0.90),
                "required_proxy_gate_size",
            ].median()
        )
    )
    conservative_gate_size = int(
        validation_gate.loc[
            validation_gate["target_n1_recall"].eq(0.90),
            "required_proxy_gate_size",
        ].max()
    )
    validation_gate.to_csv(
        args.output_dir
        / "ieee118_iterative_lodf_n1_proxy_validation_gate_sizes.csv",
        index=False,
        encoding="utf-8-sig",
    )

    training_distribution_test = table.loc[table["split"].eq("test")].copy()
    training_distribution_test["selected_proxy_score"] = (
        training_distribution_test[selected_metric]
    )
    training_distribution_test.sort_values(
        ["selected_proxy_score", "line_label"],
        ascending=[False, True],
        kind="stable",
    ).to_csv(
        args.output_dir / "ieee118_iterative_lodf_n1_proxy_test_scores.csv",
        index=False,
        encoding="utf-8-sig",
    )

    deployment_scenario = apply_load_scenario(
        adapter.case,
        seed=int(args.deployment_seed),
        load_scale=float(args.deployment_load_scale),
        low=float(args.load_random_low),
        high=float(args.load_random_high),
    )
    deployment_scenario = apply_thermal_limit_mode(
        deployment_scenario,
        limit_mode=str(args.limit_mode),
        flow_limit_scale=float(args.flow_limit_scale),
        min_rate_a=float(args.min_rate_a),
    )
    deployment_flow = deployment_scenario["branch"][:, PF].astype(np.float64)
    deployment_rate = deployment_scenario["branch"][:, RATE_A].astype(np.float64)
    deployment = compute_label_free_iterative_proxy_scores(
        signed_flow=deployment_flow,
        rate_a=deployment_rate,
        line_labels=line_labels,
        branch_from_bus=data["branch_from_bus"],
        branch_to_bus=data["branch_to_bus"],
        branch_x=branch_x,
        branch_tap_ratio=branch_tap,
        beta=float(args.beta),
        max_rounds=int(args.max_rounds),
        topology_cache=topology_cache,
    )
    deployment.insert(0, "seed", int(args.deployment_seed))
    deployment["selected_proxy_score"] = deployment[selected_metric]
    deployment["selected_proxy_metric"] = selected_metric
    deployment = deployment.sort_values(
        ["selected_proxy_score", "line_label"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    deployment["selected_proxy_rank"] = np.arange(1, len(deployment) + 1)
    deployment[
        [
            "seed",
            "line_label",
            "selected_proxy_score",
            "selected_proxy_metric",
            "selected_proxy_rank",
        ]
    ].to_csv(
        args.output_dir
        / "ieee118_iterative_lodf_n1_proxy_deployment_scores.csv",
        index=False,
        encoding="utf-8-sig",
    )
    deployment_ap = None
    deployment_num_critical = None
    if args.deployment_first_step_summary_csv.exists():
        first_step = pd.read_csv(args.deployment_first_step_summary_csv)
        required_first_step = {"first_line", "first_step_critical"}
        missing_first_step = sorted(required_first_step - set(first_step))
        if missing_first_step:
            raise ValueError(
                "Deployment first-step summary is missing fields: "
                f"{missing_first_step}"
            )
        truth_by_line = dict(
            zip(
                first_step["first_line"].astype(str),
                first_step["first_step_critical"].astype(str)
                .str.lower()
                .eq("true")
                .astype(int),
            )
        )
        if set(line_labels) - set(truth_by_line):
            raise ValueError(
                "Deployment first-step summary does not cover every line."
            )
        deployment["n1_critical_audit_only"] = [
            truth_by_line[label] for label in deployment["line_label"]
        ]
        deployment_num_critical = int(
            deployment["n1_critical_audit_only"].sum()
        )
        deployment_ap = _deterministic_average_precision(
            deployment,
            "selected_proxy_score",
            truth_column="n1_critical_audit_only",
        )
        deployment.sort_values(
            ["selected_proxy_score", "line_label"],
            ascending=[False, True],
            kind="stable",
        ).to_csv(
            args.output_dir
            / "ieee118_iterative_lodf_n1_proxy_deployment_audit.csv",
            index=False,
            encoding="utf-8-sig",
        )
    per_seed_rows = []
    for metric in candidate_metrics:
        for split_name in ("validation", "test"):
            for seed, group in table.loc[
                table["split"].eq(split_name)
            ].groupby("seed", sort=True):
                per_seed_rows.append(
                    {
                        "metric": metric,
                        "split": split_name,
                        "seed": int(seed),
                        "num_lines": int(len(group)),
                        "num_n1_critical": int(group["n1_critical"].sum()),
                        "average_precision": _deterministic_average_precision(
                            group,
                            metric,
                        ),
                    }
                )
    pd.DataFrame(per_seed_rows).to_csv(
        args.output_dir / "ieee118_iterative_lodf_n1_proxy_ap_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary = {
        "status": "complete",
        "research_stage": "Phase 3 validation-frozen low-fidelity N-1 proxy",
        "num_validation_seeds": int(
            table.loc[table["split"].eq("validation"), "seed"].nunique()
        ),
        "num_test_seeds": int(
            table.loc[table["split"].eq("test"), "seed"].nunique()
        ),
        "candidate_metrics": validation_scores,
        "selected_metric_by_validation_mean_ap": selected_metric,
        "training_distribution_test_average_precision": test_ap,
        "deployment_load_scale": float(args.deployment_load_scale),
        "deployment_seed": int(args.deployment_seed),
        "deployment_num_n1_critical": deployment_num_critical,
        "deployment_average_precision": deployment_ap,
        "validation_selected_proxy_gate_size_for_100pct_n1_recall": (
            selected_gate_size
        ),
        "validation_selected_primary_gate_size_median_K_for_90pct_n1_recall": (
            primary_gate_size
        ),
        "validation_selected_conservative_gate_size_max_K_for_90pct_n1_recall": (
            conservative_gate_size
        ),
        "validation_proxy_gate_size_summary": (
            validation_gate.groupby("target_n1_recall")[
                "required_proxy_gate_size"
            ]
            .agg(["mean", "max"])
            .reset_index()
            .to_dict("records")
        ),
        "num_cached_topologies": int(len(topology_cache)),
        "physics_cost": {
            "base_dcopf_calls": int(len(s0_rows) + 1),
            "high_fidelity_n1_cascade_calls": 0,
            "high_fidelity_n2_cascade_calls": 0,
        },
        "model_limit": (
            "The iterative proxy trips overloaded lines with LODF updates but "
            "does not solve islands, redispatch generation, or shed load."
        ),
        "deployment_score_file_has_high_fidelity_labels": False,
        "validation_score_file_has_high_fidelity_labels": False,
        "configuration": {
            "limit_mode": str(args.limit_mode),
            "flow_limit_scale": float(args.flow_limit_scale),
            "min_rate_a": float(args.min_rate_a),
            "beta": float(args.beta),
            "max_rounds": int(args.max_rounds),
        },
    }
    (args.output_dir / "ieee118_iterative_lodf_n1_proxy_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    print(json.dumps(evaluate_proxy(parse_args()), indent=2))


if __name__ == "__main__":
    main()
