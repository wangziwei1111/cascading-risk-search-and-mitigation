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


def test_ieee39_quality_summary_counts_measurement_availability(tmp_path: Path) -> None:
    summary = tmp_path / "fault_summary.csv"
    pd.DataFrame(
        [
            {
                "test_case": "three_phase_fault_clear",
                "physical_fault_or_breaker_action_executed": True,
                "schema_only": False,
                "training_ready_candidate": True,
                "min_voltage_pu": 0.82,
                "min_frequency_hz": 49.8,
                "max_speed_deviation": 0.02,
                "max_rotor_angle_separation_deg": 50.0,
            },
            {
                "test_case": "single_line_trip",
                "physical_fault_or_breaker_action_executed": False,
                "schema_only": False,
                "training_ready_candidate": False,
                "min_voltage_pu": float("nan"),
                "min_frequency_hz": float("nan"),
                "max_speed_deviation": float("nan"),
                "max_rotor_angle_separation_deg": float("nan"),
            },
        ]
    ).to_csv(summary, index=False)

    result = export_ieee39_dynamic_labels(summary, output_dir=tmp_path / "labels")
    quality = json.loads(Path(result["quality_json"]).read_text(encoding="utf-8"))
    assert quality["num_labels_with_voltage_measurement"] == 1
    assert quality["num_labels_with_frequency_measurement"] == 1
    assert quality["num_labels_with_speed_measurement"] == 1
    assert quality["num_labels_with_rotor_angle_measurement"] == 1
    assert quality["measurement_quality_status"] == "partial_dynamic_measurements"
    assert quality["allowed_for_dynamic_aware_training"] is False
