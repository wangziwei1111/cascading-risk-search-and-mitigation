from __future__ import annotations

from pathlib import Path


def test_batch_clean_breaker_lab_checklist_is_single_line_per_model() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_batch_checklist.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8").lower()
    for required in [
        "l01-l10 are training-ready handwired line-trip labels",
        "validation_passed lines: l11, l12",
        "simulation_success and merged lines: l11, l13",
        "timeout lines: l12",
        "num_training_ready_labels = 35",
        "num_training_ready_handwired_line_trip_labels = 33",
        "num_unique_handwired_line_ids = 33",
        "l12_handwiredtimedbreaker",
        "line block path=grid/b18 to b17",
        "line block path=grid/b9 to b8",
        "recheck l12 first",
        "did not retrain the dynamic-aware reranker",
        "does not auto-insert breakers",
        "does not modify simscape physical wiring",
        "do not commit .slx",
    ]:
        assert required in text
    for forbidden in [
        "train the dynamic-aware reranker now",
        "engineering-grade protection completed",
        "emt validation completed",
    ]:
        assert forbidden not in text

