import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run"
SUMMARY_JSON = OUT_DIR / "gcn_audit_dry_run_validator_summary.json"
SUMMARY_MD = OUT_DIR / "gcn_audit_dry_run_validator_summary.md"
SUMMARY_CSV = OUT_DIR / "gcn_audit_dry_run_validator_summary.csv"
MANIFEST_JSON = OUT_DIR / "proposed_no_leakage_gcn_inputs_manifest.json"
MANIFEST_MD = OUT_DIR / "proposed_no_leakage_gcn_inputs_manifest.md"
DRAFT_JSON = OUT_DIR / "formal_gcn_audit_execution_draft.json"
DRAFT_MD = OUT_DIR / "formal_gcn_audit_execution_draft.md"
ROUND_DOC = ROOT / "docs/ieee39_gcn_usefulness_audit_dry_run_validator.md"


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def test_dry_run_validator_executes_and_writes_artifacts() -> None:
    subprocess.run(
        [
            "python",
            "scripts/gcn_search/run_ieee39_gcn_usefulness_audit_dry_run_validator.py",
            "--strict",
            "--dry-run",
        ],
        cwd=ROOT,
        text=True,
        check=True,
    )
    for path in [SUMMARY_JSON, SUMMARY_MD, SUMMARY_CSV, MANIFEST_JSON, MANIFEST_MD, DRAFT_JSON, DRAFT_MD, ROUND_DOC]:
        assert os.path.exists(_long(path)), path.name


def test_dry_run_summary_fields() -> None:
    summary = _read_json(SUMMARY_JSON)
    manifest = _read_json(MANIFEST_JSON)
    draft = _read_json(DRAFT_JSON)
    assert summary["validator_scope"] == "dry_run_only"
    assert summary["audit_execution_this_round"] is False
    assert summary["gcn_trained_this_round"] is False
    assert summary["formal_gcn_training"] is False
    assert summary["reranker_retrained"] is False
    assert summary["simulink_run"] is False
    assert summary["labels_exported"] is False
    assert summary["model_saved"] is False
    assert summary["total_candidate_rows"] == 79
    assert summary["num_total_bus_fault_candidates"] == 39
    assert summary["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["forbidden_features_absent_from_gcn_inputs"] is True
    assert summary["proposed_no_leakage_gcn_input_columns"] == [
        "fault_type",
        "duration_s",
        "fault_start_s",
        "fault_clear_s",
        "trip_implementation",
        "line_id",
        "target_bus",
        "target_bus_or_component",
        "source_model_type",
    ]
    assert summary["target_bus_memorization_risk_flagged"] is True
    assert summary["strict_holdouts_complete"] is True
    assert summary["required_strict_holdouts"] == [
        "random_candidate_split_baseline",
        "label_family_holdout",
        "bus_fault_holdout",
        "leave_one_bus_fault_out",
        "no_dynamic_measurement_leave_one_bus_fault_out",
        "existing_vs_new_bus_fault_holdout",
        "nf06_provenance_sensitivity",
        "l12_exclusion_check",
    ]
    assert summary["baseline_comparison_complete"] is True
    assert "Ridge Regression" in summary["baseline_models"]
    assert "target-bus-only baseline" in summary["baseline_models"]
    assert summary["b1_special_tracking_enabled"] is True
    assert summary["nf06_sensitivity_enabled"] is True
    assert summary["l12_exclusion_check_enabled"] is True
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["l12_excluded"] is True
    assert summary["nf06_provenance_warning_preserved"] is True
    assert summary["dry_run_validator_passed"] is True
    assert summary["failed_checks"] == []
    assert summary["should_run_formal_gcn_audit_now"] is False
    assert summary["should_train_gcn_now"] is False
    assert summary["recommended_next_step"].startswith("prepare formal GCN usefulness audit execution")
    assert manifest["forbidden_features_detected_in_inputs"] == []
    assert manifest["target_bus_memorization_risk_flagged"] is True
    assert "dynamic_stress_score" not in manifest["proposed_no_leakage_gcn_input_columns"]
    assert "unstable_flag" not in manifest["proposed_no_leakage_gcn_input_columns"]
    for forbidden in ["min_voltage_pu", "max_frequency_hz", "max_speed_deviation", "max_rotor_angle_separation_deg"]:
        assert forbidden not in manifest["proposed_no_leakage_gcn_input_columns"]
    assert draft["draft_scope"] == "execution_draft_only"
    assert draft["execute_this_round"] is False


def test_dry_run_docs_are_conservative() -> None:
    text = "\n".join([_read_text(SUMMARY_MD), _read_text(ROUND_DOC), _read_text(ROOT / "docs/gcn_pio_validation_log.md")]).lower()
    normalized = " ".join(text.replace("`", "").split())
    current_text = "\n".join([_read_text(SUMMARY_MD), _read_text(ROUND_DOC)]).lower()
    current_normalized = " ".join(current_text.replace("`", "").split())
    for required in [
        "does not train gcn",
        "does not run the formal gcn usefulness audit",
        "does not run simulink",
        "does not export labels",
        "strict holdouts",
        "target_bus",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn was trained",
        "formal gcn audit was run",
        "final gcn conclusion",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_normalized
