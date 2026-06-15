from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"


def test_bus_fault_audit_script_and_artifacts_exist() -> None:
    assert (ROOT / "scripts/gcn_search/audit_ieee39_bus_fault_injection_points.py").exists()
    for name in [
        "ieee39_bus_fault_injection_feasibility.json",
        "ieee39_bus_fault_injection_feasibility.md",
        "ieee39_bus_fault_smoke_scenario_manifest.csv",
        "ieee39_bus_fault_smoke_scenario_manifest.json",
    ]:
        path = OUT / name
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_bus_fault_manifest_schema_unique_no_l12_no_line_trip() -> None:
    with (OUT / "ieee39_bus_fault_smoke_scenario_manifest.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert 2 <= len(rows) <= 4
    scenario_ids = [row["scenario_id"] for row in rows]
    assert len(scenario_ids) == len(set(scenario_ids))
    assert {"BF01", "BF02"}.issubset(set(scenario_ids))
    text = json.dumps(rows).lower()
    assert "l12" not in text
    assert "handwired" not in text
    assert "single_line_trip" not in text
    for row in rows:
        assert row["fault_type"] == "three_phase_bus_fault_smoke"
        assert row["requires_source_slx_modification"] == "False"
        assert row["runnable_now"] in {"True", "False"}
        assert row["target_bus"].startswith("B")


def test_bus_fault_feasibility_preserves_label_boundaries() -> None:
    report = json.loads((OUT / "ieee39_bus_fault_injection_feasibility.json").read_text(encoding="utf-8"))
    assert report["simulink_was_run"] is False
    assert report["source_slx_modified"] is False
    assert report["formal_label_gate_changed"] is False
    assert report["reranker_retrained"] is False
    assert report["gcn_trained"] is False
    assert report["l12_touched"] is False
    assert report["old_formal_gate"] == "35 / 33 / 33"
    assert report["v2_candidate_count_unchanged"] == 40
    assert report["capabilities"]["target_bus_selector_supported"] is False

