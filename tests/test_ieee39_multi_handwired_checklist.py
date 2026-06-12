from __future__ import annotations

from pathlib import Path


def test_multi_handwired_checklist_exists_and_names_lines() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/multi_handwired_breaker_checklist.txt"
    text = path.read_text(encoding="utf-8")
    for token in ["L02_HandwiredTimedBreaker", "L03_TripCommand", "L04", "must not be committed"]:
        assert token in text
    assert "phasor_RMS" in text
    assert "not EMT" in text
