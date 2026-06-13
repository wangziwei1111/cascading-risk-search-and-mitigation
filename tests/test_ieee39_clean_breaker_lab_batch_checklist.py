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
        "validated l09/l10 results",
        "num_training_ready_labels = 12",
        "num_training_ready_handwired_line_trip_labels = 10",
        "num_unique_handwired_line_ids = 10",
        "preview dynamic-aware reranker training already ran earlier as a sanity check",
        "line_id: l09",
        "line block path: grid/b16 to b24",
        "l09_handwiredtimedbreaker",
        "l09_tripcommand",
        "line_id: l10",
        "line block path: grid/b17 to b27",
        "l10_handwiredtimedbreaker",
        "l10_tripcommand",
        "remaining prepared-but-unwired clean lab targets",
        "line_id: l11",
        "line block path: grid/b18 to b17",
        "line_id: l34",
        "line block path: grid/b9 to b8",
        "validate_ieee39_clean_breaker_lab_lines_batch([\"l11\",\"l12\"])",
        "one line uses one .slx",
        "do not wire more than one target breaker inside the same per-line .slx",
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

