from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/non_line_trip_label_export"


def test_combined_schema_v2_files_exist() -> None:
    for name in [
        "ieee39_dynamic_label_schema_v2_combined_candidates.csv",
        "ieee39_dynamic_label_schema_v2_combined_candidates.json",
        "ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json",
        "ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json",
    ]:
        path = OUT / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_combined_schema_v2_counts_and_families() -> None:
    table = pd.read_csv(OUT / "ieee39_dynamic_label_schema_v2_combined_candidates.csv")
    assert len(table) == 40
    assert table["training_ready_label_v2"].astype(bool).all()
    assert int(table["non_line_trip_label"].astype(bool).sum()) == 5
    assert int(table["handwired_line_trip_label"].astype(bool).sum()) == 33
    assert set(table.loc[table["non_line_trip_label"].astype(bool), "scenario_id"].astype(str)) == {
        "NF01",
        "NF02",
        "NF03",
        "NF04",
        "NF06",
    }
    assert "l12" not in table.to_json().lower()


def test_v2_quality_summary_and_readiness_preserve_original_gate() -> None:
    quality = json.loads((OUT / "ieee39_dynamic_label_quality_summary_v2_with_non_line_trip_candidates.json").read_text(encoding="utf-8"))
    readiness = json.loads((OUT / "ieee39_dynamic_aware_training_readiness_v2_with_non_line_trip_candidates.json").read_text(encoding="utf-8"))
    assert quality["schema_version"] == "ieee39_dynamic_label_schema_v2"
    assert quality["original_formal_gate_preserved"] is True
    assert quality["original_num_training_ready_labels"] == 35
    assert quality["original_num_training_ready_handwired_line_trip_labels"] == 33
    assert quality["original_num_unique_handwired_line_ids"] == 33
    assert quality["num_non_line_trip_candidate_labels"] == 5
    assert quality["num_training_ready_labels_v2_combined_candidate"] == 40
    assert quality["l12_excluded"] is True
    assert quality["should_retrain_reranker_now"] is False
    assert quality["provenance_check_required_scenarios"] == ["NF06"]
    assert readiness["ready_for_v2_preview_training"] is True
    assert readiness["should_train_now"] is False
    caveats = " ".join(readiness["caveats"]).lower()
    assert "phasor_rms, not emt" in caveats
    assert "generator_speed_proxy, not direct frequency" in caveats
    assert "not engineering-grade protection" in caveats


def test_original_formal_gate_files_unchanged_values() -> None:
    quality = json.loads((ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json").read_text(encoding="utf-8"))
    readiness = json.loads((ROOT / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json").read_text(encoding="utf-8"))
    assert quality["num_training_ready_labels"] == 35
    assert quality["num_training_ready_handwired_line_trip_labels"] == 33
    assert quality["num_unique_handwired_line_ids"] == 33
    assert readiness["num_training_ready_labels"] == 35
    assert readiness["num_training_ready_handwired_line_trip_labels"] == 33
    assert readiness["num_unique_handwired_line_ids"] == 33
