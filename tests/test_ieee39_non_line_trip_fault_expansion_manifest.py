from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion"


def test_non_line_trip_taxonomy_and_reports_exist() -> None:
    for name in [
        "ieee39_non_line_trip_fault_taxonomy.json",
        "ieee39_non_line_trip_fault_taxonomy.md",
        "ieee39_non_line_trip_scenario_manifest.csv",
        "ieee39_non_line_trip_scenario_manifest.json",
        "ieee39_non_line_trip_feasibility_report.json",
        "ieee39_non_line_trip_feasibility_report.md",
    ]:
        path = OUT / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_taxonomy_has_required_fault_types_and_fields() -> None:
    taxonomy = json.loads((OUT / "ieee39_non_line_trip_fault_taxonomy.json").read_text(encoding="utf-8"))
    required_types = {
        "three_phase_bus_fault_clear",
        "fault_duration_sweep",
        "relay_proxy_fault",
        "load_step_disturbance",
        "generator_trip_or_mechanical_power_step",
        "bus_voltage_disturbance_or_reference_event",
    }
    assert required_types.issubset({row["fault_type"] for row in taxonomy})
    for row in taxonomy:
        for key in [
            "fault_type",
            "description",
            "requires_slx_modification",
            "runnable_with_existing_scripts",
            "expected_measurements",
            "expected_training_ready_gate",
            "risks",
            "recommended_first_batch",
        ]:
            assert key in row, f"{row.get('fault_type')} missing {key}"


def test_manifest_schema_unique_no_l12_no_handwired_line_trip() -> None:
    with (OUT / "ieee39_non_line_trip_scenario_manifest.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert 8 <= len(rows) <= 12
    scenario_ids = [row["scenario_id"] for row in rows]
    assert len(scenario_ids) == len(set(scenario_ids))
    text = json.dumps(rows).lower()
    assert "l12" not in text
    assert "handwired_timed_breaker" not in text
    assert "single_line_trip" not in text
    assert any(row["fault_type"] in {"three_phase_bus_fault_clear", "three_phase_fault_clear"} for row in rows)
    assert any(row["fault_type"] == "fault_duration_sweep" for row in rows)
    for row in rows:
        assert row["requires_slx_modification"] in {"True", "False"}
        assert row["runnable_with_existing_scripts"] in {"True", "False"}
        assert row["scenario_id"].startswith("NF")


def test_feasibility_report_preserves_current_label_boundary() -> None:
    report = json.loads((OUT / "ieee39_non_line_trip_feasibility_report.json").read_text(encoding="utf-8"))
    assert report["simulink_was_run"] is False
    assert report["slx_modified"] is False
    assert report["training_ready_label_count_changed"] is False
    assert report["reranker_retrained"] is False
    assert report["mixes_with_handwired_line_trip_labels"] is False
    assert report["target_feature_leakage_possible"] is True
