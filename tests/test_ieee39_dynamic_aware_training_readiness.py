from __future__ import annotations

import json
from pathlib import Path


def test_ieee39_dynamic_aware_training_readiness_summary() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["num_training_ready_labels"] == 10
    assert payload["num_training_ready_handwired_line_trip_labels"] == 8
    assert payload["num_unique_handwired_line_ids"] == 8
    assert payload["allowed_for_dynamic_aware_training"] is True
    assert payload["ready_for_preview_training"] is True
    assert payload["next_step"] == "Run preview dynamic-aware reranker training in a separate commit."
    caveats = " ".join(payload["caveats"]).lower()
    for required in [
        "phasor_rms, not emt",
        "generator_speed_proxy, not direct frequency",
        "pilot breaker-like validation, not engineering-grade protection",
        "preview only, not final dynamic performance conclusion",
    ]:
        assert required in caveats
