from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_selected_single_outage_pilot_pair_execution"
DOC = ROOT / "docs/ieee39_selected_single_outage_pilot_pair_execution.md"


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


def test_selected_single_outage_pair_execution_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/execute_ieee39_selected_single_outage_pilot_pairs.py",
            "--approved-selected-pairs-only",
            "--max-pairs",
            "32",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_selected_single_outage_pair_execution_artifacts_exist() -> None:
    expected = [
        "selected_pair_execution_approval.json",
        "selected_pair_execution_approval.md",
        "selected_pair_execution_summary.json",
        "selected_pair_execution_summary.md",
        "selected_pair_execution_summary.csv",
        "selected_pair_execution_results.json",
        "selected_pair_execution_results.md",
        "selected_pair_execution_results.csv",
        "selected_pair_label_distribution.json",
        "selected_pair_label_distribution.md",
        "no_leakage_selected_pair_execution_audit.json",
        "no_leakage_selected_pair_execution_audit.md",
        "large_file_and_artifact_safety_check.json",
        "large_file_and_artifact_safety_check.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_selected_single_outage_pair_execution_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "selected_pair_execution_summary.json")
    expected = {
        "execution_scope": "selected_single_outage_pilot_pair_execution",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "new_simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_dry_run_commit": "07d4f7b3a6d40f4695312ff8c9b8e9704b2facac",
        "selected_pair_count": 32,
        "executed_pair_count": 0,
        "succeeded_pair_count": 0,
        "failed_pair_count": 0,
        "timeout_pair_count": 0,
        "unknown_pair_count": 32,
        "pilot_label_available_count": 0,
        "pilot_positive_count": 0,
        "pilot_negative_count": 0,
        "pilot_unknown_count": 32,
        "pilot_excluded_count": 0,
        "raw_trajectories_committed": False,
        "full_timeseries_committed": False,
        "mat_files_committed": False,
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
        "recommended_next_step": (
            "fix controlled execution environment or run selected pair execution locally, then rerun evidence collection"
        ),
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert "controlled Simulink execution backend is not available" in summary["blocker_if_any"]


def test_selected_single_outage_pair_execution_approval_and_results_schema() -> None:
    approval = _read_json(OUT_DIR / "selected_pair_execution_approval.json")
    results = _read_json(OUT_DIR / "selected_pair_execution_results.json")
    assert approval["approval_scope"] == "selected_single_outage_pilot_pair_execution_approval"
    assert approval["source_dry_run_commit"] == "07d4f7b3a6d40f4695312ff8c9b8e9704b2facac"
    assert approval["approved_pair_count"] == 32
    assert approval["approved_selected_pairs_only"] is True
    assert approval["full_1056_generation_approved"] is False
    assert approval["formal_label_export_approved"] is False
    assert approval["gcn_training_approved"] is False
    assert approval["reranker_retrain_approved"] is False
    assert approval["raw_trajectory_commit_approved"] is False
    assert approval["beta_rate_a_proxy_acknowledged"] is True
    assert approval["proxy_allowed_for_audit_only_prototype"] is True
    assert approval["proxy_allowed_for_production"] is False

    assert len(results) == 32
    assert all(row["execution_status"] == "blocked" for row in results)
    assert all(row["pilot_label_value"] is None for row in results)
    assert all(row["pilot_label_status"] == "blocked" for row in results)
    assert all(row["raw_trajectory_committed"] is False for row in results)
    assert all(row["full_timeseries_committed"] is False for row in results)
    assert all(row["mat_file_committed"] is False for row in results)
    assert all(row["bus_fault_label_used"] is False for row in results)
    assert all(row["l12_special_case_flag"] is False for row in results)
    assert all("L12" not in {row["prior_outaged_branch"], row["candidate_next_branch"]} for row in results)
    assert all("no pilot labels" in row["timeout_or_failure_reason"] for row in results)
    with open(_long(OUT_DIR / "selected_pair_execution_results.csv"), newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 32


def test_selected_single_outage_pair_distribution_no_leakage_and_safety() -> None:
    distribution = _read_json(OUT_DIR / "selected_pair_label_distribution.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_selected_pair_execution_audit.json")
    safety = _read_json(OUT_DIR / "large_file_and_artifact_safety_check.json")
    assert distribution["selected_pair_count"] == 32
    assert distribution["pilot_label_available_count"] == 0
    assert distribution["pilot_positive_count"] == 0
    assert distribution["pilot_negative_count"] == 0
    assert distribution["pilot_unknown_count"] == 32
    assert distribution["pilot_timeout_count"] == 0
    assert distribution["pilot_failed_count"] == 0
    assert distribution["pilot_blocked_count"] == 32
    assert distribution["all_available_labels_negative"] is False
    assert distribution["has_positive_pilot_label"] is False
    assert "no pilot labels available" in distribution["class_balance_warning"]

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


def test_selected_single_outage_pair_execution_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"),
            _read_text(ROOT / "docs/ieee39_single_outage_label_loop_dry_run.md"),
            _read_text(OUT_DIR / "selected_pair_execution_summary.md"),
            _read_text(OUT_DIR / "selected_pair_label_distribution.md"),
            _read_text(OUT_DIR / "no_leakage_selected_pair_execution_audit.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "selected 32 single-outage pilot pair execution",
        "does not train gcn",
        "does not rerun formal audit",
        "does not export formal labels",
        "does not retrain the reranker",
        "not full 1056 generation",
        "raw trajectories, full timeseries",
        "timeout, unknown, blocked, or failed cases are not converted to 0/1",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "nf06 warning is preserved",
        "pilot labels are not formal training labels",
        "no deployment",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "formal labels exported",
        "full 1056 generation completed",
        "proxy is a real relay setting",
        "final engineering conclusion: true",
        "emt simulation",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_selected_single_outage_pair_execution_no_forbidden_large_artifacts_tracked() -> None:
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
