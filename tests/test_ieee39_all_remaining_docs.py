from __future__ import annotations

from pathlib import Path


def test_all_remaining_docs_are_conservative_and_record_l12_timeout() -> None:
    root = Path(__file__).resolve().parents[1]
    docs = [
        root / "docs/gcn_pio_validation_log.md",
        root / "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_line_map_extension_workflow.md",
        root / "docs/ieee39_dynamic_aware_reranker_preview_training.md",
        root / "docs/ieee39_measurement_extraction_and_timed_trip.md",
        root / "docs/ieee39_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_per_line_clean_breaker_lab_workflow.md",
        root / "docs/ieee39_multi_handwired_breaker_expansion.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8").lower()
        for required in [
            "phasor_rms",
            "not emt",
            "generator_speed_proxy",
            "not direct frequency",
            "pilot breaker-like",
            "not engineering-grade",
        ]:
            assert required in text
        for forbidden in [
            "emt validation completed",
            "engineering-grade protection completed",
            "is a final dynamic performance conclusion",
        ]:
            assert forbidden not in text

    batch_text = (root / "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md").read_text(encoding="utf-8").lower()
    for required in [
        "l11-l34",
        "l12",
        "simulation timeout",
        "num_training_ready_labels = 35",
        "num_training_ready_handwired_line_trip_labels = 33",
        "num_unique_handwired_line_ids = 33",
        "no dynamic-aware reranker training was run",
        ".slx",
    ]:
        assert required in batch_text
