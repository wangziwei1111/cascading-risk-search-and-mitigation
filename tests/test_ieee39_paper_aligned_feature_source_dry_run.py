from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_feature_source_dry_run"
DOC = ROOT / "docs/ieee39_paper_aligned_feature_source_dry_run.md"


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


def test_feature_source_dry_run_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/prepare_ieee39_paper_aligned_feature_source_dry_run.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_feature_source_dry_run_artifacts_exist() -> None:
    expected = [
        "feature_source_inventory.json",
        "feature_source_inventory.md",
        "l01_l34_feature_readiness_matrix.json",
        "l01_l34_feature_readiness_matrix.md",
        "l01_l34_feature_readiness_matrix.csv",
        "paper_feature_mapping_plan.json",
        "paper_feature_mapping_plan.md",
        "no_leakage_feature_source_audit.json",
        "no_leakage_feature_source_audit.md",
        "feature_source_dry_run_validator_summary.json",
        "feature_source_dry_run_validator_summary.md",
        "feature_source_dry_run_validator_summary.csv",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_feature_source_dry_run_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "feature_source_dry_run_validator_summary.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_feature_source_audit.json")
    matrix = _read_json(OUT_DIR / "l01_l34_feature_readiness_matrix.json")
    inventory = _read_json(OUT_DIR / "feature_source_inventory.json")
    mapping = _read_json(OUT_DIR / "paper_feature_mapping_plan.json")

    assert summary["dry_run_scope"] == "paper_aligned_feature_source_dry_run"
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
    assert summary["branch_flow_source_ready"] is False
    assert summary["line_limit_source_ready"] is False
    assert summary["relay_threshold_source_ready"] is False
    assert summary["bus_load_source_ready"] is False
    assert summary["can_build_required_paper_features"] is False
    assert summary["can_build_l01_l34_feature_matrix"] is False
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["no_leakage_feature_source_policy_passed"] is True
    assert summary["l12_special_case_preserved"] is True
    assert summary["final_engineering_conclusion"] is False
    assert summary["should_train_gcn_now"] is False
    assert summary["should_rerun_formal_audit_now"] is False
    assert summary["should_retrain_reranker_now"] is False
    assert summary["should_deploy_model"] is False
    assert "verified current-state branch flow" in summary["blocker_if_any"]

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_targets_only_used_as_labels"] is True
    assert no_leakage["bus_fault_labels_not_used_as_paper_inputs"] is True
    assert no_leakage["no_leakage_feature_source_policy_passed"] is True

    assert inventory["inventory_scope"] == "paper_aligned_feature_source_inventory"
    assert inventory["verified_sources_ready"] is False
    assert "verified_current_state_branch_flow" in inventory["missing_source_categories"]
    assert inventory["post_fault_sources_detected_and_forbidden"]
    assert mapping["feature_vector_shape"] == "L x 4"
    assert mapping["current_L"] == 34
    assert "dynamic_stress_score" in mapping["forbidden_dynamic_measurement_inputs"]

    assert len(matrix) == 34
    l12 = [row for row in matrix if row["line_id"] == "L12"]
    assert l12 and l12[0]["l12_special_case_flag"] is True
    assert all(row["topology_status_available"] is True for row in matrix)
    assert not any(row["ready_for_paper_feature_vector"] for row in matrix)


def test_feature_source_dry_run_matrix_csv_shape() -> None:
    with open(_long(OUT_DIR / "l01_l34_feature_readiness_matrix.csv"), newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 34
    assert rows[0]["line_id"] == "L01"
    assert rows[-1]["line_id"] == "L34"
    assert {row["ready_for_paper_feature_vector"] for row in rows} == {"False"}


def test_feature_source_dry_run_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(OUT_DIR / "feature_source_inventory.md"),
            _read_text(OUT_DIR / "paper_feature_mapping_plan.md"),
            _read_text(OUT_DIR / "no_leakage_feature_source_audit.md"),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "paper-aligned feature source dry-run",
        "does not train gcn",
        "does not rerun the formal audit",
        "does not run simulink",
        "does not export labels",
        "does not retrain the reranker",
        "x_t",
        "x_p",
        "x_b",
        "x_l",
        "branch flow",
        "relay threshold",
        "endpoint load",
        "post-fault dynamic measurement cannot replace",
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


def test_feature_source_dry_run_no_forbidden_large_artifacts_tracked() -> None:
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
