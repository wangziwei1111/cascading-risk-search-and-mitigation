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


def test_ieee39_label_gate_accepts_handwired_timed_breaker_but_blocks_training(tmp_path: Path) -> None:
    summary = tmp_path / "fault_summary.csv"
    pd.DataFrame(
        [
            {
                "test_case": "single_line_trip",
                "fault_type": "pilot_line_trip",
                "simulation_success": True,
                "schema_only": False,
                "physical_fault_or_breaker_action_executed": True,
                "training_ready_candidate": True,
                "trip_implementation": "handwired_timed_breaker",
                "min_voltage_pu": 0.95,
                "min_frequency_hz": 49.9,
                "max_speed_deviation": 0.01,
                "max_rotor_angle_separation_deg": 40.0,
            }
        ]
    ).to_csv(summary, index=False)

    result = export_ieee39_dynamic_labels(summary, output_dir=tmp_path / "labels")
    labels = pd.read_csv(result["preview_csv"])
    quality = json.loads(Path(result["quality_json"]).read_text(encoding="utf-8"))

    assert len(labels) == 1
    assert quality["num_training_ready_handwired_line_trip_labels"] == 1
    assert quality["num_training_ready_labels"] == 1
    assert quality["allowed_for_dynamic_aware_training"] is False
