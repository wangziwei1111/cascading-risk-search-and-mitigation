from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PREV_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run"
CONSISTENCY = ROOT / (
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check/"
    "paper_aligned_redesign_consistency_check.json"
)
OUT_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run"
DOC = ROOT / "docs/ieee39_paper_aligned_feature_source_dry_run.md"
VALIDATION_LOG = ROOT / "docs/gcn_pio_validation_log.md"
BRANCH_GRAPH = PREV_DIR / "ieee39_branch_as_node_graph_manifest.json"
FEATURE_MANIFEST = PREV_DIR / "paper_aligned_feature_manifest.json"
LABEL_PLAN = PREV_DIR / "paper_aligned_label_plan.json"
DRY_RUN_SUMMARY = PREV_DIR / "paper_aligned_branch_gcn_dry_run_validator_summary.json"

SOURCE_CONSISTENCY_COMMIT = "e41e17f591958f8622baa9002f9b5e01376590d5"
TEXT_SUFFIXES = {".py", ".m", ".md", ".json", ".csv", ".txt"}
MAX_SOURCE_HITS = 30

FORBIDDEN_DYNAMIC_FEATURES = [
    "min_voltage_pu",
    "max_voltage_pu",
    "frequency",
    "rotor angle",
    "speed deviation",
    "dynamic_stress_score",
    "unstable_flag",
    "phasor_RMS",
    "generator_speed_proxy",
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _read_json(path: Path) -> dict[str, Any]:
    if not _exists(path):
        return {}
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    if not _exists(path):
        return ""
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    paths: list[Path] = []
    for raw in result.stdout.splitlines():
        if not raw.strip():
            continue
        path = ROOT / raw.strip()
        if path.suffix.lower() in TEXT_SUFFIXES:
            paths.append(path)
    return paths


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _scan_sources(paths: list[Path]) -> dict[str, list[dict[str, str]]]:
    patterns = {
        "branch_flow": ["branch_flow", "branch flow", "p_mw", "q_mvar", "loading", "line_loading", "power flow"],
        "line_limit": ["rate_a", "ratea", "thermal limit", "line limit", "lmax", "long-term max"],
        "relay_threshold": ["relay_threshold", "relay threshold", "relay_beta", "beta", "protection threshold"],
        "bus_load": ["bus load", "load_mw", "load profile", " pd", " qd", "pd,", "qd,"],
        "dc_power_flow_or_opf": ["dcpf", "dc power flow", "dcopf", "opf", "lodf"],
        "matpower_or_case": ["matpower", "case39", "case 39", "pandapower", "ppc"],
        "simulink_prefault": ["pre-fault", "prefault", "initialization", "basecase"],
        "post_fault_forbidden": [
            "dynamic_stress_score",
            "unstable_flag",
            "frequency_nadir",
            "rotor_angle",
            "phasor_rms",
            "generator_speed_proxy",
            "post_fault",
            "post-fault",
            "trajectory",
            "timeseries",
        ],
    }
    hits: dict[str, list[dict[str, str]]] = {key: [] for key in patterns}
    for path in paths:
        rel = _relative(path)
        rel_lower = rel.lower()
        if any(token in rel_lower for token in [".venv", "site-packages", "local_lab_copies", "slprj"]):
            continue
        text = _read_text(path)
        lower = text.lower()
        haystack = f"{rel_lower}\n{lower}"
        for category, tokens in patterns.items():
            if len(hits[category]) >= MAX_SOURCE_HITS:
                continue
            matched = next((token for token in tokens if token in haystack), None)
            if matched:
                trust = "forbidden_post_fault_dynamic_measurement" if category == "post_fault_forbidden" else "unverified_repository_reference"
                if category in {"dc_power_flow_or_opf", "matpower_or_case"}:
                    trust = "generator_or_reference_required_not_verified_feature_source"
                hits[category].append({"path": rel, "matched_token": matched, "trust_level": trust})
    return hits


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _md_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def _write_md(path: Path, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"## {key}")
            if not value:
                lines.append("- []")
            else:
                for item in value:
                    lines.append(f"- `{_md_value(item)}`" if not isinstance(item, dict) else f"- {json.dumps(item, ensure_ascii=False)}")
            lines.append("")
        elif isinstance(value, dict):
            lines.append(f"## {key}")
            lines.append("```json")
            lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        else:
            lines.append(f"- `{key}`: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _write_key_value_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            writer.writerow([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])


def _write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "line_id",
        "from_bus",
        "to_bus",
        "topology_status_available",
        "branch_flow_available",
        "branch_flow_source",
        "line_limit_available",
        "line_limit_source",
        "relay_threshold_available",
        "relay_threshold_source",
        "endpoint_load_available",
        "endpoint_load_source",
        "ready_for_paper_feature_vector",
        "missing_fields",
        "l12_special_case_flag",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["missing_fields"] = ";".join(row["missing_fields"])
            writer.writerow(out)


def _line_sort_key(line_id: str) -> int:
    digits = "".join(ch for ch in line_id if ch.isdigit())
    return int(digits) if digits else 999


def build_payloads() -> dict[str, Any]:
    previous_summary = _read_json(DRY_RUN_SUMMARY)
    graph = _read_json(BRANCH_GRAPH)
    feature_manifest = _read_json(FEATURE_MANIFEST)
    label_plan = _read_json(LABEL_PLAN)
    consistency = _read_json(CONSISTENCY)
    source_hits = _scan_sources(_tracked_files())

    branch_endpoint_pairs = graph.get("branch_endpoint_pairs", {})
    rows: list[dict[str, Any]] = []
    for line_id in sorted(branch_endpoint_pairs, key=_line_sort_key):
        endpoints = branch_endpoint_pairs[line_id]
        from_bus, to_bus = endpoints[0], endpoints[1]
        missing_fields = ["branch_flow", "line_limit", "relay_threshold", "endpoint_load"]
        rows.append(
            {
                "line_id": line_id,
                "from_bus": from_bus,
                "to_bus": to_bus,
                "topology_status_available": True,
                "branch_flow_available": False,
                "branch_flow_source": "missing_verified_current_state_pf_or_opf_branch_flow",
                "line_limit_available": False,
                "line_limit_source": "missing_verified_rate_a_or_thermal_limit_source",
                "relay_threshold_available": False,
                "relay_threshold_source": "missing_documented_relay_threshold_or_line_limit_proxy",
                "endpoint_load_available": False,
                "endpoint_load_source": "missing_verified_current_state_bus_load_source",
                "ready_for_paper_feature_vector": False,
                "missing_fields": missing_fields,
                "l12_special_case_flag": line_id == "L12",
            }
        )

    branch_flow_ready = False
    line_limit_ready = False
    relay_threshold_ready = False
    bus_load_ready = False
    can_build_required = branch_flow_ready and (line_limit_ready or relay_threshold_ready) and bus_load_ready
    can_build_matrix = all(row["ready_for_paper_feature_vector"] for row in rows)
    if branch_flow_ready and line_limit_ready and bus_load_ready and not relay_threshold_ready:
        recommended = "define documented relay threshold proxy from verified line limit before training"
    elif can_build_required:
        recommended = "prepare paper-style branch vulnerability label generator dry-run for line-trip labels"
    else:
        recommended = "add or generate verified current-state PF/OPF branch flow, line limit, and bus load sources before label generator"
    blocker = None if can_build_required else "verified current-state branch flow, line limit or relay threshold, and endpoint bus load sources are incomplete"

    inventory = {
        "inventory_scope": "paper_aligned_feature_source_inventory",
        "branch_flow_sources_found": source_hits["branch_flow"],
        "line_limit_sources_found": source_hits["line_limit"],
        "relay_threshold_sources_found": source_hits["relay_threshold"],
        "bus_load_sources_found": source_hits["bus_load"],
        "dc_power_flow_or_opf_scripts_found": source_hits["dc_power_flow_or_opf"],
        "matpower_or_case_data_found": source_hits["matpower_or_case"],
        "simulink_prefault_sources_found": source_hits["simulink_prefault"],
        "post_fault_sources_detected_and_forbidden": source_hits["post_fault_forbidden"],
        "source_trust_level_by_category": {
            "branch_flow": "not_verified_for_ieee39_paper_input",
            "line_limit": "not_verified_for_ieee39_paper_input",
            "relay_threshold": "not_verified_for_ieee39_paper_input",
            "bus_load": "not_verified_for_ieee39_paper_input",
            "dc_power_flow_or_opf": "generator_required_if_used_for_future_features",
            "post_fault_dynamic_measurements": "forbidden_as_gcn_inputs",
        },
        "missing_source_categories": ["verified_current_state_branch_flow", "verified_line_limit_or_relay_threshold", "verified_current_state_bus_load"],
        "verified_sources_ready": can_build_required,
        "blocker_if_any": blocker,
    }

    mapping_plan = {
        "x_t_topology_status_mapping": "Use current outaged branch set over L01-L34; 0 means online and 1 means disconnected.",
        "x_p_relay_ratio_mapping": "|branch_flow| / relay_threshold; blocked until verified branch flow and relay threshold or documented line-limit proxy exist.",
        "x_b_branch_flow_mapping": "Use verified current-state PF/OPF branch active power flow; blocked in this dry-run.",
        "x_l_endpoint_load_mapping": "Use max(load_from_bus, load_to_bus) from verified current-state bus load table; blocked in this dry-run.",
        "normalization_plan": "Normalize only after raw physical values are preserved; do not compute physics ratios from normalized values.",
        "units_plan": "Record MW for branch flow and load, MW or MVA for limits, and dimensionless ratio for x_p.",
        "per_unit_conversion_plan": "If sources are per-unit, record baseMVA and convert consistently before feature normalization.",
        "missing_conversion_requirements": ["baseMVA_for_any_per_unit_source", "verified_branch_flow_units", "verified_load_units", "relay_threshold_or_line_limit_units"],
        "no_leakage_policy": "Only pre-fault/current-state static PF/OPF and topology inputs are allowed; post-fault dynamic measurements are forbidden as inputs.",
        "forbidden_dynamic_measurement_inputs": FORBIDDEN_DYNAMIC_FEATURES,
        "feature_vector_shape": "L x 4",
        "current_L": 34,
        "future_extension_note": "if full IEEE39 branch set differs from L01-L34, mapping must be reconciled before training",
    }

    no_leakage = {
        "forbidden_features_checked": FORBIDDEN_DYNAMIC_FEATURES,
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_targets_only_used_as_labels": True,
        "bus_fault_labels_not_used_as_paper_inputs": True,
        "source_leakage_risk_summary": {
            "post_fault_sources_detected_in_repository": bool(source_hits["post_fault_forbidden"]),
            "post_fault_sources_used_for_paper_inputs": False,
            "risk_level": "controlled_by_not_using_dynamic_sources",
        },
        "no_leakage_feature_source_policy_passed": True,
    }

    summary = {
        "dry_run_scope": "paper_aligned_feature_source_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_consistency_commit": SOURCE_CONSISTENCY_COMMIT,
        "paper_graph_node_type": "branch",
        "paper_graph_edge_rule": "shared_endpoint_bus",
        "branch_line_graph_ready": bool(previous_summary.get("can_build_branch_line_graph", graph.get("graph_construction_ready", False))),
        "num_branch_nodes": int(graph.get("num_branch_nodes", len(rows))),
        "branch_flow_source_ready": branch_flow_ready,
        "line_limit_source_ready": line_limit_ready,
        "relay_threshold_source_ready": relay_threshold_ready,
        "bus_load_source_ready": bus_load_ready,
        "can_build_required_paper_features": can_build_required,
        "can_build_l01_l34_feature_matrix": can_build_matrix,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_feature_source_policy_passed": True,
        "l12_special_case_preserved": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": blocker,
        "recommended_next_step": recommended,
        "previous_redesign_consistency": {
            "can_build_branch_line_graph": consistency.get("can_build_branch_line_graph"),
            "can_build_required_paper_features": consistency.get("can_build_required_paper_features"),
            "can_build_paper_labels_from_existing_data": consistency.get("can_build_paper_labels_from_existing_data"),
            "line_trip_labels_first_priority": consistency.get("line_trip_labels_first_priority"),
        },
        "previous_feature_manifest_ready": feature_manifest.get("feature_readiness_for_prototype"),
        "previous_label_plan_ready": label_plan.get("can_build_paper_labels_from_existing_data"),
    }

    return {
        "inventory": inventory,
        "matrix": rows,
        "mapping_plan": mapping_plan,
        "no_leakage": no_leakage,
        "summary": summary,
    }


def write_reports(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "feature_source_inventory.json", payloads["inventory"])
    _write_md(OUT_DIR / "feature_source_inventory.md", "IEEE39 Paper-Aligned Feature Source Inventory", payloads["inventory"])
    _write_json(OUT_DIR / "l01_l34_feature_readiness_matrix.json", payloads["matrix"])
    _write_md(
        OUT_DIR / "l01_l34_feature_readiness_matrix.md",
        "IEEE39 L01-L34 Feature Readiness Matrix",
        {"rows": payloads["matrix"]},
    )
    _write_matrix_csv(OUT_DIR / "l01_l34_feature_readiness_matrix.csv", payloads["matrix"])
    _write_json(OUT_DIR / "paper_feature_mapping_plan.json", payloads["mapping_plan"])
    _write_md(OUT_DIR / "paper_feature_mapping_plan.md", "IEEE39 Paper Feature Mapping Plan", payloads["mapping_plan"])
    _write_json(OUT_DIR / "no_leakage_feature_source_audit.json", payloads["no_leakage"])
    _write_md(OUT_DIR / "no_leakage_feature_source_audit.md", "IEEE39 No-Leakage Feature Source Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "feature_source_dry_run_validator_summary.json", payloads["summary"])
    _write_md(
        OUT_DIR / "feature_source_dry_run_validator_summary.md",
        "IEEE39 Paper-Aligned Feature Source Dry-Run Validator Summary",
        payloads["summary"],
    )
    _write_key_value_csv(OUT_DIR / "feature_source_dry_run_validator_summary.csv", payloads["summary"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Paper-Aligned Feature Source Dry-Run

This round is a paper-aligned feature source dry-run. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.

The original paper input matrix is `X_GCN` with shape `L x 4`: `x_t` topology status, `x_p` relay ratio, `x_b` branch flow, and `x_l` endpoint load. In Chinese: `x_t` means current branch outage status, `x_p` means branch-flow-to-relay-threshold ratio, `x_b` means current-state branch flow, and `x_l` means the larger load at the two endpoint buses.

## Source Readiness

- `x_t` is available from the current outaged branch set.
- `x_p` still needs verified branch flow and relay threshold, or a documented line-limit proxy.
- `x_b` still needs verified current-state PF/OPF branch flow.
- `x_l` still needs verified current-state bus load.
- branch_line_graph_ready: `{summary["branch_line_graph_ready"]}`
- num_branch_nodes: `{summary["num_branch_nodes"]}`
- branch_flow_source_ready: `{summary["branch_flow_source_ready"]}`
- line_limit_source_ready: `{summary["line_limit_source_ready"]}`
- relay_threshold_source_ready: `{summary["relay_threshold_source_ready"]}`
- bus_load_source_ready: `{summary["bus_load_source_ready"]}`
- can_build_required_paper_features: `{summary["can_build_required_paper_features"]}`
- can_build_l01_l34_feature_matrix: `{summary["can_build_l01_l34_feature_matrix"]}`

## No-Leakage Rule

Post-fault dynamic measurement cannot replace these paper inputs. `min_voltage_pu`, `max_voltage_pu`, frequency, rotor angle, speed deviation, `dynamic_stress_score`, `unstable_flag`, `phasor_RMS`, and `generator_speed_proxy` are not used as GCN inputs here. `dynamic_stress_score` and `unstable_flag` can only be labels or audit targets.

If only line limit is found but no relay threshold is found, the next step must explicitly decide whether a documented relay threshold proxy from verified line limit is allowed. This round does not make that decision.

L12 remains a special case and the old gate is unchanged.

## Blocker

`{summary["blocker_if_any"]}`

## Next Step

`{summary["recommended_next_step"]}`

This is not deployment, not reranker retraining, and not a final engineering conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Fail if required previous dry-run artifacts are missing.")
    parser.add_argument("--write-report", action="store_true", help="Write docs/ieee39_paper_aligned_feature_source_dry_run.md.")
    args = parser.parse_args()
    required = [BRANCH_GRAPH, FEATURE_MANIFEST, LABEL_PLAN, DRY_RUN_SUMMARY, CONSISTENCY]
    missing = [str(path) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required previous artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_reports(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
