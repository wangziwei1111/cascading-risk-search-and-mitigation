import csv
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
OUT = BASE / "batch_smoke_outputs"
SUMMARY_JSON = OUT / "batch_actual_smoke_summary.json"
SUMMARY_MD = OUT / "batch_actual_smoke_summary.md"
SUMMARY_CSV = OUT / "batch_actual_smoke_summary.csv"
QUALITY_JSON = OUT / "buses_ready_for_smoke_quality_review.json"
DOC = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md"

NORMAL_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
ALL_BUSES = NORMAL_BUSES + ["B16"]


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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(_long(path), encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _is_true(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _finite(value) -> bool:
    return math.isfinite(float(value))


def test_batch_actual_smoke_artifacts_exist() -> None:
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert SUMMARY_CSV.exists()
    assert QUALITY_JSON.exists()
    assert DOC.exists()
    for bus in ALL_BUSES:
        assert (OUT / f"batch_smoke_{bus}_summary.csv").exists(), bus
        assert (OUT / f"batch_smoke_{bus}_report.json").exists(), bus
        assert (OUT / f"batch_smoke_{bus}_report.md").exists(), bus


def test_batch_actual_smoke_summary_boundaries() -> None:
    summary = _read_json(SUMMARY_JSON)
    assert summary["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert summary["smoke_scope"] == "actual_temporary_smoke_only"
    assert summary["total_targets"] == 37
    assert summary["num_smoke_attempted"] == 37
    assert summary["actual_simulink_run"] is True
    assert summary["dry_run"] is False
    assert summary["labels_exported"] is False
    assert summary["candidate_labels_exported"] is False
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False
    assert summary["gcn_usefulness_audit_run"] is False
    assert summary["should_export_labels_now"] is False
    assert summary["should_train_now"] is False
    assert summary["current_candidate_count"] == 42
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["num_smoke_attempted"] == (
        summary["num_simulation_success"] + summary["num_simulation_failed"] + summary["num_timeout"]
    )
    assert set(summary["successful_buses"] + summary["failed_buses"] + summary["timeout_buses"]) == set(ALL_BUSES)
    assert summary["special_b16_smoke_status"] == "voltage_speed_angle"


def test_each_per_bus_report_preserves_label_boundaries() -> None:
    for bus in ALL_BUSES:
        report = _read_json(OUT / f"batch_smoke_{bus}_report.json")
        assert report["batch_id"] == "bus_fault_all_remaining_manual_wiring"
        assert report["target_bus"] == bus
        assert report["scenario_id"] == f"BF_{bus}_TEMP_SMOKE"
        assert report["actual_simulink_run"] is True
        assert report["dry_run"] is False
        assert report["smoke_executed"] is True
        assert report["source_slx_modified"] is False
        assert report["temporary_slx_committed"] is False
        assert report["labels_exported"] is False
        assert report["candidate_label_exported"] is False
        assert report["gcn_trained"] is False
        assert report["reranker_retrained"] is False
        assert report["gcn_usefulness_audit_run"] is False
        assert report["selected_fault_block_path"] == f"Grid/Fault_{bus}_TEMP"
        if report["simulation_success"]:
            assert report["measurement_extraction_status"] == "voltage_speed_angle"
            assert report["physical_fault_or_breaker_action_executed"] is True
            assert "frequency=generator_speed_proxy" in report["signal_source_summary"]
            for key in [
                "min_voltage_pu",
                "max_voltage_pu",
                "min_frequency_hz",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
            ]:
                assert _finite(report[key]), (bus, key, report[key])
        if bus == "B16":
            assert report["special_handling"] is True


def test_per_bus_summary_csv_matches_report() -> None:
    for bus in ALL_BUSES:
        rows = _read_csv(OUT / f"batch_smoke_{bus}_summary.csv")
        assert len(rows) == 1
        row = rows[0]
        report = _read_json(OUT / f"batch_smoke_{bus}_report.json")
        assert row["scenario_id"] == report["scenario_id"]
        assert _is_true(row["actual_simulink_run"]) is report["actual_simulink_run"]
        assert _is_true(row["labels_exported"]) is False
        assert _is_true(row["candidate_label_exported"]) is False


def test_quality_review_candidate_list_is_plan_only() -> None:
    summary = _read_json(SUMMARY_JSON)
    quality = _read_json(QUALITY_JSON)
    assert quality["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert quality["ready_for_quality_review_buses"] == summary["successful_buses"]
    assert quality["blocked_from_quality_review_buses"] == summary["failed_buses"] + summary["timeout_buses"]
    assert quality["ready_count"] == len(summary["successful_buses"])
    assert quality["blocked_count"] == len(summary["failed_buses"]) + len(summary["timeout_buses"])
    assert quality["should_run_quality_review_now"] is False
    assert quality["should_export_labels_now"] is False
    assert quality["should_train_now"] is False
    assert quality["criteria"]["measurement_extraction_status"] == "voltage_speed_angle"


def test_batch_actual_smoke_docs_are_conservative() -> None:
    actual_smoke_text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
        ]
    ).lower()
    text = "\n".join(
        [
            actual_smoke_text,
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    actual_normalized = " ".join(actual_smoke_text.replace("`", "").split())
    for required in [
        "actual simulink smoke was run",
        "did not export labels",
        "did not train gcn",
        "did not run a gcn usefulness audit",
        "not candidate labels",
        "temporary smoke evidence",
        "smoke quality review",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "37 new targets are candidate labels",
        "labels were exported",
        "gcn was trained",
        "gcn usefulness audit was run",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
            assert forbidden not in actual_normalized


def test_no_forbidden_large_artifacts_are_tracked_for_batch_smoke() -> None:
    result = subprocess.run(
        ["git", "ls-files", str(OUT.relative_to(ROOT)).replace("\\", "/")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden = [
        ".slx",
        ".slxc",
        ".mat",
        "slprj",
        "raw_trajector",
        "full_timeseries",
        "local_lab_copies",
        "_matlab_stdout",
        "_matlab_batch_smoke",
        "ieee39_simlog_tree_inventory",
        "ieee39_signal_extraction_debug",
    ]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden)]
    assert bad == []
