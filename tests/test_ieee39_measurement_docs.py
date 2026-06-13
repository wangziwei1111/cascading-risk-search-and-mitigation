from __future__ import annotations

from pathlib import Path


def test_ieee39_round29_measurement_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    doc = root / "docs/ieee39_measurement_extraction_and_timed_trip.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8").lower()

    for required in [
        "generator_speed_proxy",
        "not a direct frequency measurement",
        "static topology disable is not a timed breaker",
        "allowed_for_dynamic_aware_training = true",
        "preview dynamic-aware reranker training can run in a separate commit",
        "phasor_rms",
        "not emt",
        "not engineering-grade protection",
    ]:
        assert required in text

    forbidden = [
        "emt validation completed",
        "engineering-grade protection completed",
        "train the dynamic-aware reranker now",
        "proceed to train dynamic-aware reranker",
    ]
    for phrase in forbidden:
        assert phrase not in text
