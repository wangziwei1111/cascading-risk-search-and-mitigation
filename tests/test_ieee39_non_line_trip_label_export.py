from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export"
EXPECTED = {"NF01", "NF02", "NF03", "NF04", "NF06"}


def test_export_script_and_candidate_files_exist() -> None:
    assert (ROOT / "scripts/gcn_search/export_ieee39_non_line_trip_dynamic_labels.py").exists()
    for name in [
        "ieee39_non_line_trip_dynamic_label_candidates.csv",
        "ieee39_non_line_trip_dynamic_label_candidates.json",
        "ieee39_non_line_trip_duplicate_provenance_report.json",
        "ieee39_non_line_trip_duplicate_provenance_report.md",
    ]:
        path = OUT / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_non_line_trip_candidate_rows_and_flags() -> None:
    table = pd.read_csv(OUT / "ieee39_non_line_trip_dynamic_label_candidates.csv")
    assert len(table) == 5
    assert set(table["scenario_id"].astype(str)) == EXPECTED
    assert table["label_family"].eq("non_line_trip").all()
    assert table["non_line_trip_label"].astype(bool).all()
    assert not table["handwired_line_trip_label"].astype(bool).any()
    assert not table["formal_line_trip_label"].astype(bool).any()
    assert table["training_ready_label_v2"].astype(bool).all()
    assert table["measurement_extraction_status"].eq("voltage_speed_angle").all()
    assert table["signal_source_summary"].str.contains("frequency=generator_speed_proxy", regex=False).all()
    assert "l12" not in table.to_json().lower()


def test_nf06_requires_provenance_check() -> None:
    table = pd.read_csv(OUT / "ieee39_non_line_trip_dynamic_label_candidates.csv")
    nf06 = table.loc[table["scenario_id"].astype(str).eq("NF06")].iloc[0]
    assert bool(nf06["provenance_check_required"])
    assert bool(nf06["not_independent_physical_sample_until_verified"])
    assert str(nf06["duplicate_measurement_group"]) == "group_1"


def test_duplicate_provenance_report_includes_nf01_nf04_nf06() -> None:
    report = json.loads((OUT / "ieee39_non_line_trip_duplicate_provenance_report.json").read_text(encoding="utf-8"))
    assert report["num_duplicate_measurement_groups"] >= 1
    joined = json.dumps(report).lower()
    for scenario_id in ["nf01", "nf04", "nf06"]:
        assert scenario_id in joined
    assert report["provenance_check_required_scenarios"] == ["NF06"]
    assert report["rows_deleted_due_to_duplicates"] == 0
