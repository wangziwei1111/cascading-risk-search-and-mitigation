from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_spp001_single_pair_smoke_rerun"
DOC = ROOT / "docs/ieee39_spp001_single_pair_smoke_rerun.md"


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


def test_spp001_rerun_runner_writes_compact_artifacts() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--single-pair-smoke-only",
            "--pair-id",
            "SPP001",
            "--execute",
            "--max-pairs",
            "1",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_spp001_rerun_artifacts_exist() -> None:
    expected = [
        "spp001_rerun_approval.json",
        "spp001_rerun_approval.md",
        "spp001_rerun_summary.json",
        "spp001_rerun_summary.md",
        "spp001_rerun_summary.csv",
        "spp001_rerun_result.json",
        "spp001_rerun_result.md",
        "spp001_rerun_result.csv",
        "spp001_rerun_label_distribution.json",
        "spp001_rerun_label_distribution.md",
        "spp001_no_leakage_rerun_audit.json",
        "spp001_no_leakage_rerun_audit.md",
        "spp001_large_file_safety_rerun.json",
        "spp001_large_file_safety_rerun.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_spp001_rerun_summary_result_and_approval_fields() -> None:
    approval = _read_json(OUT_DIR / "spp001_rerun_approval.json")
    summary = _read_json(OUT_DIR / "spp001_rerun_summary.json")
    result = _read_json(OUT_DIR / "spp001_rerun_result.json")
    distribution = _read_json(OUT_DIR / "spp001_rerun_label_distribution.json")

    assert approval["approval_scope"] == "spp001_single_pair_smoke_rerun_approval"
    assert approval["approved_pair_count"] == 1
    assert approval["pair_id"] == "SPP001"
    assert approval["prior_outaged_branch"] == "L15"
    assert approval["candidate_next_branch"] == "L04"
    assert approval["selected_32_batch_execution_approved"] is False
    assert approval["full_1056_generation_approved"] is False
    assert approval["formal_label_export_approved"] is False
    assert approval["gcn_training_approved"] is False
    assert approval["reranker_retrain_approved"] is False

    expected = {
        "execution_scope": "spp001_single_pair_smoke_rerun",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_batch_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_l15_readiness_repair_commit": "a648b8cb2d4fb3a4c27a5e7f3e8e588280ddc0d1",
        "pair_id": "SPP001",
        "state_id": "single_outage_state_L15",
        "prior_outaged_branch": "L15",
        "candidate_next_branch": "L04",
        "selection_bucket": "high_relay_ratio_pairs",
        "l15_ready": True,
        "l04_ready": True,
        "execution_attempted": True,
        "single_pair_executed": summary["execution_status"] == "succeeded",
        "simulink_run": summary["execution_status"] == "succeeded",
        "pilot_labels_are_formal_training_labels": False,
        "source_slx_modified": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key

    assert summary["execution_status"] in {"succeeded", "failed", "timeout", "blocked"}
    assert summary["pilot_label_value"] in {0, 1, None}
    if summary["execution_status"] != "succeeded":
        assert summary["pilot_label_value"] is None
    assert result["pair_id"] == "SPP001"
    assert result["prior_outaged_branch"] == "L15"
    assert result["candidate_next_branch"] == "L04"
    assert distribution["pair_count"] == 1
    assert distribution["pilot_only"] is True
    assert distribution["formal_training_labels"] is False


def test_spp001_rerun_no_leakage_and_large_file_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "spp001_no_leakage_rerun_audit.json")
    safety = _read_json(OUT_DIR / "spp001_large_file_safety_rerun.json")

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_future_labels_or_targets"] is True
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["line_trip_labels_first_priority"] is True
    assert no_leakage["no_leakage_policy_passed"] is True

    for key in [
        "raw_trajectories_committed",
        "full_timeseries_committed",
        "mat_files_committed",
        "slx_files_committed",
        "slxc_files_committed",
        "slprj_committed",
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_spp001_rerun_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(OUT_DIR / "spp001_rerun_summary.md"),
            _read_text(OUT_DIR / "spp001_rerun_result.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "spp001 single-pair smoke rerun",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute the selected 32 batch",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "l15 -> l04",
        "pilot labels are not formal training labels",
        "not a final project conclusion",
        "bus-fault labels are not used",
        "line-trip labels remain first priority",
        "l12 remains special/excluded",
        "raw trajectories",
        "full timeseries",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal labels exported",
        "selected 32 batch executed",
        "full 1056 generation completed",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_spp001_rerun_no_forbidden_large_artifacts_tracked() -> None:
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
