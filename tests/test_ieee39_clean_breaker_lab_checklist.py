from __future__ import annotations

from pathlib import Path


def test_clean_breaker_lab_checklist_mentions_paths_and_rules() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_checklist.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8").lower()
    required = [
        "ieee39bussystem_dynamic_experiment_wrapper_clean_breaker_lab.slx",
        "ieee39bussystem_dynamic_experiment_wrapper_handwired_breaker.slx",
        "line_id: l02",
        "b10 to b11",
        "l02_handwiredtimedbreaker",
        "l02_tripcommand",
        "do not commit any .slx",
        "do not leave a bypass path",
        "initial value = 0",
        "final value = 1",
    ]
    for term in required:
        assert term in text
