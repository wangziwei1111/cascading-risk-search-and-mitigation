from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_diagnosis"
DOC = ROOT / "docs/ieee39_controlled_execution_backend_diagnosis.md"


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


def test_backend_diagnosis_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/diagnose_ieee39_controlled_execution_backend.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_backend_diagnosis_artifacts_exist() -> None:
    expected = [
        "backend_readiness_summary.json",
        "backend_readiness_summary.md",
        "backend_readiness_summary.csv",
        "backend_component_inventory.json",
        "backend_component_inventory.md",
        "selected_pair_execution_mapping_diagnosis.json",
        "selected_pair_execution_mapping_diagnosis.md",
        "selected_pair_execution_mapping_diagnosis.csv",
        "safe_execution_repair_plan.json",
        "safe_execution_repair_plan.md",
        "no_leakage_backend_diagnosis_audit.json",
        "no_leakage_backend_diagnosis_audit.md",
        "large_file_safety_backend_diagnosis.json",
        "large_file_safety_backend_diagnosis.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_backend_readiness_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "backend_readiness_summary.json")
    expected = {
        "diagnosis_scope": "controlled_execution_backend_diagnosis",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "selected_pairs_executed": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_execution_commit": "606eba793b3895c333ab0c632369bfadde413dca",
        "selected_pair_count": 32,
        "ieee39_wrapper_model_found": True,
        "selected_pair_mapping_found": True,
        "two_step_line_trip_injection_supported": False,
        "batch_runner_found": False,
        "timeout_policy_found": True,
        "result_parser_found": False,
        "evidence_writer_found": True,
        "safe_no_raw_artifact_policy_found": True,
        "can_execute_selected_32_pairs_now": False,
        "can_execute_without_full_1056": True,
        "graceful_blocked_mode_available": True,
        "recommended_next_step": (
            "add a selected-32-only controlled execution backend or write local manual execution instructions before rerunning evidence collection"
        ),
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert summary["matlab_available"] in {True, False, "unknown"}
    assert summary["simulink_available"] in {True, False, "unknown"}
    assert "missing approved two-step line-trip sequence injection" in summary["blocker_if_any"]


def test_backend_inventory_mapping_and_repair_plan() -> None:
    inventory = _read_json(OUT_DIR / "backend_component_inventory.json")
    mapping = _read_json(OUT_DIR / "selected_pair_execution_mapping_diagnosis.json")
    repair = _read_json(OUT_DIR / "safe_execution_repair_plan.json")
    assert inventory["candidate_matlab_scripts"]
    assert inventory["candidate_python_wrappers"]
    assert inventory["candidate_simulink_models"]
    assert inventory["candidate_line_trip_maps"]
    assert inventory["candidate_evidence_writers"]
    assert "approved selected-pair two-step line-trip sequence injection" in inventory["missing_components"]
    assert "selected-32-only batch runner" in inventory["missing_components"]
    assert "selected-pair dynamic result parser contract" in inventory["missing_components"]
    assert "IEEE39 wrapper model path" in inventory["reusable_components"]

    assert len(mapping) == 32
    assert all(row["prior_branch_mapping_available"] is True for row in mapping)
    assert all(row["next_branch_mapping_available"] is True for row in mapping)
    assert all(row["sequence_injection_supported"] is False for row in mapping)
    assert all(row["execution_ready"] is False for row in mapping)
    assert all(row["l12_special_case_flag"] is False for row in mapping)
    with open(_long(OUT_DIR / "selected_pair_execution_mapping_diagnosis.csv"), newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 32

    assert repair["repair_plan_scope"] == "controlled_execution_backend_repair_plan"
    assert "selected-32-only batch runner" in repair["required_components_to_add"]
    assert repair["manual_approval_required_before_execution"] is True
    assert "--approved-selected-pairs-only" in repair["proposed_selected_32_only_guard"]
    assert "do not commit raw trajectories" in repair["proposed_large_file_policy"]


def test_backend_no_leakage_and_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "no_leakage_backend_diagnosis_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_backend_diagnosis.json")
    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_future_labels_or_targets"] is True
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["proxy_relay_threshold_used_only_in_feature_generation"] is True
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["no_leakage_policy_passed"] is True

    for key in [
        "raw_trajectories_committed",
        "full_timeseries_committed",
        "mat_files_committed",
        "slx_files_committed",
        "slxc_files_committed",
        "slprj_committed",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_backend_diagnosis_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
            _read_text(ROOT / "docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"),
            _read_text(OUT_DIR / "backend_readiness_summary.md"),
            _read_text(OUT_DIR / "safe_execution_repair_plan.md"),
            _read_text(OUT_DIR / "no_leakage_backend_diagnosis_audit.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "controlled execution backend diagnosis",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute selected 32 pairs",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "selected pair execution 被 blocked",
        "controlled simulink execution backend",
        "raw trajectory, full timeseries, or .mat",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "nf06 warning is preserved",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "selected 32 pairs executed",
        "full 1056 generation completed",
        "formal labels exported",
        "proxy is a real relay setting",
        "final engineering conclusion: true",
        "emt simulation",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_backend_diagnosis_no_forbidden_large_artifacts_tracked() -> None:
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
        "raw_trajector",
        "full_timeseries",
        "local_lab_copies",
    ]
    for path in changed:
        assert not any(token in path for token in forbidden_tokens), path
