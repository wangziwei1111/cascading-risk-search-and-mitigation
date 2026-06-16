import json
import os
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "batch_bus_fault_expansion_all_remaining/candidate_label_export"
)
DOC_PATH = ROOT / "docs/ieee39_all_remaining_bus_fault_candidate_label_export.md"
ALL_NEW_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39)), "B16"]


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def _read_json(name: str) -> dict:
    with open(_long(EXPORT_DIR / name), encoding="utf-8") as handle:
        return json.load(handle)


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def test_candidate_export_files_exist() -> None:
    for bus in ALL_NEW_BUSES:
        assert _exists(EXPORT_DIR / f"candidate_label_{bus}.json"), bus
        assert _exists(EXPORT_DIR / f"candidate_label_{bus}.csv"), bus
    for name in [
        "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv",
        "batch_candidate_label_export_summary.json",
        "batch_candidate_label_export_summary.md",
        "batch_candidate_label_export_summary.csv",
        "v2_plus_all_bus_fault_training_readiness.json",
        "all_bus_fault_candidate_coverage_report.json",
        "all_bus_fault_candidate_coverage_report.md",
    ]:
        assert _exists(EXPORT_DIR / name), name
    assert _exists(DOC_PATH)


def test_export_summary_counts_and_boundaries() -> None:
    summary = _read_json("batch_candidate_label_export_summary.json")
    assert summary["export_scope"] == "candidate_only"
    assert summary["previous_candidate_count"] == 42
    assert summary["num_new_all_remaining_bus_fault_candidates"] == 37
    assert summary["num_v2_plus_all_bus_fault_candidate_labels"] == 79
    assert summary["num_total_bus_fault_candidates"] == 39
    assert summary["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert summary["unstable_flag_false_buses"] == ["B1"]
    assert summary["formal_label_gate_changed"] is False
    assert summary["old_formal_gate"] == "35 / 33 / 33"
    assert summary["gcn_trained"] is False
    assert summary["reranker_retrained"] is False
    assert summary["gcn_usefulness_audit_run"] is False
    assert summary["should_train_now"] is False
    assert summary["l12_excluded"] is True
    assert summary["nf06_provenance_warning_preserved"] is True


def test_each_new_candidate_has_required_fields() -> None:
    for bus in ALL_NEW_BUSES:
        payload = _read_json(f"candidate_label_{bus}.json")
        assert payload["scenario_id"] == f"BF_{bus}_TEMP_SMOKE"
        assert payload["label_id_v2"] == f"{bus.lower()}_bus_fault_candidate_001"
        assert payload["label_family"] == "non_line_trip"
        assert payload["fault_type"] == "three_phase_bus_fault_temp_smoke"
        assert payload["target_bus"] == bus
        assert payload["target_bus_or_component"] == bus
        assert payload["line_id"] == "NO_LINE"
        assert payload["trip_implementation"] == "temporary_bus_fault"
        assert payload["simulation_mode"] == "graphical_simulink_phasor_RMS"
        assert payload["selected_fault_block_path"] == f"Grid/Fault_{bus}_TEMP"
        assert _as_bool(payload["simulation_success"])
        assert _as_bool(payload["physical_fault_or_breaker_action_executed"])
        assert payload["measurement_extraction_status"] == "voltage_speed_angle"
        assert _as_bool(payload["quality_review_passed_for_candidate_export"])
        assert _as_bool(payload["training_ready_label_candidate"])
        assert _as_bool(payload["training_ready_label_v2"])
        assert not _as_bool(payload["formal_line_trip_label"])
        assert not _as_bool(payload["handwired_line_trip_label"])
        assert _as_bool(payload["non_line_trip_label"])
        assert _as_bool(payload["bus_fault_label"])
        assert _as_bool(payload["temporary_smoke_candidate"])
        assert _as_bool(payload["candidate_not_formal_label"])
        assert "frequency=generator_speed_proxy" in payload["signal_source_summary"]
        assert payload["labels_exported_this_round"] == "candidate_only"
        assert payload["gcn_trained"] is False
        assert payload["reranker_retrained"] is False
        assert payload["gcn_usefulness_audit_run"] is False
        assert payload["old_formal_gate"] == "35 / 33 / 33"


def test_combined_dataset_has_all_bus_fault_candidates() -> None:
    combined = pd.read_csv(_long(EXPORT_DIR / "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"))
    assert len(combined) == 79
    bus_fault = combined[combined["bus_fault_label"].map(_as_bool)].copy()
    assert len(bus_fault) == 39
    assert set(bus_fault["target_bus"].astype(str)) == {f"B{i}" for i in range(1, 40)}
    assert bus_fault["line_id"].astype(str).eq("NO_LINE").all()
    assert bus_fault["target_bus"].astype(str).ne("").all()
    assert bus_fault["target_bus_or_component"].astype(str).ne("").all()
    assert bus_fault["candidate_not_formal_label"].map(_as_bool).all()


def test_training_readiness_and_coverage_are_future_only() -> None:
    readiness = _read_json("v2_plus_all_bus_fault_training_readiness.json")
    coverage = _read_json("all_bus_fault_candidate_coverage_report.json")
    assert readiness["ready_for_future_preview_training"] is True
    assert readiness["should_train_now"] is False
    assert readiness["candidate_count"] == 79
    assert readiness["num_bus_fault_candidates"] == 39
    assert readiness["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert readiness["b39_b26_existing_candidates_preserved"] is True
    assert readiness["new_all_remaining_bus_fault_candidates"] == 37
    assert coverage["num_expected_buses"] == 39
    assert coverage["num_covered_buses"] == 39
    assert coverage["missing_buses"] == []
    assert coverage["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert coverage["candidate_not_formal_label_for_all"] is True


def test_candidate_export_docs_do_not_overstate_result() -> None:
    doc_paths = [
        DOC_PATH,
        ROOT / "docs/gcn_pio_validation_log.md",
        ROOT / "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md",
        ROOT / "docs/ieee39_all_remaining_bus_fault_batch_actual_smoke.md",
        ROOT / "docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md",
        ROOT / "docs/ieee39_v2_plus_b39_b26_no_training_composition_review.md",
    ]
    text = "\n".join(Path(path).read_text(encoding="utf-8").lower() for path in doc_paths if _exists(path))
    current_text = "\n".join(
        Path(path).read_text(encoding="utf-8").lower()
        for path in [DOC_PATH, EXPORT_DIR / "batch_candidate_label_export_summary.md"]
        if _exists(path)
    )
    for required in [
        "candidate-only export",
        "did not run simulink",
        "did not run actual smoke",
        "did not train gcn",
        "did not retrain the reranker",
        "did not run a gcn usefulness audit",
        "candidate_not_formal_label",
        "not formal labels",
        "35 / 33 / 33",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
        "target-feature leakage",
        "no-training composition review",
    ]:
        assert required in text
    for forbidden in [
        "this round ran simulink",
        "this round ran actual smoke",
        "gcn was trained",
        "gcn usefulness audit was run",
        "bus-fault labels are formal labels",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
            assert forbidden not in current_text


def test_no_forbidden_result_artifacts_tracked_for_all_bus_fault_export() -> None:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/candidate_label_export",
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
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden_tokens)]
