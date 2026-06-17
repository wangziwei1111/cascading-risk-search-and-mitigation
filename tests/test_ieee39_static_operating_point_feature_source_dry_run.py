from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_static_operating_point_feature_source_dry_run"
DOC = ROOT / "docs/ieee39_static_operating_point_feature_source_dry_run.md"


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path):
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def test_static_operating_point_dry_run_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/prepare_ieee39_static_operating_point_feature_source_dry_run.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_static_operating_point_dry_run_artifacts_exist() -> None:
    expected = [
        "static_case_source_inventory.json",
        "static_case_source_inventory.md",
        "dc_power_flow_generation_plan.json",
        "dc_power_flow_generation_plan.md",
        "l01_l34_static_feature_source_matrix.json",
        "l01_l34_static_feature_source_matrix.md",
        "l01_l34_static_feature_source_matrix.csv",
        "relay_threshold_proxy_proposal.json",
        "relay_threshold_proxy_proposal.md",
        "no_leakage_static_feature_audit.json",
        "no_leakage_static_feature_audit.md",
        "static_feature_source_dry_run_validator_summary.json",
        "static_feature_source_dry_run_validator_summary.md",
        "static_feature_source_dry_run_validator_summary.csv",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_static_operating_point_dry_run_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "static_feature_source_dry_run_validator_summary.json")
    inventory = _read_json(OUT_DIR / "static_case_source_inventory.json")
    plan = _read_json(OUT_DIR / "dc_power_flow_generation_plan.json")
    proxy = _read_json(OUT_DIR / "relay_threshold_proxy_proposal.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_static_feature_audit.json")

    assert summary["dry_run_scope"] == "ieee39_static_operating_point_feature_source_dry_run"
    assert summary["gcn_training_run"] is False
    assert summary["formal_gcn_audit_rerun"] is False
    assert summary["simulink_run"] is False
    assert summary["labels_exported"] is False
    assert summary["reranker_retrained"] is False
    assert summary["production_model_saved"] is False
    assert summary["paper_graph_node_type"] == "branch"
    assert summary["paper_graph_edge_rule"] == "shared_endpoint_bus"
    assert summary["branch_line_graph_ready"] is True
    assert summary["num_branch_nodes"] == 34
    assert summary["selected_case_source"] == "pypower.case39"
    assert summary["selected_case_source_trust_level"] == "standard_installed_case_loader_static_pre_fault"
    assert summary["dc_pf_run_this_round"] is True
    assert summary["branch_flow_source_ready"] is True
    assert summary["line_limit_source_ready"] is True
    assert summary["relay_threshold_source_ready"] is False
    assert summary["relay_threshold_proxy_proposed"] is True
    assert summary["relay_threshold_proxy_allowed_for_training_now"] is False
    assert summary["bus_load_source_ready"] is True
    assert summary["can_build_l01_l34_static_feature_matrix"] is False
    assert summary["can_build_required_paper_features_without_proxy"] is False
    assert summary["can_build_required_paper_features_with_documented_proxy"] is True
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["no_leakage_static_feature_policy_passed"] is True
    assert summary["l12_special_case_preserved"] is True
    assert summary["final_engineering_conclusion"] is False
    assert summary["should_train_gcn_now"] is False
    assert summary["should_rerun_formal_audit_now"] is False
    assert summary["should_retrain_reranker_now"] is False
    assert summary["should_deploy_model"] is False
    assert "unapproved beta * RATE_A proxy" in summary["blocker_if_any"]

    assert inventory["inventory_scope"] == "ieee39_static_operating_point_source_inventory"
    assert inventory["baseMVA_available"] is True
    assert inventory["bus_table_available"] is True
    assert inventory["branch_table_available"] is True
    assert inventory["generator_table_available"] is True
    assert inventory["branch_flow_available"] is True
    assert inventory["branch_limit_available"] is True
    assert inventory["bus_load_available"] is True
    assert inventory["can_generate_dc_power_flow"] is True

    assert plan["run_dc_pf_this_round"] is True
    assert plan["uses_simulink"] is False
    assert plan["uses_post_fault_dynamic_measurements"] is False
    assert plan["baseMVA"] == 100.0
    assert plan["bus_count"] == 39
    assert plan["branch_count"] == 46
    assert plan["mapping_to_L01_L34_possible"] is True

    assert proxy["relay_threshold_source_found"] is False
    assert proxy["line_limit_source_found"] is True
    assert proxy["proxy_needed"] is True
    assert proxy["proposed_proxy"] == "beta * line_limit"
    assert proxy["beta_value"] == 1.2
    assert proxy["proxy_allowed_for_training_now"] is False
    assert proxy["no_training_this_round"] is True

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_targets_only_used_as_labels"] is True
    assert no_leakage["static_or_prefault_sources_only"] is True
    assert no_leakage["no_leakage_static_feature_policy_passed"] is True


def test_static_operating_point_l01_l34_matrix() -> None:
    matrix = _read_json(OUT_DIR / "l01_l34_static_feature_source_matrix.json")
    assert len(matrix) == 34
    assert matrix[0]["line_id"] == "L01"
    assert matrix[-1]["line_id"] == "L34"
    assert all(row["branch_flow_available"] for row in matrix)
    assert all(row["line_limit_available"] for row in matrix)
    assert all(row["endpoint_load_available"] for row in matrix)
    assert not any(row["relay_threshold_available"] for row in matrix)
    assert all(row["relay_threshold_is_proxy"] for row in matrix)
    assert not any(row["ready_for_x_p"] for row in matrix)
    assert not any(row["ready_for_lx4_feature_vector"] for row in matrix)
    assert [row for row in matrix if row["line_id"] == "L12"][0]["l12_special_case_flag"] is True

    with open(_long(OUT_DIR / "l01_l34_static_feature_source_matrix.csv"), newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 34
    assert rows[0]["branch_flow_unit"] == "MW"


def test_static_operating_point_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(OUT_DIR / "static_case_source_inventory.md"),
            _read_text(OUT_DIR / "relay_threshold_proxy_proposal.md"),
            _read_text(OUT_DIR / "no_leakage_static_feature_audit.md"),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "static operating point feature source dry-run",
        "does not train gcn",
        "does not rerun the formal audit",
        "does not run simulink",
        "does not export labels",
        "does not retrain the reranker",
        "branch flow can only come from verified static/pre-fault/current-state pf or opf",
        "relay threshold proxy",
        "not allowed for training now",
        "post-fault dynamic measurements are not used as inputs",
        "l12 remains a special case",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "final engineering conclusion: true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "production_model_saved = true",
    ]:
        assert forbidden not in normalized


def test_static_operating_point_no_forbidden_large_artifacts_tracked() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    changed = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    forbidden_tokens = [
        ".venv-gcn-audit/",
        ".venv/",
        "site-packages",
        ".whl",
        ".dll",
        ".pt",
        ".pth",
        ".ckpt",
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    bad = [path for path in changed if any(token in path for token in forbidden_tokens)]
    assert not bad, bad
