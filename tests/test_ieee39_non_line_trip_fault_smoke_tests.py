from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion"
REQUESTED = {"NF01", "NF02", "NF03", "NF04", "NF06"}


def test_smoke_runner_and_outputs_exist() -> None:
    assert (ROOT / "scripts/gcn_search/run_ieee39_non_line_trip_fault_smoke_tests.py").exists()
    for name in [
        "ieee39_non_line_trip_smoke_test_summary.csv",
        "ieee39_non_line_trip_smoke_test_summary.json",
        "ieee39_non_line_trip_smoke_test_report.json",
        "ieee39_non_line_trip_smoke_test_report.md",
    ]:
        path = OUT / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_smoke_report_requested_and_completed_scenarios() -> None:
    report = json.loads((OUT / "ieee39_non_line_trip_smoke_test_report.json").read_text(encoding="utf-8"))
    assert set(report["scenario_ids_requested"]) == REQUESTED
    assert set(report["scenario_ids_completed"]) == REQUESTED
    assert set(report["scenario_ids_successful"]) == REQUESTED
    assert report["scenario_ids_failed"] == []
    assert report["scenario_ids_timeout"] == []
    assert report["num_successful_smoke_candidates"] == 5
    assert report["whether_formal_label_gate_changed"] is False
    assert report["whether_reranker_retrained"] is False
    assert report["whether_slx_modified"] is False
    assert report["whether_l12_touched"] is False


def test_smoke_summary_schema_and_success_measurements() -> None:
    table = pd.read_csv(OUT / "ieee39_non_line_trip_smoke_test_summary.csv")
    assert set(table["scenario_id"]) == REQUESTED
    text = table.to_json().lower()
    assert "nf07" not in text and "nf08" not in text and "nf09" not in text and "nf10" not in text
    assert "l12" not in text
    assert "handwired" not in text
    required = {
        "scenario_id",
        "fault_type",
        "target_bus_or_component",
        "fault_start_s",
        "fault_clear_s",
        "duration_s",
        "simulation_success",
        "physical_fault_or_breaker_action_executed",
        "measurement_extraction_status",
        "training_ready_candidate_smoke",
        "timeout_or_error_message",
        "min_voltage_pu",
        "max_voltage_pu",
        "min_frequency_hz",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
        "unstable_flag",
        "signal_source_summary",
        "output_summary_path",
        "output_event_log_path",
        "note",
    }
    assert required.issubset(table.columns)
    successful = table[table["training_ready_candidate_smoke"].astype(bool)]
    assert len(successful) == 5
    assert successful["simulation_success"].astype(bool).all()
    assert successful["measurement_extraction_status"].eq("voltage_speed_angle").all()
    assert successful["signal_source_summary"].str.contains("frequency=generator_speed_proxy", regex=False).all()


def test_formal_label_gate_still_unchanged() -> None:
    readiness = json.loads(
        (ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json").read_text(
            encoding="utf-8"
        )
    )
    assert readiness["num_training_ready_labels"] == 35
    assert readiness["num_training_ready_handwired_line_trip_labels"] == 33
    assert readiness["num_unique_handwired_line_ids"] == 33


def test_no_forbidden_simulink_artifacts_tracked_by_smoke_round() -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion"],
        cwd=ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.lower()
    for forbidden in [".slx", ".slxc", "slprj", ".mat", "raw_trajectories", "full_timeseries"]:
        assert forbidden not in tracked
