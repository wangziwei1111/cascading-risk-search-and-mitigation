from __future__ import annotations

from pathlib import Path


def test_batch_clean_breaker_lab_checklist_is_single_line_per_model() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_batch_checklist.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8").lower()
    for required in [
        "clean lab l02",
        "per-line clean lab l03",
        "num_training_ready_labels = 7",
        "line_id: l04",
        "line block path: grid/b11 to b6",
        "l04_handwiredtimedbreaker",
        "l04_tripcommand",
        "line_id: l05",
        "line block path: grid/b13 to b14",
        "l05_handwiredtimedbreaker",
        "l05_tripcommand",
        "one line uses one .slx",
        "do not wire l05 inside the l04 .slx",
        "not_in_current_line_map",
        "do not commit .slx",
    ]:
        assert required in text
    for forbidden in [
        "train the dynamic-aware reranker now",
        "engineering-grade protection completed",
        "emt validation completed",
    ]:
        assert forbidden not in text

