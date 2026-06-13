from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_batch_clean_breaker_lab_prepare_summary_contains_l06_l07_l08() -> None:
    root = Path(__file__).resolve().parents[1]
    csv_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_prepare_summary.csv"
    json_path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_prepare_summary.json"
    assert csv_path.exists()
    assert json_path.exists()
    table = pd.read_csv(csv_path)
    required = {
        "line_id",
        "line_block_path",
        "target_clean_lab_path",
        "source_found",
        "target_created",
        "target_loadable",
        "existing_handwired_breaker_found",
        "clean_lab_committed",
        "status",
        "note",
    }
    assert required.issubset(table.columns)
    assert set(table["line_id"].astype(str)) == {"L06", "L07", "L08"}
    for line_id, line_path in {
        "L06": "Grid/B14 to B15",
        "L07": "Grid/B15 to B16",
        "L08": "Grid/B16 to B17",
    }.items():
        row = table[table["line_id"].astype(str) == line_id].iloc[0]
        assert line_path in row["line_block_path"]
        assert row["target_clean_lab_path"].endswith(f"IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx")
        assert str(row["source_found"]).lower() in {"1", "true"}
        assert str(row["target_created"]).lower() in {"1", "true"}
        assert str(row["target_loadable"]).lower() in {"1", "true"}
        assert str(row["existing_handwired_breaker_found"]).lower() in {"0", "false"}
        assert str(row["clean_lab_committed"]).lower() in {"0", "false"}
        assert row["status"] == "prepared"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(payload) == 3
