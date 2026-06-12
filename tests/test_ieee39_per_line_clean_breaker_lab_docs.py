from __future__ import annotations

from pathlib import Path


def test_per_line_clean_breaker_lab_docs_separate_single_line_and_sequence_cases() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs/ieee39_per_line_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_multi_handwired_breaker_expansion.md",
    ]
    for doc in docs:
        assert doc.exists()
        text = doc.read_text(encoding="utf-8").lower()
        for required in [
            "single-line",
            "l03",
            "clean_breaker_lab_l03.slx",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade",
        ]:
            assert required in text
        for forbidden in [
            "emt validation completed",
            "engineering-grade protection completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            assert forbidden not in text

    per_line = docs[0].read_text(encoding="utf-8").lower()
    assert "multi-line cascading trip sequence" in per_line
    assert "must not be mixed into single-line label collection" in per_line
    assert "allowed_for_dynamic_aware_training = false" in per_line
