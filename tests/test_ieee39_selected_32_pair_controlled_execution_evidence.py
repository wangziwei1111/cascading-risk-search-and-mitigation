from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_selected_32_pair_controlled_execution_evidence"
DOC = ROOT / "docs/ieee39_selected_32_pair_controlled_execution_evidence.md"


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


def test_selected_32_execution_runner_writes_blocked_evidence() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--execute",
            "--max-pairs",
            "32",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_selected_32_execution_artifacts_exist() -> None:
    expected = [
        "selected_32_execution_approval.json",
        "selected_32_execution_approval.md",
        "selected_32_execution_summary.json",
        "selected_32_execution_summary.md",
        "selected_32_execution_summary.csv",
        "selected_32_execution_results.json",
        "selected_32_execution_results.md",
        "selected_32_execution_results.csv",
        "selected_32_label_distribution.json",
        "selected_32_label_distribution.md",
        "no_leakage_selected_32_execution_audit.json",
        "no_leakage_selected_32_execution_audit.md",
        "large_file_safety_selected_32_execution.json",
        "large_file_safety_selected_32_execution.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_selected_32_execution_approval_fields() -> None:
    approval = _read_json(OUT_DIR / "selected_32_execution_approval.json")
    expected = {
        "approval_scope": "selected_32_controlled_execution_approval",
        "source_backend_repair_commit": "5c15cf88c3d980e3491d7327602a4d318216f2e4",
        "approved_selected_pairs_only": True,
        "approved_pair_count": 32,
        "full_1056_generation_approved": False,
        "formal_label_export_approved": False,
        "gcn_training_approved": False,
        "reranker_retrain_approved": False,
        "raw_trajectory_commit_approved": False,
        "explicit_execute_required": True,
        "beta_rate_a_proxy_acknowledged": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
    }
    for key, value in expected.items():
        assert approval.get(key) == value, key


def test_selected_32_execution_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "selected_32_execution_summary.json")
    expected = {
        "execution_scope": "selected_32_controlled_execution_evidence",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_backend_repair_commit": "5c15cf88c3d980e3491d7327602a4d318216f2e4",
        "selected_pair_count": 32,
        "executed_pair_count": 0,
        "succeeded_pair_count": 0,
        "failed_pair_count": 0,
        "timeout_pair_count": 0,
        "blocked_pair_count": 32,
        "pilot_label_available_count": 0,
        "pilot_positive_count": 0,
        "pilot_negative_count": 0,
        "pilot_unknown_count": 32,
        "pilot_blocked_count": 32,
        "has_positive_pilot_label": False,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
        "slx_files_committed": False,
        "slxc_files_committed": False,
        "slprj_committed": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "pilot_labels_are_formal_training_labels": False,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert "guarded skeleton" in summary["blocker_if_any"]


def test_selected_32_execution_results_are_blocked_null() -> None:
    rows = _read_json(OUT_DIR / "selected_32_execution_results.json")
    assert len(rows) == 32
    with open(_long(OUT_DIR / "selected_32_execution_results.csv"), newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 32
    for row in rows:
        assert row["execution_status"] == "blocked"
        assert row["pilot_label_value"] is None
        assert row["pilot_label_status"] == "blocked"
        assert row["dynamic_stress_score_if_available"] is None
        assert row["unstable_flag_if_available"] is None
        assert row["raw_trajectory_committed"] is False
        assert row["full_timeseries_committed"] is False
        assert row["mat_file_committed"] is False
        assert row["bus_fault_label_used"] is False
        assert row["l12_special_case_flag"] is False


def test_selected_32_label_distribution_no_leakage_and_safety() -> None:
    distribution = _read_json(OUT_DIR / "selected_32_label_distribution.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_selected_32_execution_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_selected_32_execution.json")
    assert distribution["selected_pair_count"] == 32
    assert distribution["pilot_label_available_count"] == 0
    assert distribution["pilot_positive_count"] == 0
    assert distribution["pilot_negative_count"] == 0
    assert distribution["pilot_unknown_count"] == 32
    assert distribution["pilot_blocked_count"] == 32
    assert distribution["has_positive_pilot_label"] is False
    assert "do not train" in distribution["training_readiness_recommendation"]

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_labels_or_targets"] is True
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


def test_selected_32_execution_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_controlled_execution_backend_repair.md"),
            _read_text(ROOT / "docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
            _read_text(OUT_DIR / "selected_32_execution_summary.md"),
            _read_text(OUT_DIR / "selected_32_execution_results.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "selected 32 pair controlled execution evidence",
        "does not train gcn",
        "does not rerun formal audit",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "only selected 32 pairs",
        "compact blocked evidence",
        "raw trajectories",
        "full timeseries",
        "blocked, and unknown results are not converted to 0/1",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "nf06 warning is preserved",
        "pilot labels are not formal training labels",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "full 1056 generation completed",
        "formal labels exported",
        "proxy is a real relay setting",
        "emt simulation",
        "generator_speed_proxy is direct frequency",
        "final engineering conclusion",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_selected_32_execution_no_forbidden_large_artifacts_tracked() -> None:
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
