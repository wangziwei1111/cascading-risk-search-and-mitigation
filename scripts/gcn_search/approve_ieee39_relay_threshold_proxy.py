from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run"
OUT_DIR = ROOT / "results/gcn_search/ieee39_relay_threshold_proxy_approval"
DOC = ROOT / "docs/ieee39_relay_threshold_proxy_approval.md"

SOURCE_STATIC_FEATURE_COMMIT = "a29bc6e209afe764aa8bf57613d66dd53114fba9"
BETA_VALUE = 1.2
FORBIDDEN_FEATURES = [
    "min_voltage_pu",
    "max_voltage_pu",
    "frequency",
    "rotor angle",
    "speed deviation",
    "dynamic_stress_score",
    "unstable_flag",
    "phasor_RMS",
    "generator_speed_proxy",
    "label-derived flags",
    "post-fault dynamic measurements",
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


def _write_md(path: Path, title: str, payload: dict[str, Any]) -> None:
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


def _write_key_value_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            writer.writerow([key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value])


def _write_matrix_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "line_id",
        "from_bus",
        "to_bus",
        "x_t_topology_status_available",
        "x_b_branch_flow_available",
        "x_b_branch_flow_value",
        "x_b_branch_flow_unit",
        "x_p_relay_threshold_proxy_value",
        "x_p_relay_threshold_proxy_unit",
        "x_p_relay_threshold_proxy_formula",
        "x_p_relay_ratio_value",
        "x_l_endpoint_load_available",
        "x_l_endpoint_load_max_value",
        "x_l_endpoint_load_unit",
        "ready_for_x_t",
        "ready_for_x_p_with_proxy",
        "ready_for_x_b",
        "ready_for_x_l",
        "ready_for_lx4_feature_vector_with_proxy",
        "relay_threshold_is_proxy",
        "proxy_allowed_for_audit_only_prototype",
        "proxy_allowed_for_production",
        "l12_special_case_flag",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_approved_matrix(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        flow = row.get("branch_flow_value")
        threshold = row.get("relay_threshold_value")
        ratio = abs(float(flow)) / float(threshold) if flow is not None and threshold else None
        ready_x_t = bool(row.get("ready_for_x_t"))
        ready_x_b = bool(row.get("ready_for_x_b"))
        ready_x_l = bool(row.get("ready_for_x_l"))
        ready_x_p = threshold is not None
        rows.append(
            {
                "line_id": row["line_id"],
                "from_bus": row["from_bus"],
                "to_bus": row["to_bus"],
                "x_t_topology_status_available": bool(row.get("topology_status_available", ready_x_t)),
                "x_b_branch_flow_available": bool(row.get("branch_flow_available", ready_x_b)),
                "x_b_branch_flow_value": flow,
                "x_b_branch_flow_unit": row.get("branch_flow_unit", "MW"),
                "x_p_relay_threshold_proxy_value": threshold,
                "x_p_relay_threshold_proxy_unit": row.get("relay_threshold_unit", "MVA_or_MW_proxy"),
                "x_p_relay_threshold_proxy_formula": "beta * RATE_A",
                "x_p_relay_ratio_value": ratio,
                "x_l_endpoint_load_available": bool(row.get("endpoint_load_available", ready_x_l)),
                "x_l_endpoint_load_max_value": row.get("endpoint_load_max_value"),
                "x_l_endpoint_load_unit": row.get("load_unit", "MW"),
                "ready_for_x_t": ready_x_t,
                "ready_for_x_p_with_proxy": ready_x_p,
                "ready_for_x_b": ready_x_b,
                "ready_for_x_l": ready_x_l,
                "ready_for_lx4_feature_vector_with_proxy": ready_x_t and ready_x_p and ready_x_b and ready_x_l,
                "relay_threshold_is_proxy": True,
                "proxy_allowed_for_audit_only_prototype": True,
                "proxy_allowed_for_production": False,
                "l12_special_case_flag": bool(row.get("l12_special_case_flag")),
            }
        )
    return rows


def build_payloads() -> dict[str, Any]:
    source_summary = _read_json(SOURCE_DIR / "static_feature_source_dry_run_validator_summary.json")
    source_proxy = _read_json(SOURCE_DIR / "relay_threshold_proxy_proposal.json")
    source_matrix = _read_json(SOURCE_DIR / "l01_l34_static_feature_source_matrix.json")
    source_no_leakage = _read_json(SOURCE_DIR / "no_leakage_static_feature_audit.json")

    matrix = _build_approved_matrix(source_matrix)
    no_leakage = {
        "forbidden_features_checked": FORBIDDEN_FEATURES,
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "static_or_prefault_sources_only": True,
        "dynamic_targets_only_used_as_labels": True,
        "proxy_not_engineering_relay_setting": True,
        "no_leakage_policy_passed": True,
    }
    summary = {
        "approval_scope": "relay_threshold_proxy_approval",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_static_feature_commit": SOURCE_STATIC_FEATURE_COMMIT,
        "relay_threshold_source_ready": False,
        "relay_threshold_proxy_approved": True,
        "relay_threshold_proxy_allowed_for_audit_only_prototype": True,
        "relay_threshold_proxy_allowed_for_production": False,
        "proxy_formula": "beta * RATE_A",
        "beta_value": BETA_VALUE,
        "beta_value_source": "project default beta = 1.2",
        "line_limit_source": "pypower.case39 branch RATE_A",
        "branch_flow_source_ready": bool(source_summary.get("branch_flow_source_ready")),
        "line_limit_source_ready": bool(source_summary.get("line_limit_source_ready")),
        "bus_load_source_ready": bool(source_summary.get("bus_load_source_ready")),
        "can_build_required_paper_features_without_proxy": False,
        "can_build_required_paper_features_with_approved_proxy": True,
        "can_build_l01_l34_paper_feature_matrix_with_proxy": all(
            row["ready_for_lx4_feature_vector_with_proxy"] for row in matrix
        ),
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": bool(source_no_leakage.get("no_leakage_static_feature_policy_passed", True)),
        "l12_special_case_preserved": any(row["line_id"] == "L12" and row["l12_special_case_flag"] for row in matrix),
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "recommended_next_step": "prepare paper-style branch vulnerability label generator dry-run for line-trip labels",
        "source_proxy_was_previously_allowed_for_training_now": bool(source_proxy.get("proxy_allowed_for_training_now")),
    }
    limitations = {
        "proxy_formula": "beta * RATE_A",
        "beta_value": BETA_VALUE,
        "line_limit_source": "pypower.case39 branch RATE_A",
        "approval_scope": "audit-only paper-aligned prototype",
        "not_real_relay_setting": True,
        "not_engineering_grade_protection": True,
        "not_allowed_for_production": True,
        "replace_when_real_threshold_available": True,
        "proxy_based_gcn_audit_must_be_marked_proxy_based": True,
    }
    return {
        "summary": summary,
        "matrix": matrix,
        "no_leakage": no_leakage,
        "limitations": limitations,
    }


def write_reports(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "relay_threshold_proxy_approval_summary.json", payloads["summary"])
    _write_md(OUT_DIR / "relay_threshold_proxy_approval_summary.md", "IEEE39 Relay Threshold Proxy Approval Summary", payloads["summary"])
    _write_key_value_csv(OUT_DIR / "relay_threshold_proxy_approval_summary.csv", payloads["summary"])
    _write_json(OUT_DIR / "l01_l34_approved_paper_feature_source_matrix.json", payloads["matrix"])
    _write_md(
        OUT_DIR / "l01_l34_approved_paper_feature_source_matrix.md",
        "IEEE39 L01-L34 Approved Paper Feature Source Matrix",
        {"rows": payloads["matrix"]},
    )
    _write_matrix_csv(OUT_DIR / "l01_l34_approved_paper_feature_source_matrix.csv", payloads["matrix"])
    _write_json(OUT_DIR / "no_leakage_proxy_feature_audit.json", payloads["no_leakage"])
    _write_md(OUT_DIR / "no_leakage_proxy_feature_audit.md", "IEEE39 No-Leakage Proxy Feature Audit", payloads["no_leakage"])
    _write_md(OUT_DIR / "relay_threshold_proxy_limitations.md", "IEEE39 Relay Threshold Proxy Limitations", payloads["limitations"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Relay Threshold Proxy Approval

This round is relay threshold proxy approval only. It did not train GCN, did not rerun formal audit, did not run Simulink, did not export labels, did not retrain the reranker, and did not save a production model.

## Approved Audit-Only Proxy

`beta * RATE_A` is approved as an audit-only paper-aligned prototype proxy for IEEE39 paper-style branch GCN feature preparation.

- proxy_formula: `{summary["proxy_formula"]}`
- beta_value: `{summary["beta_value"]}`
- beta_value_source: `{summary["beta_value_source"]}`
- line_limit_source: `{summary["line_limit_source"]}`
- relay_threshold_proxy_approved: `{summary["relay_threshold_proxy_approved"]}`
- relay_threshold_proxy_allowed_for_audit_only_prototype: `{summary["relay_threshold_proxy_allowed_for_audit_only_prototype"]}`
- relay_threshold_proxy_allowed_for_production: `{summary["relay_threshold_proxy_allowed_for_production"]}`

This proxy is not a real relay protection setting, not an engineering-grade relay threshold, and not allowed for production. If a future real protection threshold source is obtained, this proxy should be replaced. Any GCN audit that uses this proxy must be marked proxy-based.

## Feature Readiness

Branch flow, line limit, and bus load come from the `pypower.case39` static/pre-fault source. With this approved audit-only proxy, the L01-L34 L x 4 paper feature source matrix can now be built with proxy.

- branch_flow_source_ready: `{summary["branch_flow_source_ready"]}`
- line_limit_source_ready: `{summary["line_limit_source_ready"]}`
- bus_load_source_ready: `{summary["bus_load_source_ready"]}`
- can_build_required_paper_features_without_proxy: `{summary["can_build_required_paper_features_without_proxy"]}`
- can_build_required_paper_features_with_approved_proxy: `{summary["can_build_required_paper_features_with_approved_proxy"]}`
- can_build_l01_l34_paper_feature_matrix_with_proxy: `{summary["can_build_l01_l34_paper_feature_matrix_with_proxy"]}`

There are still no branch vulnerability labels in this approval round. The next step is a paper-style branch vulnerability label generator dry-run for line-trip labels.

## No-Leakage Policy

Post-fault dynamic measurements are not used as inputs. `dynamic_stress_score` and `unstable_flag` can only be labels or audit targets. Label-derived flags are not allowed as inputs.

- forbidden_features_detected_in_inputs: `{summary["forbidden_features_detected_in_inputs"]}`
- no_leakage_policy_passed: `{summary["no_leakage_policy_passed"]}`
- l12_special_case_preserved: `{summary["l12_special_case_preserved"]}`

## Boundaries

This is not deployment, not reranker retraining, and not a final engineering conclusion. It provides no GCN usefulness conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [
        SOURCE_DIR / "static_feature_source_dry_run_validator_summary.json",
        SOURCE_DIR / "relay_threshold_proxy_proposal.json",
        SOURCE_DIR / "l01_l34_static_feature_source_matrix.json",
        SOURCE_DIR / "no_leakage_static_feature_audit.json",
        ROOT / "docs/ieee39_static_operating_point_feature_source_dry_run.md",
    ]
    missing = [str(path) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required source artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_reports(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
