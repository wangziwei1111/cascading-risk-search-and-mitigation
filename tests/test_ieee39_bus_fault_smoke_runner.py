from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"


def test_bus_fault_runner_and_summary_artifacts_exist() -> None:
    assert (ROOT / "scripts/gcn_search/run_ieee39_bus_fault_smoke_tests.py").exists()
    for name in [
        "ieee39_bus_fault_smoke_test_summary.csv",
        "ieee39_bus_fault_smoke_test_summary.json",
        "ieee39_bus_fault_smoke_test_report.json",
        "ieee39_bus_fault_smoke_test_report.md",
    ]:
        path = OUT / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_bus_fault_summary_fields_and_boundaries() -> None:
    table = pd.read_csv(OUT / "ieee39_bus_fault_smoke_test_summary.csv")
    assert set(table["scenario_id"].astype(str)) == {"BF01", "BF02", "BF03", "BF04"}
    assert "L12" not in table.to_json().lower()
    assert not table["source_slx_modified"].astype(bool).any()
    assert not table["simulation_success"].astype(bool).any()
    assert not table["physical_fault_or_breaker_action_executed"].astype(bool).any()
    assert not table["training_ready_candidate_smoke"].astype(bool).any()
    assert table["measurement_extraction_status"].eq("not_runnable_until_bus_injection_verified").all()

    successful = table[table["training_ready_candidate_smoke"].astype(bool)]
    if not successful.empty:
        assert successful["measurement_extraction_status"].eq("voltage_speed_angle").all()
        assert successful["signal_source_summary"].str.contains("frequency=generator_speed_proxy", regex=False).all()


def test_bus_fault_report_counts_and_no_gate_change() -> None:
    report = json.loads((OUT / "ieee39_bus_fault_smoke_test_report.json").read_text(encoding="utf-8"))
    assert report["scenario_ids_requested"] == ["BF01", "BF02", "BF03", "BF04"]
    assert report["scenario_ids_runnable"] == []
    assert report["scenario_ids_successful"] == []
    assert report["scenario_ids_timeout"] == []
    assert report["num_successful_bus_fault_smoke_candidates"] == 0
    assert report["whether_source_slx_modified"] is False
    assert report["whether_formal_label_gate_changed"] is False
    assert report["whether_reranker_retrained"] is False
    assert report["whether_gcn_trained"] is False
    assert report["whether_l12_touched"] is False
    assert report["old_formal_gate"] == "35 / 33 / 33"
    assert report["v2_candidate_count_unchanged"] == 40


def test_bus_fault_summary_json_matches_csv_ids() -> None:
    with (OUT / "ieee39_bus_fault_smoke_test_summary.csv").open(encoding="utf-8-sig", newline="") as f:
        csv_ids = [row["scenario_id"] for row in csv.DictReader(f)]
    payload = json.loads((OUT / "ieee39_bus_fault_smoke_test_summary.json").read_text(encoding="utf-8"))
    assert [row["scenario_id"] for row in payload] == csv_ids

