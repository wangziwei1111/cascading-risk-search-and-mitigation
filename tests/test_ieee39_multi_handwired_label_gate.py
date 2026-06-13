from __future__ import annotations

import json
from pathlib import Path


def test_multi_handwired_label_gate_counts_unique_lines_and_blocks_training() -> None:
    root = Path(__file__).resolve().parents[1]
    quality = json.loads((root / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json").read_text())
    assert quality["num_training_ready_labels"] == 12
    assert quality["num_training_ready_handwired_line_trip_labels"] == 10
    assert quality["num_training_ready_handwired_line_trip_labels_by_line"] == {
        "L01": 1,
        "L02": 1,
        "L03": 1,
        "L04": 1,
        "L05": 1,
        "L06": 1,
        "L07": 1,
        "L08": 1,
        "L09": 1,
        "L10": 1,
    }
    assert quality["num_unique_handwired_line_ids"] == 10
    assert quality["num_unique_training_ready_fault_types"] >= 3
    assert quality["allowed_for_dynamic_aware_training"] is True
