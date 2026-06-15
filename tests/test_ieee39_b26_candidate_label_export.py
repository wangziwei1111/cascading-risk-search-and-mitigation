import json
import math
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export"
)
DOC_PATH = ROOT / "docs/ieee39_b26_bus_fault_candidate_label_export.md"


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _candidate_payload():
    return json.loads((EXPORT_DIR / "ieee39_b26_bus_fault_dynamic_label_candidate.json").read_text())


def test_b26_candidate_export_files_exist():
    for name in [
        "ieee39_b26_bus_fault_dynamic_label_candidate.csv",
        "ieee39_b26_bus_fault_dynamic_label_candidate.json",
        "ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv",
        "ieee39_b26_bus_fault_candidate_export_summary.json",
        "ieee39_b26_bus_fault_candidate_export_summary.md",
        "ieee39_v2_plus_b39_b26_training_readiness.json",
    ]:
        path = EXPORT_DIR / name
        assert path.exists(), name
        assert path.stat().st_size > 0, name
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_b26_candidate_identity_and_measurement_fields():
    payload = _candidate_payload()
    assert payload["scenario_id"] == "BF_B26_TEMP_SMOKE"
    assert payload["target_bus"] == "B26"
    assert payload["target_bus_or_component"] == "B26"
    assert payload["line_id"] == "NO_LINE"
    assert payload["fault_type"] == "three_phase_bus_fault_temp_smoke"
    assert payload["label_family"] == "non_line_trip"
    assert _as_bool(payload["simulation_success"])
    assert _as_bool(payload["physical_fault_or_breaker_action_executed"])
    assert payload["measurement_extraction_status"] == "voltage_speed_angle"
    assert "frequency=generator_speed_proxy" in payload["signal_source_summary"]
    assert _as_bool(payload["quality_review_passed_for_candidate_export"])
    assert math.isclose(float(payload["dynamic_stress_score"]), 0.5314759474846006)


def test_b26_candidate_is_candidate_only_not_formal_label():
    payload = _candidate_payload()
    assert _as_bool(payload["training_ready_label_candidate"])
    assert _as_bool(payload["training_ready_label_v2"])
    assert not _as_bool(payload["formal_line_trip_label"])
    assert not _as_bool(payload["handwired_line_trip_label"])
    assert _as_bool(payload["non_line_trip_label"])
    assert _as_bool(payload["bus_fault_label"])
    assert _as_bool(payload["temporary_smoke_candidate"])
    assert _as_bool(payload["candidate_not_formal_label"])
    assert payload["labels_exported_this_round"] == "candidate_only"
    assert payload["b39_status"] == "candidate_label_not_formal"
    assert _as_bool(payload["l12_excluded"])
    assert _as_bool(payload["nf06_provenance_warning_preserved"])


def test_b26_plus_v2_counts_and_training_readiness_are_preserved():
    combined = pd.read_csv(EXPORT_DIR / "ieee39_dynamic_label_schema_v2_plus_b39_b26_candidate.csv")
    summary = json.loads((EXPORT_DIR / "ieee39_b26_bus_fault_candidate_export_summary.json").read_text())
    readiness = json.loads((EXPORT_DIR / "ieee39_v2_plus_b39_b26_training_readiness.json").read_text())
    assert len(combined) == 42
    assert int((combined["scenario_id"].astype(str) == "BF_B26_TEMP_SMOKE").sum()) == 1
    assert int((combined["scenario_id"].astype(str) == "BF_B39_TEMP_SMOKE").sum()) == 1
    b26 = combined.loc[combined["scenario_id"].astype(str) == "BF_B26_TEMP_SMOKE"].iloc[0]
    b39 = combined.loc[combined["scenario_id"].astype(str) == "BF_B39_TEMP_SMOKE"].iloc[0]
    for row, bus in [(b26, "B26"), (b39, "B39")]:
        assert row["target_bus"] == bus
        assert row["target_bus_or_component"] == bus
        assert row["line_id"] == "NO_LINE"
        assert row["fault_type"] == "three_phase_bus_fault_temp_smoke"
        assert _as_bool(row["bus_fault_label"])
        assert _as_bool(row["candidate_not_formal_label"])
    assert summary["previous_v2_plus_b39_count"] == 41
    assert summary["num_new_b26_bus_fault_candidates"] == 1
    assert summary["num_v2_plus_b39_b26_candidate_labels"] == 42
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False
    assert summary["should_train_now"] is False
    assert readiness["ready_for_future_preview_training"] is True
    assert readiness["should_train_now"] is False
    assert readiness["candidate_count"] == 42
    assert readiness["num_bus_fault_candidates"] == 2
    assert readiness["b39_candidate_present"] is True
    assert readiness["b26_candidate_present"] is True


def test_b26_candidate_docs_do_not_overstate_result():
    doc_paths = [
        DOC_PATH,
        ROOT / "docs/ieee39_b26_temp_smoke_quality_review.md",
        ROOT / "docs/ieee39_b26_temporary_bus_fault_smoke.md",
        ROOT / "docs/ieee39_v2_plus_b39_no_training_composition_review.md",
        ROOT / "docs/ieee39_v2_plus_b39_preview_interpretation.md",
        ROOT / "docs/gcn_pio_validation_log.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in doc_paths)
    for required in [
        "candidate_only",
        "b26 is a candidate label, not a formal label",
        "b39",
        "candidate label, not a formal label",
        "does not run simulink",
        "does not train gcn",
        "does not retrain",
        "gcn usefulness audit",
        "35 / 33 / 33",
        "42",
        "l12",
        "nf06",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
        "no-training composition review",
    ]:
        assert required in text
    forbidden = [
        "b26 is a formal label",
        "b26 formal label exported",
        "gcn trained: `true`",
        "reranker retrained: `true`",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade protection completed",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_no_forbidden_result_artifacts_tracked_for_b26_export():
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export",
        ],
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
        "local_lab_copies",
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden_tokens)]
