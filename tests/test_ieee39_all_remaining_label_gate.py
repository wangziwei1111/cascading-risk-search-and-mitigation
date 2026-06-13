from __future__ import annotations

import json
from pathlib import Path


def test_all_remaining_label_gate_counts_expanded_successful_lines_only() -> None:
    root = Path(__file__).resolve().parents[1]
    quality = json.loads((root / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json").read_text())
    readiness = json.loads((root / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json").read_text())
    expected_by_line = {f"L{i:02d}": 1 for i in range(1, 35) if i != 12}

    assert quality["num_training_ready_labels"] == 35
    assert quality["num_training_ready_handwired_line_trip_labels"] == 33
    assert quality["num_unique_handwired_line_ids"] == 33
    assert quality["num_training_ready_handwired_line_trip_labels_by_line"] == expected_by_line
    assert "L12" not in quality["num_training_ready_handwired_line_trip_labels_by_line"]
    assert quality["allowed_for_dynamic_aware_training"] is True
    assert readiness["num_training_ready_labels"] == 35
    assert readiness["num_training_ready_handwired_line_trip_labels"] == 33
    assert readiness["num_unique_handwired_line_ids"] == 33
    assert readiness["ready_for_preview_training"] is True
    assert "do not retrain" in readiness["next_step"].lower()
