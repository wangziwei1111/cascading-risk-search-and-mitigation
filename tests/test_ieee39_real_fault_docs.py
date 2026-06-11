from __future__ import annotations

from pathlib import Path


def test_ieee39_real_fault_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    doc = (root / "docs/ieee39_real_fault_execution_status.md").read_text(encoding="utf-8").lower()
    assert "partial_physical_execution" in doc
    assert "allowed_for_dynamic_aware_training = false" in doc
    assert "static topology disable is not a timed breaker" in doc
    assert "not emt" in doc
    assert "not engineering-grade protection" in doc
    assert "not full opf dynamic simulation" in doc
    for phrase in [
        "emt validation completed",
        "engineering-grade protection completed",
        "train the dynamic-aware reranker now",
    ]:
        assert phrase not in doc
