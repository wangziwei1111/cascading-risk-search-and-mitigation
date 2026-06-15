import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export"
)
DOC_PATH = ROOT / "docs/ieee39_b39_bus_fault_candidate_label_export.md"


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _candidate_payload():
    return json.loads((EXPORT_DIR / "ieee39_b39_bus_fault_dynamic_label_candidate.json").read_text())


def test_b39_candidate_files_exist():
    for name in [
        "ieee39_b39_bus_fault_dynamic_label_candidate.csv",
        "ieee39_b39_bus_fault_dynamic_label_candidate.json",
        "ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv",
        "ieee39_dynamic_label_quality_summary_v2_plus_b39_candidate.json",
        "ieee39_dynamic_aware_training_readiness_v2_plus_b39_candidate.json",
        "ieee39_b39_candidate_duplicate_provenance_report.md",
    ]:
        path = EXPORT_DIR / name
        assert path.exists(), name
        assert path.stat().st_size > 0, name


def test_b39_candidate_identity_and_measurement_fields():
    payload = _candidate_payload()
    assert payload["scenario_id"] == "BF_B39_TEMP_SMOKE"
    assert payload["target_bus"] == "B39"
    assert payload["target_bus_or_component"] == "B39"
    assert payload["fault_type"] == "three_phase_bus_fault_temp_smoke"
    assert payload["line_id"] == "NO_LINE"
    assert _as_bool(payload["simulation_success"])
    assert _as_bool(payload["physical_fault_or_breaker_action_executed"])
    assert payload["measurement_extraction_status"] == "voltage_speed_angle"
    assert "frequency=generator_speed_proxy" in payload["signal_source_summary"]
    assert _as_bool(payload["quality_review_passed_for_candidate_export"])


def test_b39_candidate_is_not_formal_line_trip_label():
    payload = _candidate_payload()
    assert _as_bool(payload["training_ready_label_candidate"])
    assert not _as_bool(payload["formal_line_trip_label"])
    assert not _as_bool(payload["handwired_line_trip_label"])
    assert _as_bool(payload["non_line_trip_label"])
    assert _as_bool(payload["bus_fault_label"])
    assert _as_bool(payload["candidate_not_formal_label"])
    assert payload["export_status"] == "candidate_only"
    assert "not GCN training" in payload["note"]
    assert "not reranker retraining" in payload["note"]


def test_b39_plus_v2_counts_and_quality_gate_are_preserved():
    combined = pd.read_csv(EXPORT_DIR / "ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv")
    quality = json.loads(
        (EXPORT_DIR / "ieee39_dynamic_label_quality_summary_v2_plus_b39_candidate.json").read_text()
    )
    readiness = json.loads(
        (EXPORT_DIR / "ieee39_dynamic_aware_training_readiness_v2_plus_b39_candidate.json").read_text()
    )
    assert len(combined) == 41
    assert int((combined["scenario_id"].astype(str) == "BF_B39_TEMP_SMOKE").sum()) == 1
    b39 = combined.loc[combined["scenario_id"].astype(str) == "BF_B39_TEMP_SMOKE"].iloc[0]
    assert b39["target_bus"] == "B39"
    assert b39["target_bus_or_component"] == "B39"
    assert b39["line_id"] == "NO_LINE"
    assert b39["fault_type"] == "three_phase_bus_fault_temp_smoke"
    assert _as_bool(b39["bus_fault_label"])
    assert _as_bool(b39["candidate_not_formal_label"])
    assert quality["previous_v2_candidate_count"] == 40
    assert quality["num_v2_plus_b39_candidate_labels"] == 41
    assert quality["original_num_training_ready_labels"] == 35
    assert quality["original_num_training_ready_handwired_line_trip_labels"] == 33
    assert quality["original_num_unique_handwired_line_ids"] == 33
    assert quality["l12_excluded"] is True
    assert quality["nf06_provenance_warning_preserved"] is True
    assert quality["gcn_trained"] is False
    assert quality["reranker_retrained"] is False
    assert readiness["should_train_now"] is False


def test_b39_candidate_docs_do_not_overstate_result():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    assert "does not run simulink" in text
    assert "does not train gcn" in text
    assert "does not retrain" in text
    assert "not yet a formal dynamic label" in text
    assert "phasor_rms`, not emt" in text
    assert "generator_speed_proxy` is not direct frequency" in text
    assert "not engineering-grade protection" in text
    forbidden = [
        "gcn trained: `true`",
        "reranker retrained: `true`",
        "final dynamic performance conclusion",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_b39_provenance_report_preserves_nf06_and_l12_warnings():
    text = (EXPORT_DIR / "ieee39_b39_candidate_duplicate_provenance_report.md").read_text(
        encoding="utf-8"
    ).lower()
    assert "no exact duplicate" in text
    assert "nf06 warning preserved" in text
    assert "l12 excluded" in text


def test_no_forbidden_result_artifacts_tracked_for_b39_export():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden_tokens = [
        ".pt",
        ".npz",
        ".slx",
        ".slxc",
        ".mat",
        "slprj",
        "full_truth",
        "simulation_results",
        "raw_trajectories",
        "full_timeseries",
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden_tokens)]
