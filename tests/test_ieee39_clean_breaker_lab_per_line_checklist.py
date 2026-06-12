from __future__ import annotations

from pathlib import Path


def test_per_line_clean_breaker_lab_checklist_points_to_l03_only() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/clean_breaker_lab_per_line_checklist.txt"
    assert path.exists()
    text = path.read_text(encoding="utf-8").lower()
    for required in [
        "clean lab l02 has already passed",
        "do not keep adding l03/l04 breakers into the same clean lab",
        "simultaneous trip",
        "single-line l03 label",
        "one independent clean lab .slx per line",
        "ieee39bussystem_dynamic_experiment_wrapper_clean_breaker_lab_l03.slx",
        "line_id: l03",
        "line block path: grid/b10 to b13",
        "breaker name: l03_handwiredtimedbreaker",
        "trip command name: l03_tripcommand",
        "l03_tripcommand must control only l03_handwiredtimedbreaker",
        "do not commit any .slx",
    ]:
        assert required in text
