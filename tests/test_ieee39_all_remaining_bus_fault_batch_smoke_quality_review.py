import csv
import json
import math
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
QUALITY = BASE / "batch_smoke_quality_review"
SUMMARY_JSON = QUALITY / "batch_smoke_quality_review_summary.json"
SUMMARY_MD = QUALITY / "batch_smoke_quality_review_summary.md"
SUMMARY_CSV = QUALITY / "batch_smoke_quality_review_summary.csv"
ELIGIBLE_JSON = QUALITY / "buses_eligible_for_candidate_export.json"
DOC = ROOT / "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md"

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


def _finite(value) -> bool:
    return math.isfinite(float(value))


def test_quality_review_artifacts_exist() -> None:
    assert SUMMARY_JSON.exists()
    assert SUMMARY_MD.exists()
    assert SUMMARY_CSV.exists()
    assert ELIGIBLE_JSON.exists()
    assert DOC.exists()
    for bus in ALL_BUSES:
        assert (QUALITY / f"smoke_quality_review_{bus}.json").exists(), bus
        assert (QUALITY / f"smoke_quality_review_{bus}.md").exists(), bus


def test_quality_review_summary_boundaries() -> None:
    summary = _read_json(SUMMARY_JSON)
    assert summary["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert summary["quality_review_scope"] == "smoke_output_quality_only"
    assert summary["total_smoke_reports_reviewed"] == 37
    assert summary["num_quality_review_passed"] + summary["num_quality_review_failed"] == 37
    assert summary["actual_simulink_run_this_round"] is False
    assert summary["smoke_was_run_in_previous_round"] is True
    assert summary["labels_exported"] is False
    assert summary["candidate_labels_exported"] is False
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False
    assert summary["gcn_usefulness_audit_run"] is False
    assert summary["should_export_labels_now"] is False
    assert summary["should_train_now"] is False
    assert summary["current_candidate_count"] == 42
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["measurement_extraction_status_counts"] == {"voltage_speed_angle": 37}
    assert set(summary["quality_review_passed_buses"] + summary["quality_review_failed_buses"]) == set(ALL_BUSES)


def test_each_quality_review_record_is_conservative_and_finite() -> None:
    for bus in ALL_BUSES:
        review = _read_json(QUALITY / f"smoke_quality_review_{bus}.json")
        assert review["batch_id"] == "bus_fault_all_remaining_manual_wiring"
        assert review["target_bus"] == bus
        assert review["scenario_id"] == f"BF_{bus}_TEMP_SMOKE"
        assert review["quality_review_scope"] == "smoke_output_quality_only"
        assert review["actual_simulink_run_this_round"] is False
        assert review["smoke_was_run_in_previous_round"] is True
        assert review["labels_exported"] is False
        assert review["candidate_label_exported"] is False
        assert review["gcn_trained"] is False
        assert review["reranker_retrained"] is False
        assert review["gcn_usefulness_audit_run"] is False
        assert review["source_slx_modified"] is False
        assert review["temporary_slx_committed"] is False
        assert review["selected_fault_block_path"] == f"Grid/Fault_{bus}_TEMP"
        if review["simulation_success"]:
            assert review["measurement_extraction_status"] == "voltage_speed_angle"
            assert review["metrics_all_finite"] is True
            assert review["signal_source_has_frequency_proxy"] is True
            assert review["compact_dynamic_measurement_available"] is True
            for key in [
                "min_voltage_pu",
                "max_voltage_pu",
                "min_frequency_hz",
                "max_frequency_hz",
                "max_speed_deviation",
                "max_rotor_angle_separation_deg",
            ]:
                assert _finite(review[key]), (bus, key, review[key])
        if bus == "B16":
            assert review["special_handling"] is True
            assert review["b16_old_fault_not_moved"] is True


def test_eligible_list_is_next_round_only() -> None:
    summary = _read_json(SUMMARY_JSON)
    eligible = _read_json(ELIGIBLE_JSON)
    assert eligible["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert eligible["eligible_buses"] == summary["candidate_export_eligible_buses"]
    assert eligible["blocked_buses"] == summary["candidate_export_blocked_buses"]
    assert eligible["eligible_count"] == len(eligible["eligible_buses"])
    assert eligible["blocked_count"] == len(eligible["blocked_buses"])
    assert eligible["should_export_labels_now"] is False
    assert eligible["should_train_now"] is False
    assert eligible["next_round_export_scope"] == "candidate_only"
    assert eligible["criteria"]["quality_review_passed_for_candidate_export"] is True
    assert eligible["criteria"]["measurement_extraction_status"] == "voltage_speed_angle"


def test_quality_review_csv_matches_summary() -> None:
    rows = _read_csv(SUMMARY_CSV)
    summary = _read_json(SUMMARY_JSON)
    assert len(rows) == 37
    passed = {row["target_bus"] for row in rows if row["quality_review_passed_for_candidate_export"].lower() == "true"}
    assert passed == set(summary["quality_review_passed_buses"])


def test_quality_review_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    current_doc = "\n".join([_read_text(DOC), _read_text(SUMMARY_MD)]).lower()
    normalized = " ".join(text.replace("`", "").split())
    current_normalized = " ".join(current_doc.replace("`", "").split())
    for required in [
        "did not run simulink",
        "did not run actual smoke",
        "did not export labels",
        "did not train gcn",
        "did not retrain the reranker",
        "did not run a gcn usefulness audit",
        "still not candidate labels",
        "candidate-only export",
        "unstable_flag is a compact smoke threshold marker",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "37 new targets are candidate labels",
        "this round ran simulink",
        "this round ran actual smoke",
        "labels were exported",
        "gcn was trained",
        "gcn usefulness audit was run",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_normalized


def test_no_forbidden_large_artifacts_are_tracked_for_quality_review() -> None:
    result = subprocess.run(
        ["git", "ls-files", str(QUALITY.relative_to(ROOT)).replace("\\", "/")],
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
    ]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden)]
    assert bad == []
