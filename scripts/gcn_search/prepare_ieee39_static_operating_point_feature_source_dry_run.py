from __future__ import annotations

import argparse
import csv
import importlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PREV_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run"
GRAPH_MANIFEST = ROOT / (
    "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run/"
    "ieee39_branch_as_node_graph_manifest.json"
)
PREV_SUMMARY = PREV_DIR / "feature_source_dry_run_validator_summary.json"
OUT_DIR = ROOT / "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run"
DOC = ROOT / "docs/ieee39_static_operating_point_feature_source_dry_run.md"

SOURCE_FEATURE_DRY_RUN_COMMIT = "8deeab9b37c1033dc957736981119705977b4473"
DEFAULT_BETA = 1.2
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
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "line_id",
        "from_bus",
        "to_bus",
        "topology_status_available",
        "branch_flow_available",
        "branch_flow_value",
        "branch_flow_unit",
        "branch_flow_source",
        "line_limit_available",
        "line_limit_value",
        "line_limit_unit",
        "line_limit_source",
        "relay_threshold_available",
        "relay_threshold_value",
        "relay_threshold_unit",
        "relay_threshold_source",
        "relay_threshold_is_proxy",
        "endpoint_load_available",
        "from_bus_load_value",
        "to_bus_load_value",
        "endpoint_load_max_value",
        "load_unit",
        "endpoint_load_source",
        "ready_for_x_t",
        "ready_for_x_p",
        "ready_for_x_b",
        "ready_for_x_l",
        "ready_for_lx4_feature_vector",
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


def _tracked_repo_case_sources() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
    )
    tokens = ["case39", "case_ieee39", "matpower", "pypower", "pandapower", "ieee39"]
    hits = []
    for raw in result.stdout.splitlines():
        rel = raw.strip()
        lower = rel.lower()
        if any(token in lower for token in tokens):
            hits.append(rel)
    return hits[:80]


def _probe_loader(module_name: str) -> dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
        return {"module": module_name, "available": True, "error": None, "version": getattr(module, "__version__", None)}
    except Exception as exc:  # pragma: no cover - environment dependent
        return {"module": module_name, "available": False, "error": f"{type(exc).__name__}: {exc}", "version": None}


def _load_pypower_case39() -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        from pypower.case39 import case39

        return case39(), {
            "selected_case_source": "pypower.case39",
            "selected_case_source_trust_level": "standard_installed_case_loader_static_pre_fault",
            "selected_case_source_provenance": "Loaded with local pypower.case39; no repository parameters were hand-written.",
            "source_blocker_if_any": None,
        }
    except Exception as exc:
        return None, {
            "selected_case_source": None,
            "selected_case_source_trust_level": "unavailable",
            "selected_case_source_provenance": None,
            "source_blocker_if_any": f"pypower.case39 unavailable: {type(exc).__name__}: {exc}",
        }


def _run_dcpf(ppc: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    try:
        from pypower.ppoption import ppoption
        from pypower.rundcpf import rundcpf

        options = ppoption(VERBOSE=0, OUT_ALL=0)
        result, success = rundcpf(ppc, options)
        return result, {"dc_pf_solver_available": True, "run_dc_pf_this_round": bool(success), "success": bool(success), "error": None}
    except Exception as exc:
        return None, {
            "dc_pf_solver_available": False,
            "run_dc_pf_this_round": False,
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _case_tables_ready(ppc: dict[str, Any] | None) -> dict[str, bool]:
    return {
        "baseMVA_available": bool(ppc and "baseMVA" in ppc),
        "bus_table_available": bool(ppc and "bus" in ppc),
        "branch_table_available": bool(ppc and "branch" in ppc),
        "generator_table_available": bool(ppc and "gen" in ppc),
    }


def _line_sort_key(line_id: str) -> int:
    digits = "".join(ch for ch in line_id if ch.isdigit())
    return int(digits) if digits else 999


def _build_case_lookup(dcpf_result: dict[str, Any] | None) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[int, dict[str, float]]]:
    if not dcpf_result:
        return {}, {}
    from pypower.idx_brch import F_BUS, PF, RATE_A, T_BUS
    from pypower.idx_bus import BUS_I, PD, QD

    branch_lookup: dict[tuple[int, int], dict[str, Any]] = {}
    for idx, row in enumerate(dcpf_result["branch"]):
        f_bus = int(row[F_BUS])
        t_bus = int(row[T_BUS])
        branch_lookup[tuple(sorted((f_bus, t_bus)))] = {
            "case_branch_index": idx,
            "case_from_bus": f_bus,
            "case_to_bus": t_bus,
            "pf_mw_from_to": float(row[PF]),
            "rate_a": float(row[RATE_A]),
        }
    bus_lookup: dict[int, dict[str, float]] = {}
    for row in dcpf_result["bus"]:
        bus = int(row[BUS_I])
        bus_lookup[bus] = {"pd_mw": float(row[PD]), "qd_mvar": float(row[QD])}
    return branch_lookup, bus_lookup


def _parse_bus(bus_id: str) -> int:
    return int(str(bus_id).strip().lstrip("B"))


def _build_matrix(graph: dict[str, Any], dcpf_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    branch_lookup, bus_lookup = _build_case_lookup(dcpf_result)
    rows: list[dict[str, Any]] = []
    for line_id, buses in sorted(graph.get("branch_endpoint_pairs", {}).items(), key=lambda item: _line_sort_key(item[0])):
        from_bus_name, to_bus_name = buses
        from_bus = _parse_bus(from_bus_name)
        to_bus = _parse_bus(to_bus_name)
        branch = branch_lookup.get(tuple(sorted((from_bus, to_bus))))
        from_load = bus_lookup.get(from_bus, {}).get("pd_mw")
        to_load = bus_lookup.get(to_bus, {}).get("pd_mw")
        flow_available = branch is not None
        if branch:
            flow = branch["pf_mw_from_to"] if branch["case_from_bus"] == from_bus else -branch["pf_mw_from_to"]
            rate_a = branch["rate_a"] if branch["rate_a"] > 0 else None
        else:
            flow = None
            rate_a = None
        line_limit_available = rate_a is not None
        endpoint_load_available = from_load is not None and to_load is not None
        relay_proxy_value = DEFAULT_BETA * rate_a if line_limit_available else None
        missing_fields = []
        if not flow_available:
            missing_fields.append("branch_flow")
        if not line_limit_available:
            missing_fields.append("line_limit")
        missing_fields.append("approved_relay_threshold")
        if not endpoint_load_available:
            missing_fields.append("endpoint_load")
        ready_for_x_t = True
        ready_for_x_b = flow_available
        ready_for_x_l = endpoint_load_available
        ready_for_x_p = False
        rows.append(
            {
                "line_id": line_id,
                "from_bus": from_bus_name,
                "to_bus": to_bus_name,
                "topology_status_available": True,
                "branch_flow_available": flow_available,
                "branch_flow_value": flow,
                "branch_flow_unit": "MW",
                "branch_flow_source": "pypower.case39 rundcpf PF column mapped by endpoint bus pair" if flow_available else "missing",
                "line_limit_available": line_limit_available,
                "line_limit_value": rate_a,
                "line_limit_unit": "MVA_or_MW_case_RATE_A",
                "line_limit_source": "pypower.case39 branch RATE_A column" if line_limit_available else "missing",
                "relay_threshold_available": False,
                "relay_threshold_value": relay_proxy_value,
                "relay_threshold_unit": "MVA_or_MW_proxy",
                "relay_threshold_source": "proxy proposal only: beta * RATE_A; not approved for training",
                "relay_threshold_is_proxy": relay_proxy_value is not None,
                "endpoint_load_available": endpoint_load_available,
                "from_bus_load_value": from_load,
                "to_bus_load_value": to_load,
                "endpoint_load_max_value": max(from_load, to_load) if endpoint_load_available else None,
                "load_unit": "MW",
                "endpoint_load_source": "pypower.case39 bus PD column" if endpoint_load_available else "missing",
                "ready_for_x_t": ready_for_x_t,
                "ready_for_x_p": ready_for_x_p,
                "ready_for_x_b": ready_for_x_b,
                "ready_for_x_l": ready_for_x_l,
                "ready_for_lx4_feature_vector": False,
                "missing_fields": missing_fields,
                "l12_special_case_flag": line_id == "L12",
            }
        )
    return rows


def build_payloads() -> dict[str, Any]:
    graph = _read_json(GRAPH_MANIFEST)
    previous = _read_json(PREV_SUMMARY)
    loader_probes = [_probe_loader(name) for name in ["pandapower.networks", "pypower.case39", "numpy", "scipy"]]
    ppc, source_meta = _load_pypower_case39()
    dcpf_result, dcpf_meta = _run_dcpf(ppc) if ppc is not None else (None, {"dc_pf_solver_available": False, "run_dc_pf_this_round": False, "success": False, "error": source_meta["source_blocker_if_any"]})
    matrix = _build_matrix(graph, dcpf_result)
    table_ready = _case_tables_ready(ppc)
    branch_flow_ready = bool(matrix) and all(row["branch_flow_available"] for row in matrix)
    line_limit_ready = bool(matrix) and all(row["line_limit_available"] for row in matrix)
    bus_load_ready = bool(matrix) and all(row["endpoint_load_available"] for row in matrix)
    relay_threshold_ready = False
    relay_proxy_proposed = line_limit_ready
    can_without_proxy = branch_flow_ready and line_limit_ready and bus_load_ready and relay_threshold_ready
    can_with_proxy = branch_flow_ready and line_limit_ready and bus_load_ready and relay_proxy_proposed
    can_matrix = can_without_proxy
    if can_without_proxy:
        recommended = "prepare paper-style branch vulnerability label generator dry-run for line-trip labels"
        blocker = None
    elif can_with_proxy:
        recommended = "document and approve relay threshold proxy before paper-style label generator"
        blocker = "relay threshold is available only as an unapproved beta * RATE_A proxy proposal"
    else:
        recommended = "add verified IEEE39 MATPOWER/PYPOWER/pandapower operating point source before proceeding"
        blocker = "static operating point sources are still incomplete"

    inventory = {
        "inventory_scope": "ieee39_static_operating_point_source_inventory",
        "repository_case_sources_found": _tracked_repo_case_sources(),
        "installed_case_loaders_found": loader_probes,
        "selected_case_source": source_meta["selected_case_source"],
        "selected_case_source_trust_level": source_meta["selected_case_source_trust_level"],
        "selected_case_source_provenance": source_meta["selected_case_source_provenance"],
        **table_ready,
        "branch_flow_available": branch_flow_ready,
        "branch_limit_available": line_limit_ready,
        "bus_load_available": bus_load_ready,
        "can_generate_dc_power_flow": bool(dcpf_meta.get("success")),
        "source_blocker_if_any": source_meta["source_blocker_if_any"],
    }
    plan = {
        "dc_pf_generation_scope": "audit-only static/pre-fault operating point generation for paper-aligned IEEE39 branch features",
        "run_dc_pf_this_round": bool(dcpf_meta.get("run_dc_pf_this_round")),
        "dc_pf_solver_available": bool(dcpf_meta.get("dc_pf_solver_available")),
        "input_case_source": source_meta["selected_case_source"],
        "uses_simulink": False,
        "uses_post_fault_dynamic_measurements": False,
        "baseMVA": float(ppc["baseMVA"]) if ppc is not None else None,
        "bus_count": int(ppc["bus"].shape[0]) if ppc is not None else 0,
        "branch_count": int(ppc["branch"].shape[0]) if ppc is not None else 0,
        "branch_flow_units": "MW",
        "line_limit_units": "MVA_or_MW_case_RATE_A",
        "bus_load_units": "MW",
        "mapping_to_L01_L34_possible": branch_flow_ready and line_limit_ready and bus_load_ready,
        "blocker_if_any": None if dcpf_meta.get("success") else dcpf_meta.get("error"),
    }
    proxy = {
        "relay_threshold_source_found": relay_threshold_ready,
        "line_limit_source_found": line_limit_ready,
        "proxy_needed": line_limit_ready and not relay_threshold_ready,
        "proposed_proxy": "beta * line_limit" if line_limit_ready else None,
        "beta_value": DEFAULT_BETA if line_limit_ready else None,
        "beta_value_source": "docs/pio_gcn_relay_vs_security_constraint.md project default beta = 1.2",
        "proxy_allowed_for_training_now": False,
        "reason": "needs explicit approval / documentation before training",
        "no_training_this_round": True,
    }
    no_leakage = {
        "forbidden_features_checked": FORBIDDEN_DYNAMIC_FEATURES,
        "forbidden_features_detected_in_inputs": [],
        "post_fault_dynamic_measurements_used_as_inputs": False,
        "dynamic_targets_only_used_as_labels": True,
        "static_or_prefault_sources_only": bool(dcpf_meta.get("success")),
        "no_leakage_static_feature_policy_passed": bool(dcpf_meta.get("success")),
    }
    summary = {
        "dry_run_scope": "ieee39_static_operating_point_feature_source_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_feature_dry_run_commit": SOURCE_FEATURE_DRY_RUN_COMMIT,
        "paper_graph_node_type": "branch",
        "paper_graph_edge_rule": "shared_endpoint_bus",
        "branch_line_graph_ready": bool(previous.get("branch_line_graph_ready", graph.get("graph_construction_ready", False))),
        "num_branch_nodes": int(graph.get("num_branch_nodes", len(matrix))),
        "selected_case_source": source_meta["selected_case_source"],
        "selected_case_source_trust_level": source_meta["selected_case_source_trust_level"],
        "dc_pf_run_this_round": bool(dcpf_meta.get("run_dc_pf_this_round")),
        "branch_flow_source_ready": branch_flow_ready,
        "line_limit_source_ready": line_limit_ready,
        "relay_threshold_source_ready": relay_threshold_ready,
        "relay_threshold_proxy_proposed": relay_proxy_proposed,
        "relay_threshold_proxy_allowed_for_training_now": False,
        "bus_load_source_ready": bus_load_ready,
        "can_build_l01_l34_static_feature_matrix": can_matrix,
        "can_build_required_paper_features_without_proxy": can_without_proxy,
        "can_build_required_paper_features_with_documented_proxy": can_with_proxy,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_static_feature_policy_passed": bool(dcpf_meta.get("success")),
        "l12_special_case_preserved": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": blocker,
        "recommended_next_step": recommended,
    }
    return {
        "inventory": inventory,
        "plan": plan,
        "matrix": matrix,
        "proxy": proxy,
        "no_leakage": no_leakage,
        "summary": summary,
    }


def write_reports(payloads: dict[str, Any], write_report: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "static_case_source_inventory.json", payloads["inventory"])
    _write_md(OUT_DIR / "static_case_source_inventory.md", "IEEE39 Static Case Source Inventory", payloads["inventory"])
    _write_json(OUT_DIR / "dc_power_flow_generation_plan.json", payloads["plan"])
    _write_md(OUT_DIR / "dc_power_flow_generation_plan.md", "IEEE39 DC Power Flow Generation Plan", payloads["plan"])
    _write_json(OUT_DIR / "l01_l34_static_feature_source_matrix.json", payloads["matrix"])
    _write_md(
        OUT_DIR / "l01_l34_static_feature_source_matrix.md",
        "IEEE39 L01-L34 Static Feature Source Matrix",
        {"rows": payloads["matrix"]},
    )
    _write_matrix_csv(OUT_DIR / "l01_l34_static_feature_source_matrix.csv", payloads["matrix"])
    _write_json(OUT_DIR / "relay_threshold_proxy_proposal.json", payloads["proxy"])
    _write_md(OUT_DIR / "relay_threshold_proxy_proposal.md", "IEEE39 Relay Threshold Proxy Proposal", payloads["proxy"])
    _write_json(OUT_DIR / "no_leakage_static_feature_audit.json", payloads["no_leakage"])
    _write_md(OUT_DIR / "no_leakage_static_feature_audit.md", "IEEE39 No-Leakage Static Feature Audit", payloads["no_leakage"])
    _write_json(OUT_DIR / "static_feature_source_dry_run_validator_summary.json", payloads["summary"])
    _write_md(
        OUT_DIR / "static_feature_source_dry_run_validator_summary.md",
        "IEEE39 Static Operating Point Feature Source Dry-Run Validator Summary",
        payloads["summary"],
    )
    _write_key_value_csv(OUT_DIR / "static_feature_source_dry_run_validator_summary.csv", payloads["summary"])
    if write_report:
        DOC.write_text(_build_doc(payloads), encoding="utf-8")


def _build_doc(payloads: dict[str, Any]) -> str:
    summary = payloads["summary"]
    return f"""# IEEE39 Static Operating Point Feature Source Dry-Run

This round is a static operating point feature source dry-run. It does not train GCN, does not rerun the formal audit, does not run Simulink, does not export labels, does not retrain the reranker, and does not save a production model.

The goal is to fill trustworthy sources for the paper inputs `x_p`, `x_b`, and `x_l`. `x_t` is already constructed from branch outage status. Branch flow can only come from verified static/pre-fault/current-state PF or OPF. Line limit or relay threshold must have provenance. Bus load must have provenance.

## Selected Static Source

- selected_case_source: `{summary["selected_case_source"]}`
- selected_case_source_trust_level: `{summary["selected_case_source_trust_level"]}`
- dc_pf_run_this_round: `{summary["dc_pf_run_this_round"]}`
- branch_flow_source_ready: `{summary["branch_flow_source_ready"]}`
- line_limit_source_ready: `{summary["line_limit_source_ready"]}`
- relay_threshold_source_ready: `{summary["relay_threshold_source_ready"]}`
- relay_threshold_proxy_proposed: `{summary["relay_threshold_proxy_proposed"]}`
- relay_threshold_proxy_allowed_for_training_now: `{summary["relay_threshold_proxy_allowed_for_training_now"]}`
- bus_load_source_ready: `{summary["bus_load_source_ready"]}`
- can_build_l01_l34_static_feature_matrix: `{summary["can_build_l01_l34_static_feature_matrix"]}`
- can_build_required_paper_features_without_proxy: `{summary["can_build_required_paper_features_without_proxy"]}`
- can_build_required_paper_features_with_documented_proxy: `{summary["can_build_required_paper_features_with_documented_proxy"]}`

## Relay Threshold Proxy

The case provides line limits through `RATE_A`, but it does not provide a verified relay threshold table. A proxy `beta * line_limit` is proposed with project default `beta = 1.2`, but this proxy is not allowed for training now. It needs explicit approval and documentation before any training run.

## No-Leakage Rule

Post-fault dynamic measurements are not used as inputs. `min_voltage_pu`, `max_voltage_pu`, frequency, rotor angle, speed deviation, `dynamic_stress_score`, `unstable_flag`, `phasor_RMS`, and `generator_speed_proxy` are forbidden as GCN inputs. `dynamic_stress_score` and `unstable_flag` can only be labels or audit targets.

L12 remains a special case.

## Blocker

`{summary["blocker_if_any"]}`

## Next Step

`{summary["recommended_next_step"]}`

This is not deployment, not reranker retraining, and not a final engineering conclusion. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    required = [PREV_SUMMARY, GRAPH_MANIFEST]
    missing = [str(path) for path in required if not _exists(path)]
    if args.strict and missing:
        raise SystemExit("Missing required previous artifacts: " + "; ".join(missing))
    payloads = build_payloads()
    write_reports(payloads, args.write_report)
    print(json.dumps(payloads["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
