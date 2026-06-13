from __future__ import annotations

from pathlib import Path


def test_batch_per_line_clean_breaker_lab_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_per_line_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_clean_breaker_lab_workflow.md",
    ]
    for doc in docs:
        assert doc.exists()
        text = doc.read_text(encoding="utf-8").lower()
        for required in [
            "num_training_ready_labels = 7",
            "one",
            ".slx",
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "not engineering-grade",
            "allowed_for_dynamic_aware_training = false",
        ]:
            assert required in text
        for forbidden in [
            "emt validation completed",
            "engineering-grade protection completed",
            "train the dynamic-aware reranker now",
            "proceed to train dynamic-aware reranker",
        ]:
            assert forbidden not in text

    batch_doc = docs[0].read_text(encoding="utf-8").lower()
    for required in ["l06", "l07", "l08", "grid/b14 to b15", "grid/b15 to b16", "grid/b16 to b17"]:
        assert required in batch_doc
    assert "do not invent a block path" in batch_doc
    assert "sequential or simultaneous multi-line trip experiments" in batch_doc
    assert "must not be mixed into single-line labels" in batch_doc

