from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run"
LINE_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
LINE_MAP_SUMMARY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full_summary.json"
AUDIT_SUMMARY = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.json"
EVIDENCE_SUMMARY = ROOT / "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/gcn_audit_evidence_diagnosis_summary.json"
GRAPH_DIAGNOSIS = ROOT / "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis/graph_construction_diagnosis.json"
LABEL_SCHEMA = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_schema.json"
LABEL_PREVIEW = ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_preview.csv"
ALL_BUS_LABELS = ROOT / (
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "batch_bus_fault_expansion_all_remaining/candidate_label_export/"
    "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
)

SOURCE_EVIDENCE_DIAGNOSIS_COMMIT = "945f9028235a3b8d7ec6011bf7d9314150198200"


def _read_json(path: Path) -> dict[str, Any]:
    if not _exists(path):
        return {}
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not _exists(path):
        return []
    with open(_long(path), newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _write_json(name: str, payload: dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_md(name: str, title: str, payload: dict[str, Any]) -> None:
    lines = [f"# {title}", ""]
    for key, value in payload.items():
        lines.extend(_md_item(key, value, 0))
    (OUT_DIR / f"{name}.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _md_item(key: str, value: Any, indent: int) -> list[str]:
    pad = "  " * indent
    if isinstance(value, dict):
        lines = [f"{pad}- `{key}`:"]
        for sub_key, sub_value in value.items():
            lines.extend(_md_item(sub_key, sub_value, indent + 1))
        return lines
    if isinstance(value, list):
        lines = [f"{pad}- `{key}`:"]
        if not value:
            lines.append(f"{pad}  - []")
            return lines
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}  -")
                if isinstance(item, dict):
                    for sub_key, sub_value in item.items():
                        lines.extend(_md_item(sub_key, sub_value, indent + 2))
                else:
                    for sub_item in item:
                        lines.append(f"{pad}    - {sub_item}")
            else:
                lines.append(f"{pad}  - {item}")
        return lines
    return [f"{pad}- `{key}`: {value}"]


def _write_csv(name: str, payload: dict[str, Any]) -> None:
    with (OUT_DIR / f"{name}.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "value"])
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                writer.writerow([key, json.dumps(value, ensure_ascii=False)])
            else:
                writer.writerow([key, value])


def _line_number(line_id: str) -> int:
    digits = "".join(ch for ch in str(line_id) if ch.isdigit())
    return int(digits) if digits else 0


def _collect_bus_ids(line_rows: list[dict[str, str]], label_rows: list[dict[str, str]]) -> list[str]:
    buses = set()
    for row in line_rows:
        buses.add(str(row.get("from_bus", "")).strip())
        buses.add(str(row.get("to_bus", "")).strip())
    for row in label_rows:
        for key in ["target_bus", "target_bus_or_component", "fault_injection_bus_or_line"]:
            value = str(row.get(key, "")).strip()
            if value.startswith("B") and value[1:].isdigit():
                buses.add(value)
    buses.discard("")
    return sorted(buses, key=lambda item: int(item[1:]) if item[1:].isdigit() else 999)


def _build_graph(line_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[list[str]], float]:
    branches = [
        {
            "line_id": str(row.get("line_id", "")).strip(),
            "from_bus": str(row.get("from_bus", "")).strip(),
            "to_bus": str(row.get("to_bus", "")).strip(),
            "line_block_path": str(row.get("line_block_path", "")).strip(),
            "mapping_status": str(row.get("mapping_status", "")).strip(),
        }
        for row in line_rows
        if str(row.get("line_id", "")).strip() and str(row.get("from_bus", "")).strip() and str(row.get("to_bus", "")).strip()
    ]
    branches = sorted(branches, key=lambda row: _line_number(row["line_id"]))
    edges: list[list[str]] = []
    for idx, left in enumerate(branches):
        left_buses = {left["from_bus"], left["to_bus"]}
        for right in branches[idx + 1 :]:
            if left_buses & {right["from_bus"], right["to_bus"]}:
                edges.append([left["line_id"], right["line_id"]])
    node_count = len(branches)
    possible = node_count * (node_count - 1) / 2
    density = float(len(edges) / possible) if possible else 0.0
    return branches, edges, density


def build_payloads() -> dict[str, dict[str, Any]]:
    line_rows = _read_csv(LINE_MAP)
    audit_summary = _read_json(AUDIT_SUMMARY)
    evidence_summary = _read_json(EVIDENCE_SUMMARY)
    graph_diagnosis = _read_json(GRAPH_DIAGNOSIS)
    line_summary = _read_json(LINE_MAP_SUMMARY)
    label_rows = _read_csv(LABEL_PREVIEW) + _read_csv(ALL_BUS_LABELS)
    branches, graph_edges, adjacency_density = _build_graph(line_rows)
    bus_ids = _collect_bus_ids(line_rows, label_rows)
    expected_line_ids = [f"L{idx:02d}" for idx in range(1, 35)]
    detected_line_ids = [branch["line_id"] for branch in branches]
    missing_line_ids = [line_id for line_id in expected_line_ids if line_id not in detected_line_ids]
    l12 = next((branch for branch in branches if branch["line_id"] == "L12"), None)
    can_build_branch_line_graph = bool(branches) and not missing_line_ids
    missing_required_paper_features = [
        "relay_ratio_feature: verified current-state branch flow and relay threshold source",
        "branch_flow_feature: verified OPF/PF/current-state branch flow source",
        "endpoint_load_feature: verified current-state bus load source",
    ]
    available_required_paper_features = ["topology_status_feature from current outaged branch set"]
    can_build_required_paper_features = False
    can_build_paper_labels_from_existing_data = False
    no_leakage_feature_policy_passed = True
    blocker_parts = []
    if not can_build_branch_line_graph:
        blocker_parts.append("verified IEEE39 branch-to-bus topology mapping is incomplete")
    if not can_build_required_paper_features:
        blocker_parts.append("verified pre-fault/current-state branch flow, line limit, and bus load sources are incomplete")
    if not can_build_paper_labels_from_existing_data:
        blocker_parts.append("paper-style branch vulnerability label generator is not available yet")
    blocker_if_any = "; ".join(blocker_parts) if blocker_parts else None
    recommended_next_step = (
        "implement audit-only paper-aligned branch-as-node GCN prototype in a separate round"
        if can_build_branch_line_graph
        and no_leakage_feature_policy_passed
        and can_build_required_paper_features
        and can_build_paper_labels_from_existing_data
        else "add verified pre-fault/current-state branch flow, line limit, and bus load sources first"
        if not can_build_required_paper_features
        else "build paper-style branch vulnerability label generator before training"
    )

    method = {
        "paper_method": "branch_as_node_gcn_for_cascading_search",
        "paper_graph_node": "branch_or_line",
        "paper_graph_edge_rule": "two_branch_nodes_connected_if_original_branches_share_a_bus",
        "paper_output": "branch_vulnerability_vector",
        "paper_target_semantics": "whether disconnecting branch k from current state leads to load shedding",
        "paper_inputs": ["topology_status", "relay_ratio", "branch_flow", "endpoint_load"],
        "paper_online_search": "gcn_first_then_physical_rule_lodf",
        "paper_lrp_note": "LRP explains contribution from topology, protection, branch flow, and load input groups.",
        "current_repo_previous_graph": graph_diagnosis.get("sample_granularity", "candidate_similarity_graph"),
        "current_repo_previous_issue": "candidate rows used as graph nodes",
        "redesign_required": True,
    }
    inventory = {
        "topology_sources_found": [str(LINE_MAP.relative_to(ROOT)), str(LINE_MAP_SUMMARY.relative_to(ROOT))],
        "branch_endpoint_mapping_source": str(LINE_MAP.relative_to(ROOT)) if LINE_MAP.exists() else None,
        "bus_list_source": "branch endpoints plus existing dynamic label candidate bus fields",
        "line_id_mapping_source": str(LINE_MAP.relative_to(ROOT)) if LINE_MAP.exists() else None,
        "detected_num_buses": len(bus_ids),
        "detected_bus_ids": bus_ids,
        "branch_endpoint_bus_ids": sorted({bus for branch in branches for bus in [branch["from_bus"], branch["to_bus"]]}, key=lambda item: int(item[1:]) if item[1:].isdigit() else 999),
        "detected_num_branches": len(branches),
        "detected_line_ids": detected_line_ids,
        "missing_line_ids": missing_line_ids,
        "l12_mapping_status": {
            "line_id": "L12",
            "mapping_found": l12 is not None,
            "from_bus": l12.get("from_bus") if l12 else None,
            "to_bus": l12.get("to_bus") if l12 else None,
            "status_note": "L12 remains the previously documented islanding/timeout special case; this dry-run does not change old formal gates.",
        },
        "transformer_or_special_branch_status": "not fully verified; wrapper line map currently covers 34 line-like Grid blocks and does not claim complete transformer modeling",
        "old_formal_gate_35_33_33_unchanged": True,
        "topology_source_trust_level": "medium_wrapper_inventory_verified_not_engineering_final",
        "can_build_branch_line_graph": can_build_branch_line_graph,
        "blocker_if_any": None if can_build_branch_line_graph else "add verified IEEE39 branch-to-bus topology mapping first",
        "line_map_summary": line_summary,
    }
    graph = {
        "graph_type": "paper_aligned_branch_as_node_line_graph",
        "graph_node_type": "branch",
        "graph_edge_rule": "shared_endpoint_bus",
        "num_branch_nodes": len(branches),
        "branch_node_ids": detected_line_ids,
        "branch_endpoint_pairs": {branch["line_id"]: [branch["from_bus"], branch["to_bus"]] for branch in branches},
        "graph_edges": graph_edges,
        "edge_index_preview": graph_edges[:20],
        "num_graph_edges": len(graph_edges),
        "adjacency_density": adjacency_density,
        "graph_is_candidate_similarity_graph": False,
        "graph_uses_physical_branch_connectivity": can_build_branch_line_graph,
        "graph_construction_ready": can_build_branch_line_graph,
        "blocker_if_any": None if can_build_branch_line_graph else "verified branch endpoint pairs are incomplete",
    }
    features = {
        "topology_status_feature": {
            "paper_symbol": "x_t",
            "chinese_meaning": "支路当前是否已经断开；0 表示在线运行，1 表示已经断开",
            "repo_mapping": "encode current cascading state's outaged branch set over L branch nodes",
            "available": True,
            "no_leakage": True,
        },
        "relay_ratio_feature": {
            "paper_symbol": "x_p",
            "chinese_meaning": "保护继电器相关比例，即支路潮流除以继电器动作阈值",
            "repo_mapping": "|branch_flow| / relay_threshold",
            "available": False,
            "missing_reason": "missing_static_or_prefault_flow_source and verified relay threshold source",
            "post_fault_dynamic_measurements_forbidden_as_substitute": True,
        },
        "branch_flow_feature": {
            "paper_symbol": "x_b",
            "chinese_meaning": "当前状态下支路潮流",
            "repo_mapping": "current-state OPF/PF branch flow",
            "available": False,
            "missing_reason": "missing OPF/PF/static current-state branch flow source for IEEE39 dry-run",
        },
        "endpoint_load_feature": {
            "paper_symbol": "x_l",
            "chinese_meaning": "支路两端母线负荷中较大的一个",
            "repo_mapping": "max(load_from_bus, load_to_bus)",
            "available": False,
            "missing_reason": "missing verified current-state bus load source for IEEE39 dry-run",
        },
        "forbidden_features_detected_in_inputs": [],
        "dynamic_measurements_forbidden": True,
        "dynamic_targets_only_used_as_labels": True,
        "no_leakage_feature_policy_passed": no_leakage_feature_policy_passed,
        "missing_required_paper_features": missing_required_paper_features,
        "available_required_paper_features": available_required_paper_features,
        "feature_readiness_for_prototype": can_build_required_paper_features,
    }
    labels = {
        "paper_label_type": "branch_vulnerability_binary_vector",
        "label_shape": "num_states x num_branches",
        "y_gcn_k_semantics": "whether disconnecting branch k from current state leads to load shedding / unacceptable dynamic risk",
        "our_current_labels": "scenario-level dynamic_stress_score / unstable_flag",
        "gap_between_paper_labels_and_current_labels": "current IEEE39 labels are scenario-level outcomes, not a per-state vector over every candidate branch k",
        "can_build_paper_labels_from_existing_data": can_build_paper_labels_from_existing_data,
        "missing_label_generation_requirements": [
            "state-wise branch candidate loop over L01-L34",
            "paper-style label generator that applies next branch outage k from current state",
            "documented proxy relation between OPA load shedding and Simulink dynamic instability",
        ],
        "possible_adaptation": [
            "line-trip labels can be used first for branch outage vulnerability",
            "bus-fault labels are not directly paper-aligned and should be separate extension",
            "dynamic_stress_score can be mapped to binary unstable label only as output target, not input",
            "load shedding in OPA is not identical to Simulink dynamic instability, so proxy semantics must be documented",
        ],
        "bus_fault_labels_directly_paper_aligned": False,
        "line_trip_labels_first_priority": True,
    }
    policy = {
        "paper_search_policy": "GCN predicted vulnerable branches first, then physical LODF priority",
        "proposed_repo_policy": {
            "y_gcn_branch_vulnerability_score": "paper-aligned branch GCN output over L branch nodes",
            "y_p_lodf_physics_priority": "physical LODF/security priority used as fallback and tie-breaker",
            "combined_search_or_reranking": "search GCN-positive/high-score branches first, then supplement with y_P ordering",
            "top_k_physical_simulation_validation": "validate selected paths with existing physical/dynamic pipeline only after audit evidence improves",
        },
        "no_reranker_retrain_now": True,
        "no_deployment_now": True,
        "how_this_connects_to_existing_pipeline": [
            "physics-enhanced GCN initial screening",
            "online state update",
            "path-level reranking",
            "Top-K Simulink validation",
        ],
    }
    summary = {
        "dry_run_scope": "paper_aligned_branch_gcn_redesign_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_evidence_diagnosis_commit": SOURCE_EVIDENCE_DIAGNOSIS_COMMIT,
        "source_audit_gcn_dependency_status": audit_summary.get("gcn_dependency_status"),
        "paper_graph_node_type": "branch",
        "paper_graph_edge_rule": "shared_endpoint_bus",
        "previous_repo_graph_type": "candidate_similarity_graph",
        "previous_candidate_as_node_design_deprecated": True,
        "proposed_graph_type": "branch_as_node_physical_line_graph",
        "can_build_branch_line_graph": can_build_branch_line_graph,
        "no_leakage_feature_policy_passed": no_leakage_feature_policy_passed,
        "can_build_required_paper_features": can_build_required_paper_features,
        "can_build_paper_labels_from_existing_data": can_build_paper_labels_from_existing_data,
        "bus_fault_labels_directly_paper_aligned": False,
        "line_trip_labels_first_priority": True,
        "forbidden_features_detected_in_inputs": [],
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": blocker_if_any,
        "recommended_next_step": recommended_next_step,
        "detected_num_branch_nodes": len(branches),
        "detected_num_buses": len(bus_ids),
        "l12_mapping_status": inventory["l12_mapping_status"],
        "previous_audit_conclusion": evidence_summary.get("gcn_vs_baseline_gap", {}).get("audit_level_conclusion"),
    }
    return {
        "paper_method_mapping_summary": method,
        "ieee39_branch_topology_source_inventory": inventory,
        "ieee39_branch_as_node_graph_manifest": graph,
        "paper_aligned_feature_manifest": features,
        "paper_aligned_label_plan": labels,
        "hybrid_search_policy_plan": policy,
        "paper_aligned_branch_gcn_dry_run_validator_summary": summary,
    }


def write_reports(payloads: dict[str, dict[str, Any]]) -> None:
    titles = {
        "paper_method_mapping_summary": "Paper Method Mapping Summary",
        "ieee39_branch_topology_source_inventory": "IEEE39 Branch Topology Source Inventory",
        "ieee39_branch_as_node_graph_manifest": "IEEE39 Branch-As-Node Graph Manifest",
        "paper_aligned_feature_manifest": "Paper-Aligned Feature Manifest",
        "paper_aligned_label_plan": "Paper-Aligned Label Plan",
        "hybrid_search_policy_plan": "Hybrid Search Policy Plan",
        "paper_aligned_branch_gcn_dry_run_validator_summary": "Paper-Aligned Branch GCN Dry-Run Validator Summary",
    }
    for name, payload in payloads.items():
        _write_json(name, payload)
        _write_md(name, titles[name], payload)
    _write_csv("paper_aligned_branch_gcn_dry_run_validator_summary", payloads["paper_aligned_branch_gcn_dry_run_validator_summary"])
    _write_doc(payloads)


def _write_doc(payloads: dict[str, dict[str, Any]]) -> None:
    summary = payloads["paper_aligned_branch_gcn_dry_run_validator_summary"]
    graph = payloads["ieee39_branch_as_node_graph_manifest"]
    features = payloads["paper_aligned_feature_manifest"]
    labels = payloads["paper_aligned_label_plan"]
    doc = ROOT / "docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md"
    lines = [
        "# IEEE39 Paper-Aligned Branch GCN Redesign Dry-Run",
        "",
        "This round is a paper-aligned branch GCN redesign dry-run. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.",
        "",
        "The paper method is not a candidate-row graph. It maps each power-system branch or line to one GCN node, and two branch nodes are connected when the original branches share one bus.",
        "",
        "The paper input is a four-column branch feature matrix: topology status, relay ratio, branch flow, and endpoint load. The paper output is a branch vulnerability vector. The kth value means whether disconnecting branch k from the current state causes load shedding.",
        "",
        "Our previous IEEE39 audit used a candidate similarity graph, where candidate rows were graph nodes. That design is deprecated for the next paper-aligned prototype because it is not the physical branch-as-node graph described by the paper.",
        "",
        "Current scenario-level bus-fault labels are not directly equivalent to paper branch vulnerability labels. Line-trip labels should be the first priority for a paper-aligned prototype; bus-fault labels are a later extension and should not be forced into the original branch vulnerability structure.",
        "",
        "Post-fault dynamic measurements cannot be used as GCN inputs. Dynamic_stress_score and unstable_flag can only be labels or audit targets, not inputs.",
        "",
        "Phasor_RMS is not EMT. Generator_speed_proxy is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.",
        "",
        "## Dry-Run Status",
        "",
        f"- dry_run_scope: {summary['dry_run_scope']}",
        f"- paper_graph_node_type: {summary['paper_graph_node_type']}",
        f"- paper_graph_edge_rule: {summary['paper_graph_edge_rule']}",
        f"- previous_repo_graph_type: {summary['previous_repo_graph_type']}",
        f"- proposed_graph_type: {summary['proposed_graph_type']}",
        f"- can_build_branch_line_graph: {summary['can_build_branch_line_graph']}",
        f"- can_build_required_paper_features: {summary['can_build_required_paper_features']}",
        f"- can_build_paper_labels_from_existing_data: {summary['can_build_paper_labels_from_existing_data']}",
        f"- bus_fault_labels_directly_paper_aligned: {summary['bus_fault_labels_directly_paper_aligned']}",
        f"- line_trip_labels_first_priority: {summary['line_trip_labels_first_priority']}",
        f"- forbidden_features_detected_in_inputs: {summary['forbidden_features_detected_in_inputs']}",
        f"- final_engineering_conclusion: {summary['final_engineering_conclusion']}",
        "",
        "## Branch Graph",
        "",
        f"- num_branch_nodes: {graph['num_branch_nodes']}",
        f"- num_graph_edges: {graph['num_graph_edges']}",
        f"- adjacency_density: {graph['adjacency_density']:.6f}",
        f"- graph_is_candidate_similarity_graph: {graph['graph_is_candidate_similarity_graph']}",
        f"- graph_uses_physical_branch_connectivity: {graph['graph_uses_physical_branch_connectivity']}",
        "",
        "## Feature Readiness",
        "",
        f"- available_required_paper_features: {features['available_required_paper_features']}",
        f"- missing_required_paper_features: {features['missing_required_paper_features']}",
        f"- no_leakage_feature_policy_passed: {features['no_leakage_feature_policy_passed']}",
        "",
        "## Label Readiness",
        "",
        f"- paper_label_type: {labels['paper_label_type']}",
        f"- label_shape: {labels['label_shape']}",
        f"- can_build_paper_labels_from_existing_data: {labels['can_build_paper_labels_from_existing_data']}",
        "",
        "## Blocker And Next Step",
        "",
        f"- blocker_if_any: {summary['blocker_if_any']}",
        f"- recommended_next_step: {summary['recommended_next_step']}",
        "",
        "This is preparation for a future audit-only paper-aligned branch-as-node GCN prototype. It is not deployment and not reranker retraining.",
    ]
    doc.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate(payloads: dict[str, dict[str, Any]], strict: bool) -> None:
    summary = payloads["paper_aligned_branch_gcn_dry_run_validator_summary"]
    if summary["gcn_training_run"] or summary["simulink_run"] or summary["labels_exported"]:
        raise RuntimeError("Dry-run boundary violation.")
    if strict and not LINE_MAP.exists():
        raise RuntimeError(f"Missing topology source: {LINE_MAP}")
    if strict and summary["forbidden_features_detected_in_inputs"]:
        raise RuntimeError("Forbidden features detected in proposed inputs.")
    if strict:
        for value in payloads.values():
            for item in _flatten_strings(value):
                if "generator_speed_proxy is direct frequency" in item.lower():
                    raise RuntimeError("Forbidden overstatement detected.")


def _flatten_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        out: list[str] = []
        for sub_value in value.values():
            out.extend(_flatten_strings(sub_value))
        return out
    if isinstance(value, list):
        out: list[str] = []
        for sub_value in value:
            out.extend(_flatten_strings(sub_value))
        return out
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare IEEE39 paper-aligned branch-as-node GCN redesign dry-run artifacts.")
    parser.add_argument("--strict", action="store_true", help="Validate dry-run boundaries and source availability.")
    parser.add_argument("--write-report", action="store_true", help="Write JSON/MD/CSV artifacts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payloads = build_payloads()
    validate(payloads, strict=args.strict)
    if args.write_report:
        write_reports(payloads)
    print(json.dumps(payloads["paper_aligned_branch_gcn_dry_run_validator_summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
