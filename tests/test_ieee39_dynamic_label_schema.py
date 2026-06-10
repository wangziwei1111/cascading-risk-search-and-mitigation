from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from export_ieee39_dynamic_labels import export_ieee39_dynamic_labels


def test_ieee39_dynamic_label_schema(tmp_path: Path) -> None:
    summary_csv = tmp_path / "ieee39_fault_test_summary.csv"
    event_csv = tmp_path / "ieee39_event_log.csv"
    pd.DataFrame(
        [
            {
                "test_case": "ordered_N2_trip",
                "unstable_flag": True,
                "tripped_line": "L01->L02",
                "min_frequency_hz": 49.0,
                "min_voltage_pu": 0.85,
                "max_rotor_angle_separation_deg": 210.0,
                "max_speed_deviation": 0.1,
            }
        ]
    ).to_csv(summary_csv, index=False)
    pd.DataFrame(
        [
            {"test_case": "ordered_N2_trip", "event_type": "relay_trip"},
            {"test_case": "ordered_N2_trip", "event_type": "breaker_open"},
        ]
    ).to_csv(event_csv, index=False)

    result = export_ieee39_dynamic_labels(summary_csv, event_csv, output_dir=tmp_path / "labels")
    labels = pd.read_csv(result["preview_csv"])
    schema = json.loads(Path(result["schema_json"]).read_text(encoding="utf-8"))
    required = {
        "path",
        "first_line",
        "second_line",
        "dynamic_unstable",
        "dynamic_stress_score",
        "min_frequency_hz",
        "min_voltage_pu",
        "max_rotor_angle_separation_deg",
        "relay_trip_count",
        "breaker_trip_count",
    }
    assert required.issubset(labels.columns)
    assert required.issubset(schema["columns"].keys())
    assert labels.loc[0, "first_line"] == "L01"
    assert labels.loc[0, "second_line"] == "L02"
    assert labels.loc[0, "dynamic_stress_score"] > 0
