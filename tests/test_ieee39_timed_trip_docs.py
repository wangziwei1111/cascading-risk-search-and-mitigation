from __future__ import annotations

from pathlib import Path


def test_ieee39_timed_trip_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs/ieee39_timed_line_trip_probe_status.md",
        root / "docs/ieee39_timed_breaker_manual_wiring_guide.md",
    ]
    for doc in docs:
        assert doc.exists()
        text = doc.read_text(encoding="utf-8").lower()
        for required in [
            "manual_required",
            "static_topology_disable",
            "not a timed breaker",
            "generator_speed_proxy",
            "not a direct frequency",
            "phasor_rms",
            "not emt",
            "not engineering-grade",
        ]:
            assert required in text
        for forbidden in [
            "static_topology_disable is a timed breaker",
            "engineering-grade protection completed",
            "emt validation completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            assert forbidden not in text
