from __future__ import annotations

from pathlib import Path


def test_remaining_clean_breaker_lab_checklist_lists_l11_l34_and_boundaries() -> None:
    root = Path(__file__).resolve().parents[1]
    path = (
        root
        / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
        / "clean_breaker_lab_batch_checklist.txt"
    )
    assert path.exists()
    text = path.read_text(encoding="utf-8").lower()
    for required in [
        "validated l09/l10 results",
        "remaining prepared-but-unwired clean lab targets",
        "target line ids: l11-l34",
        "line_id: l11",
        "grid/b18 to b17",
        "l11_handwiredtimedbreaker",
        "line_id: l34",
        "grid/b9 to b8",
        "l34_handwiredtimedbreaker",
        "do not retrain the dynamic-aware reranker in this round",
        "does not auto-insert breakers",
        "does not modify simscape physical wiring",
        "do not commit .slx",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
    ]:
        assert required in text
