from __future__ import annotations

from pathlib import Path


def test_ieee39_relay_proxy_doc_is_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    doc = root / "docs/ieee39_fault_breaker_relay_wrapper.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8").lower()
    assert "basic relay proxy" in text
    assert "not engineering-grade" in text
    assert "phasor_rms" in text
    assert "pilot" in text
    forbidden = [
        "emt validation completed",
        "engineering-grade protection completed",
        "full protection model completed",
        "allowed for dynamic-aware reranker training: true",
    ]
    for phrase in forbidden:
        assert phrase not in text
