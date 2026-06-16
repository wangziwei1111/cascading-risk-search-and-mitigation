import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution"
SUMMARY_JSON = OUT_DIR / "gcn_usefulness_audit_execution_summary.json"
SUMMARY_MD = OUT_DIR / "gcn_usefulness_audit_execution_summary.md"
SUMMARY_CSV = OUT_DIR / "gcn_usefulness_audit_execution_summary.csv"
DOC = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"
FORBIDDEN_JSON = OUT_DIR / "forbidden_feature_audit_report.json"
FORBIDDEN_MD = OUT_DIR / "forbidden_feature_audit_report.md"
COMPARE_JSON = OUT_DIR / "baseline_vs_gcn_comparison.json"
COMPARE_MD = OUT_DIR / "baseline_vs_gcn_comparison.md"
B1_JSON = OUT_DIR / "b1_special_tracking_report.json"
B1_MD = OUT_DIR / "b1_special_tracking_report.md"
NF06_JSON = OUT_DIR / "nf06_sensitivity_report.json"
NF06_MD = OUT_DIR / "nf06_sensitivity_report.md"
L12_JSON = OUT_DIR / "l12_exclusion_confirmation.json"
L12_MD = OUT_DIR / "l12_exclusion_confirmation.md"


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


def test_audit_execution_runs_and_writes_artifacts() -> None:
    subprocess.run(
        ["python", "scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py"],
        cwd=ROOT,
        text=True,
        check=True,
    )
    required = [
        SUMMARY_JSON,
        SUMMARY_MD,
        SUMMARY_CSV,
        DOC,
        FORBIDDEN_JSON,
        FORBIDDEN_MD,
        COMPARE_JSON,
        COMPARE_MD,
        B1_JSON,
        B1_MD,
        NF06_JSON,
        NF06_MD,
        L12_JSON,
        L12_MD,
    ]
    for path in required:
        assert os.path.exists(_long(path)), path.name


def test_audit_execution_summary_fields() -> None:
    summary = _read_json(SUMMARY_JSON)
    assert summary["audit_scope"] == "formal_gcn_usefulness_audit_execution"
    assert summary["audit_only"] is True
    assert summary["production_model_saved"] is False
    assert summary["simulink_run"] is False
    assert summary["actual_smoke_run"] is False
    assert summary["labels_exported"] is False
    assert summary["reranker_retrained"] is False
    assert summary["rl_mitigation_touched"] is False
    assert summary["total_candidate_rows"] == 79
    assert summary["num_total_bus_fault_candidates"] == 39
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["no_leakage_feature_policy_passed"] is True
    assert "bus_fault_holdout" in summary["strict_holdouts_executed"]
    assert "leave_one_bus_fault_out" in summary["strict_holdouts_executed"]
    assert "no_dynamic_measurement_leave_one_bus_fault_out" in summary["strict_holdouts_executed"]
    assert summary["baseline_comparison_executed"] is True
    assert summary["b1_special_tracking_enabled"] is True
    assert summary["nf06_provenance_warning_preserved"] is True
    assert summary["l12_excluded"] is True
    assert summary["final_engineering_conclusion"] is False
    assert summary["should_retrain_reranker_now"] is False
    assert summary["should_deploy_model"] is False
    assert summary["gcn_dependency_status"] != ""


def test_audit_execution_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(SUMMARY_MD),
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    current = "\n".join([_read_text(SUMMARY_MD), _read_text(DOC)]).lower()
    current_normalized = " ".join(current.replace("`", "").split())
    for required in [
        "formal gcn usefulness audit execution",
        "audit-only",
        "did not run simulink",
        "did not export labels",
        "did not retrain the reranker",
        "did not modify rl mitigation",
        "no-leakage features",
        "target_bus memorization risk",
        "b1",
        "nf06",
        "l12",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
    ]:
        assert required in normalized
    for forbidden in [
        "final gcn conclusion",
        "production model saved",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_normalized
