import csv
import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs"
SUMMARY = OUT_DIR / "ieee39_b26_bus_fault_temp_lab_smoke_summary.csv"
REPORT_JSON = OUT_DIR / "ieee39_b26_bus_fault_temp_lab_smoke_report.json"
REPORT_MD = OUT_DIR / "ieee39_b26_bus_fault_temp_lab_smoke_report.md"
DOC = ROOT / "docs/ieee39_b26_temporary_bus_fault_smoke.md"


def _load_report():
    return json.loads(REPORT_JSON.read_text(encoding="utf-8"))


def _load_summary_row():
    with SUMMARY.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    return rows[0]


def test_b26_smoke_artifacts_exist():
    for path in [SUMMARY, REPORT_JSON, REPORT_MD, DOC]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path


def test_b26_smoke_report_records_actual_run_and_boundaries():
    report = _load_report()
    assert report["target_bus"] == "B26"
    assert report["scenario_id"] == "BF_B26_TEMP_SMOKE"
    assert report["actual_simulink_run"] is True
    assert report["dry_run"] is False
    assert report["human_readiness_used"] is True
    assert report["human_readiness_ready"] is True
    assert report["selected_fault_block_path"] == "Grid/Fault_B26_TEMP"
    assert report["selected_injection_block_path"]
    assert report["source_slx_modified"] is False
    assert report["temporary_slx_committed"] is False
    assert report["labels_exported"] is False
    assert report["gcn_trained"] is False
    assert report["reranker_retrained"] is False
    assert report["formal_label_gate_changed"] is False
    assert report["v2_plus_b39_count_changed"] is False
    assert report["old_formal_gate"] == "35 / 33 / 33"
    assert report["v2_plus_b39_count"] == 41
    assert report["b39_status"] == "candidate_label_not_formal"
    assert report["l12_touched"] is False


def test_b26_smoke_success_measurements_are_real_when_successful():
    report = _load_report()
    if report["simulation_success"]:
        assert report["physical_fault_or_breaker_action_executed"] is True
        assert report["measurement_extraction_status"] == "voltage_speed_angle"
        assert "frequency=generator_speed_proxy" in report["signal_source_summary"]
        for key in [
            "min_voltage_pu",
            "max_voltage_pu",
            "min_frequency_hz",
            "max_frequency_hz",
            "max_speed_deviation",
            "max_rotor_angle_separation_deg",
        ]:
            assert math.isfinite(float(report[key])), key
        assert "review B26 smoke output quality" in report["recommended_next_step"]
    else:
        assert report["smoke_not_run_reason"]
        assert "diagnose" in report["recommended_next_step"].lower()
        assert report["labels_exported"] is False
        assert report["gcn_trained"] is False


def test_b26_smoke_summary_matches_report():
    report = _load_report()
    row = _load_summary_row()
    assert row["scenario_id"] == "BF_B26_TEMP_SMOKE"
    assert row["target_bus"] == "B26"
    assert row["simulation_success"].lower() == str(report["simulation_success"]).lower()
    assert row["physical_fault_or_breaker_action_executed"].lower() == str(
        report["physical_fault_or_breaker_action_executed"]
    ).lower()
    assert row["measurement_extraction_status"] == report["measurement_extraction_status"]
    assert row["source_slx_modified"] == "False"
    assert row["temporary_slx_committed"] == "False"


def test_b26_smoke_docs_do_not_overstate_label_status():
    text = " ".join(
        "\n".join(path.read_text(encoding="utf-8").lower() for path in [REPORT_MD, DOC]).split()
    )
    required = [
        "actual_simulink_run",
        "temporary smoke candidate",
        "not a formal label",
        "no labels exported",
        "no training run",
        "no reranker",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]
    for phrase in required:
        assert phrase in text
    forbidden = [
        "b26 candidate label exported",
        "b26 formal label",
        "gcn trained",
        "reranker retrained",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_no_forbidden_artifacts_tracked_for_b26_actual_smoke():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden = [".slx", ".slxc", "slprj", ".mat", "raw_trajectories", "full_timeseries", "local_lab_copies"]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden)]
