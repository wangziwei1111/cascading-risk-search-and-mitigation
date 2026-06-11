from __future__ import annotations

from pathlib import Path


def test_ieee39_handwired_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs/ieee39_handwired_breaker_validation.md",
        root / "docs/ieee39_timed_breaker_manual_wiring_guide.md",
        root / "docs/ieee39_timed_line_trip_probe_status.md",
    ]
    for doc in docs:
        assert doc.exists()
        text = doc.read_text(encoding="utf-8").lower()
        for required in [
            "handwired",
            "must not be committed",
            "pilot",
            "not engineering-grade",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
        ]:
            assert required in text
        for forbidden in [
            "engineering-grade protection completed",
            "emt validation completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            assert forbidden not in text
