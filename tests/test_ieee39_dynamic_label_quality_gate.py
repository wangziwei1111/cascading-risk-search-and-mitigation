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


def test_ieee39_label_quality_gate_blocks_schema_only_labels(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    pd.DataFrame(
        [
            {"test_case": "no_fault_sanity", "simulation_success": True, "physical_fault_or_breaker_action_executed": False},
            {"test_case": "schema_trip", "simulation_success": False, "physical_fault_or_breaker_action_executed": False},
        ]
    ).to_csv(summary, index=False)
    result = export_ieee39_dynamic_labels(summary, output_dir=tmp_path / "labels")
    quality = json.loads(Path(result["quality_json"]).read_text(encoding="utf-8"))
    labels = pd.read_csv(result["preview_csv"])
    assert labels.empty
    assert quality["label_quality_status"] == "schema_only"
    assert quality["allowed_for_dynamic_aware_training"] is False


def test_ieee39_label_quality_gate_requires_enough_physical_rows(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    pd.DataFrame(
        [
            {"test_case": f"trip_{i}", "simulation_success": True, "physical_fault_or_breaker_action_executed": True, "tripped_line": f"L{i:02d}"}
            for i in range(3)
        ]
    ).to_csv(summary, index=False)
    result = export_ieee39_dynamic_labels(summary, output_dir=tmp_path / "labels")
    quality = json.loads(Path(result["quality_json"]).read_text(encoding="utf-8"))
    assert quality["num_training_ready_labels"] == 3
    assert quality["label_quality_status"] == "insufficient_physical_fault_rows"
    assert quality["allowed_for_dynamic_aware_training"] is False
