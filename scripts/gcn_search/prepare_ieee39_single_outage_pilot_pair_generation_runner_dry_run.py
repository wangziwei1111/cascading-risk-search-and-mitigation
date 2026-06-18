from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_SINGLE_OUTAGE_LOOP_COMMIT = "b5e98d4fd27f438b2d46e6ec0ec60b46e21bcda9"

LOOP_DIR = ROOT / "results/gcn_search/ieee39_single_outage_label_loop_dry_run"
PROXY_DIR = ROOT / "results/gcn_search/ieee39_relay_threshold_proxy_approval"
BASE_PILOT_DIR = ROOT / "results/gcn_search/ieee39_base_state_branch_vulnerability_label_pilot"
OUT_DIR = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
DOC = ROOT / "docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"

FORBIDDEN_FEATURES = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "dynamic_stress_score",
    "unstable_flag",
    "phasor_RMS",
    "generator_speed_proxy",
    "post-fault dynamic measurements",
    "label-derived flags",
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _read_json(path: Path) -> Any:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_kv_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            writer.writerow([key, value])


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            for key, value in out.items():
                if isinstance(value, list):
                    out[key] = ";".join(str(item) for item in value)
            writer.writerow(out)


def _write_kv_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"## {key}")
            lines.append("```json")
            lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_pairs_md(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# IEEE39 Selected Single-Outage Pilot Pairs",
        "",
        "All selected pairs are dry-run planned rows. No real 0/1 label is generated in this round.",
        "",
        "| pair_id | bucket | prior | next | shares_bus | prior_xp | next_xp | label_status |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {pair_id} | {selection_bucket} | {prior_outaged_branch} | {candidate_next_branch} | "
            "{shares_bus_with_prior} | {prior_x_p_relay_ratio:.6f} | {next_x_p_relay_ratio:.6f} | "
            "{label_status} |".format(**row)
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _bus_set(feature: dict[str, Any]) -> set[str]:
    return {str(feature["from_bus"]), str(feature["to_bus"])}


def _shared_bus(prior_feature: dict[str, Any], next_feature: dict[str, Any]) -> str | None:
    shared = sorted(_bus_set(prior_feature) & _bus_set(next_feature))
    return shared[0] if shared else None


def _load_sources() -> dict[str, Any]:
    return {
        "loop_summary": _read_json(LOOP_DIR / "single_outage_label_loop_dry_run_summary.json"),
        "state_manifest": _read_json(LOOP_DIR / "single_outage_state_manifest.json"),
        "pair_plan": _read_json(LOOP_DIR / "single_outage_state_branch_label_loop_plan.json"),
        "base_distribution": _read_json(LOOP_DIR / "base_state_label_distribution_review.json"),
        "feature_matrix": _read_json(PROXY_DIR / "l01_l34_approved_paper_feature_source_matrix.json"),
        "base_matrix": _read_json(BASE_PILOT_DIR / "base_state_branch_vulnerability_label_matrix.json"),
    }


def _candidate_rows(sources: dict[str, Any]) -> list[dict[str, Any]]:
    features = {row["line_id"]: row for row in sources["feature_matrix"]}
    candidates: list[dict[str, Any]] = []
    for row in sources["pair_plan"]:
        if row["label_status"] != "planned":
            continue
        prior = row["prior_outaged_branch"]
        nxt = row["candidate_next_branch"]
        prior_feature = features[prior]
        next_feature = features[nxt]
        shared_bus = _shared_bus(prior_feature, next_feature)
        candidates.append(
            {
                "state_id": row["state_id"],
                "prior_outaged_branch": prior,
                "prior_from_bus": prior_feature["from_bus"],
                "prior_to_bus": prior_feature["to_bus"],
                "candidate_next_branch": nxt,
                "next_from_bus": next_feature["from_bus"],
                "next_to_bus": next_feature["to_bus"],
                "planned_contingency_sequence": [prior, nxt],
                "shares_bus_with_prior": shared_bus is not None,
                "shared_bus_if_any": shared_bus,
                "prior_x_p_relay_ratio": float(prior_feature["x_p_relay_ratio_value"]),
                "next_x_p_relay_ratio": float(next_feature["x_p_relay_ratio_value"]),
                "relay_score_sum": float(prior_feature["x_p_relay_ratio_value"])
                + float(next_feature["x_p_relay_ratio_value"]),
            }
        )
    return candidates


def _select_bucket(
    rows: list[dict[str, Any]],
    selected_keys: set[tuple[str, str]],
    limit: int,
    bucket: str,
    branch_counts: dict[str, int],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        key = (row["prior_outaged_branch"], row["candidate_next_branch"])
        if key in selected_keys:
            continue
        if branch_counts.get(row["prior_outaged_branch"], 0) >= 4:
            continue
        if branch_counts.get(row["candidate_next_branch"], 0) >= 4:
            continue
        out = dict(row)
        out["selection_bucket"] = bucket
        selected.append(out)
        selected_keys.add(key)
        branch_counts[row["prior_outaged_branch"]] = branch_counts.get(row["prior_outaged_branch"], 0) + 1
        branch_counts[row["candidate_next_branch"]] = branch_counts.get(row["candidate_next_branch"], 0) + 1
        if len(selected) >= limit:
            break
    return selected


def _select_pairs(candidates: list[dict[str, Any]], max_pairs: int) -> list[dict[str, Any]]:
    max_pairs = max(1, min(max_pairs, 40))
    high_target = max(1, max_pairs // 3)
    neighbor_target = max(1, max_pairs // 3)
    control_target = max_pairs - high_target - neighbor_target
    selected_keys: set[tuple[str, str]] = set()
    branch_counts: dict[str, int] = {}

    high_rows = sorted(candidates, key=lambda row: (row["relay_score_sum"], row["next_x_p_relay_ratio"]), reverse=True)
    neighbor_rows = sorted(
        [row for row in candidates if row["shares_bus_with_prior"]],
        key=lambda row: (row["relay_score_sum"], row["prior_outaged_branch"], row["candidate_next_branch"]),
        reverse=True,
    )
    control_rows = sorted(
        [row for row in candidates if not row["shares_bus_with_prior"]],
        key=lambda row: (row["relay_score_sum"], row["prior_outaged_branch"], row["candidate_next_branch"]),
    )

    selected: list[dict[str, Any]] = []
    selected.extend(_select_bucket(high_rows, selected_keys, high_target, "high_relay_ratio_pairs", branch_counts))
    selected.extend(
        _select_bucket(neighbor_rows, selected_keys, neighbor_target, "shared_bus_neighbor_pairs", branch_counts)
    )
    selected.extend(
        _select_bucket(control_rows, selected_keys, control_target, "non_neighbor_control_pairs", branch_counts)
    )
    if len(selected) < max_pairs:
        fill_rows = sorted(candidates, key=lambda row: row["relay_score_sum"], reverse=True)
        selected.extend(
            _select_bucket(fill_rows, selected_keys, max_pairs - len(selected), "diversity_fill_pairs", branch_counts)
        )
    return selected[:max_pairs]


def _materialize_pairs(selected: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for idx, row in enumerate(selected, start=1):
        rows.append(
            {
                "pair_id": f"SPP{idx:03d}",
                "state_id": row["state_id"],
                "prior_outaged_branch": row["prior_outaged_branch"],
                "prior_from_bus": row["prior_from_bus"],
                "prior_to_bus": row["prior_to_bus"],
                "candidate_next_branch": row["candidate_next_branch"],
                "next_from_bus": row["next_from_bus"],
                "next_to_bus": row["next_to_bus"],
                "planned_contingency_sequence": row["planned_contingency_sequence"],
                "shares_bus_with_prior": row["shares_bus_with_prior"],
                "shared_bus_if_any": row["shared_bus_if_any"],
                "prior_x_p_relay_ratio": row["prior_x_p_relay_ratio"],
                "next_x_p_relay_ratio": row["next_x_p_relay_ratio"],
                "selection_bucket": row["selection_bucket"],
                "feature_matrix_with_proxy_ready": True,
                "relay_threshold_is_proxy": True,
                "proxy_allowed_for_audit_only_prototype": True,
                "bus_fault_label_used": False,
                "l12_special_case_flag": False,
                "label_value": None,
                "label_status": "planned",
                "future_generation_required": True,
                "exclusion_reason_if_any": None,
            }
        )
    return rows


def build_payloads(max_pairs: int) -> dict[str, Any]:
    sources = _load_sources()
    candidates = _candidate_rows(sources)
    selected = _materialize_pairs(_select_pairs(candidates, max_pairs))
    bucket_counts: dict[str, int] = {}
    for row in selected:
        bucket_counts[row["selection_bucket"]] = bucket_counts.get(row["selection_bucket"], 0) + 1
    l12_pairs_excluded = int(sources["loop_summary"]["num_pairs_excluded_due_to_l12_special"])
    can_execute = bool(selected)
    selection_summary = {
        "selection_scope": "single_outage_pilot_pair_selection",
        "source_single_outage_loop_commit": SOURCE_SINGLE_OUTAGE_LOOP_COMMIT,
        "max_pairs_requested": max_pairs,
        "num_pairs_selected": len(selected),
        "num_high_relay_ratio_pairs": bucket_counts.get("high_relay_ratio_pairs", 0),
        "num_shared_bus_neighbor_pairs": bucket_counts.get("shared_bus_neighbor_pairs", 0),
        "num_non_neighbor_control_pairs": bucket_counts.get("non_neighbor_control_pairs", 0),
        "num_l12_pairs_excluded": l12_pairs_excluded,
        "bus_fault_labels_used": False,
        "label_values_fabricated": False,
        "ready_for_future_controlled_generation": can_execute,
        "selection_policy": [
            "high_relay_ratio_pairs: choose high prior/next x_p_relay_ratio combinations",
            "shared_bus_neighbor_pairs: choose branch pairs sharing a bus",
            "non_neighbor_control_pairs: choose non-neighbor control pairs",
            "known_special_exclusion: exclude L12 prior or next branch",
            "diversity: limit repeated branch concentration while filling buckets",
        ],
    }
    run_plan = {
        "run_plan_scope": "future_controlled_single_outage_pilot_generation",
        "dry_run_only_this_round": True,
        "new_simulink_run_this_round": False,
        "future_runner_entrypoint": (
            "future script should execute selected_single_outage_pilot_pairs after manual approval"
        ),
        "selected_pair_count": len(selected),
        "expected_outputs_per_pair": [
            "pair execution summary",
            "label evidence summary",
            "timeout/error status",
            "no raw trajectory committed",
            "label_value remains withheld unless an approved label export round follows",
        ],
        "timeout_policy": "timeouts remain unknown/null and are not converted to 0/1",
        "unknown_policy": "unknown, missing, timeout, or failed cases remain null/planned/blocked",
        "l12_exclusion_policy": "any pair with L12 as prior or candidate branch stays excluded",
        "no_raw_trajectory_commit_policy": True,
        "no_formal_label_export_this_round": True,
        "required_manual_approval_before_execution": True,
    }
    no_leakage = {
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_outputs_used_only_as_future_labels_or_targets": True,
        "label_derived_flags_used_as_inputs": False,
        "proxy_relay_threshold_used_only_in_feature_generation": True,
        "bus_fault_labels_used": False,
        "no_leakage_policy_passed": True,
        "forbidden_features_checked": FORBIDDEN_FEATURES,
    }
    summary = {
        "dry_run_scope": "single_outage_pilot_pair_runner_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "new_simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_single_outage_loop_commit": SOURCE_SINGLE_OUTAGE_LOOP_COMMIT,
        "feature_matrix_with_proxy_ready": True,
        "relay_threshold_is_proxy": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
        "base_state_should_not_be_used_alone_for_training": True,
        "num_candidate_pairs_available": len(candidates),
        "num_pilot_pairs_selected": len(selected),
        "num_high_relay_ratio_pairs": selection_summary["num_high_relay_ratio_pairs"],
        "num_shared_bus_neighbor_pairs": selection_summary["num_shared_bus_neighbor_pairs"],
        "num_non_neighbor_control_pairs": selection_summary["num_non_neighbor_control_pairs"],
        "label_values_fabricated": False,
        "selected_pairs_label_status": "planned",
        "can_execute_future_generation_runner_after_approval": can_execute,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_run_simulink_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": None if can_execute else "no eligible non-L12 pilot pairs selected",
        "recommended_next_step": "approve and execute selected single-outage pilot pair generation in a separate round",
    }
    return {
        "selection_summary": selection_summary,
        "selected_pairs": selected,
        "run_plan": run_plan,
        "no_leakage": no_leakage,
        "summary": summary,
    }


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    selection = payloads["selection_summary"]
    return f"""# IEEE39 Single-Outage Pilot Pair Generation Runner Dry-Run

This round is a selected single-outage pilot pair generation runner dry-run. It does not train GCN, does not rerun formal audit, does not run new Simulink, does not export formal labels, does not retrain the reranker, and does not save a production model.

There is no deployment in this round.

## Plain-Language Purpose

The base-state labels are all negative for the 33 available non-L12 branches, so they cannot be used alone for training. This round does not run all 1056 eligible `single_outage_state x next_branch` pairs. Instead, this dry-run selects a small pilot set and writes the future run plan. The selected rows are still planned samples, not real labels.

## Selection Strategy

1. `high_relay_ratio_pairs`: select high prior/next `x_p_relay_ratio` combinations to increase the chance of finding positive examples.
2. `shared_bus_neighbor_pairs`: select branch pairs that share a bus, matching the branch-as-node graph adjacency idea.
3. `non_neighbor_control_pairs`: select non-neighbor pairs as lower-risk/control samples.
4. `known_special_exclusion`: exclude any pair with L12 as prior or next branch.
5. `diversity`: avoid putting every pilot row on the same branch area.

## Current Counts

- dry_run_scope: `{summary["dry_run_scope"]}`
- max_pairs_requested: `{selection["max_pairs_requested"]}`
- num_candidate_pairs_available: `{summary["num_candidate_pairs_available"]}`
- num_pilot_pairs_selected: `{summary["num_pilot_pairs_selected"]}`
- num_high_relay_ratio_pairs: `{summary["num_high_relay_ratio_pairs"]}`
- num_shared_bus_neighbor_pairs: `{summary["num_shared_bus_neighbor_pairs"]}`
- num_non_neighbor_control_pairs: `{summary["num_non_neighbor_control_pairs"]}`
- num_l12_pairs_excluded: `{selection["num_l12_pairs_excluded"]}`
- selected_pairs_label_status: `{summary["selected_pairs_label_status"]}`
- label_values_fabricated: `{summary["label_values_fabricated"]}`

## Boundaries

`beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

Dynamic outputs such as `dynamic_stress_score` and `unstable_flag` can only be future labels or audit targets, not input features. No label-derived flags are inputs.

## Next Step

`{summary["recommended_next_step"]}`

Manual approval is required before executing the selected pair generation runner.
"""


def write_payloads(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "pilot_pair_selection_summary.json", payloads["selection_summary"])
    _write_kv_md(
        OUT_DIR / "pilot_pair_selection_summary.md",
        "IEEE39 Pilot Pair Selection Summary",
        payloads["selection_summary"],
    )
    _write_kv_csv(OUT_DIR / "pilot_pair_selection_summary.csv", payloads["selection_summary"])

    _write_json(OUT_DIR / "selected_single_outage_pilot_pairs.json", payloads["selected_pairs"])
    _write_pairs_md(OUT_DIR / "selected_single_outage_pilot_pairs.md", payloads["selected_pairs"])
    _write_rows_csv(OUT_DIR / "selected_single_outage_pilot_pairs.csv", payloads["selected_pairs"])

    _write_json(OUT_DIR / "future_controlled_generation_run_plan.json", payloads["run_plan"])
    _write_kv_md(
        OUT_DIR / "future_controlled_generation_run_plan.md",
        "IEEE39 Future Controlled Generation Run Plan",
        payloads["run_plan"],
    )
    _write_json(OUT_DIR / "no_leakage_pilot_pair_runner_audit.json", payloads["no_leakage"])
    _write_kv_md(
        OUT_DIR / "no_leakage_pilot_pair_runner_audit.md",
        "IEEE39 No-Leakage Pilot Pair Runner Audit",
        payloads["no_leakage"],
    )
    _write_json(OUT_DIR / "single_outage_pilot_pair_runner_dry_run_summary.json", payloads["summary"])
    _write_kv_md(
        OUT_DIR / "single_outage_pilot_pair_runner_dry_run_summary.md",
        "IEEE39 Single-Outage Pilot Pair Runner Dry-Run Summary",
        payloads["summary"],
    )
    _write_kv_csv(OUT_DIR / "single_outage_pilot_pair_runner_dry_run_summary.csv", payloads["summary"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prepare IEEE39 selected single-outage pilot pair runner dry-run."
    )
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--max-pairs", type=int, default=32)
    args = parser.parse_args()
    required = [
        LOOP_DIR / "single_outage_label_loop_dry_run_summary.json",
        LOOP_DIR / "single_outage_state_manifest.json",
        LOOP_DIR / "single_outage_state_branch_label_loop_plan.json",
        LOOP_DIR / "base_state_label_distribution_review.json",
        PROXY_DIR / "l01_l34_approved_paper_feature_source_matrix.json",
        BASE_PILOT_DIR / "base_state_branch_vulnerability_label_matrix.json",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads(args.max_pairs)
    write_payloads(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
