from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
STRESS_SMOKE = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_120_smoke500"


def test_stress_smoke_has_required_mechanism_fields():
    table = pd.read_csv(STRESS_SMOKE / "ieee118_fulltruth_summary.csv")

    required = {
        "max_event_loading_ratio",
        "max_pre_redispatch_loading_ratio",
        "num_relay_trips",
        "relay_trip_labels",
        "num_passive_outages",
        "has_overload_cascade",
        "critical_mechanism",
    }
    assert required.issubset(table.columns)
    assert len(table) == 500
    assert (table["critical_mechanism"] == "relay_cascade").any()


def test_stress_smoke_audit_counts_relay_and_island_mechanisms():
    summary = pd.read_json(STRESS_SMOKE / "ieee118_fulltruth_audit_summary.json", typ="series")

    assert int(summary["total_paths"]) == 500
    assert int(summary["critical_paths"]) > 0
    assert int(summary["relay_cascade_paths"]) > 0
    assert int(summary["island_only_paths"]) >= 0
    assert "mixed_paths" in summary
