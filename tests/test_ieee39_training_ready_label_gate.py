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


def test_ieee39_quality_gate_allows_partial_but_blocks_training(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    pd.DataFrame(
        [
            {"test_case": "no_fault_sanity", "simulation_success": True, "physical_fault_or_breaker_action_executed": False, "schema_only": False, "training_ready_candidate": False},
            {"test_case": "three_phase_fault_clear", "simulation_success": True, "physical_fault_or_breaker_action_executed": True, "schema_only": False, "training_ready_candidate": True, "fault_type": "three_phase_fault_clear"},
            {"test_case": "single_line_trip", "simulation_success": True, "physical_fault_or_breaker_action_executed": False, "schema_only": False, "training_ready_candidate": False, "trip_implementation": "static_topology_disable"},
        ]
    ).to_csv(summary, index=False)
    result = export_ieee39_dynamic_labels(summary, output_dir=tmp_path / "labels")
    quality = json.loads(Path(result["quality_json"]).read_text(encoding="utf-8"))
    labels = pd.read_csv(result["preview_csv"])
    assert quality["label_quality_status"] == "partial_physical_execution"
    assert quality["allowed_for_dynamic_aware_training"] is False
    assert len(labels) == 1
    assert labels.iloc[0]["path"] == "three_phase_fault_clear"
