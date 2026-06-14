from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


DOCS = [
    "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md",
    "docs/gcn_pio_validation_log.md",
    "docs/ieee39_non_line_trip_label_export.md",
    "docs/ieee39_non_line_trip_fault_smoke_tests.md",
    "docs/ieee39_dynamic_aware_reranker_preview_training.md",
    "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
]


def test_v2_preview_docs_record_boundaries_and_counts() -> None:
    for rel_path in DOCS:
        text = (ROOT / rel_path).read_text(encoding="utf-8").lower()
        for required in [
            "preview",
            "35 / 33 / 33",
            "40",
            "39",
            "nf06",
            "not a final dynamic performance conclusion",
        ]:
            assert required in text, f"{rel_path} missing {required}"


def test_v2_preview_docs_do_not_overclaim_dynamic_fidelity() -> None:
    joined = "\n".join((ROOT / rel_path).read_text(encoding="utf-8").lower() for rel_path in DOCS)
    for required in [
        "phasor_rms, not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in joined
    for forbidden in [
        "emt validation completed",
        "is direct frequency measurement",
        "engineering-grade protection completed",
        "production ready",
        "is a final dynamic performance conclusion",
    ]:
        assert forbidden not in joined


def test_v2_preview_docs_record_no_simulink_or_slx_change() -> None:
    doc = (ROOT / "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md").read_text(encoding="utf-8").lower()
    for required in [
        "does not run simulink",
        "does not modify `.slx`",
        "does not fix l12",
        "does not overwrite the old formal gate",
        "final_performance_conclusion = false",
    ]:
        assert required in doc
