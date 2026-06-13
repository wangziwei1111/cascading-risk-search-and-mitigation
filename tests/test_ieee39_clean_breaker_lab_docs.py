from __future__ import annotations

from pathlib import Path


def test_clean_breaker_lab_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs/ieee39_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_handwired_breaker_validation.md",
        root / "docs/ieee39_multi_handwired_breaker_expansion.md",
    ]
    for doc in docs:
        assert doc.exists()
        text = doc.read_text(encoding="utf-8").lower()
        for required in [
            "clean",
            "l02",
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
            "formal dynamic superiority",
        ]:
            assert forbidden not in text

    clean_doc = (root / "docs/ieee39_clean_breaker_lab_workflow.md").read_text(encoding="utf-8").lower()
    for required in [
        "validation_passed = true",
        "simulation_success = true",
        "training_ready_candidate = true",
        "num_training_ready_labels = 10",
        "allowed_for_dynamic_aware_training = true",
        "preview training",
    ]:
        assert required in clean_doc

