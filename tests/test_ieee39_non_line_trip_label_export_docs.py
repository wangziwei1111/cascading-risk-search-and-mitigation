from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").lower()


def test_label_export_doc_required_claims() -> None:
    text = _read("docs/ieee39_non_line_trip_label_export.md")
    for required in [
        "did not run simulink",
        "did not modify `.slx`",
        "did not fix l12",
        "did not retrain",
        "35 / 33 / 33",
        "non-line-trip candidate labels: `5`",
        "v2 combined candidate rows: `40`",
        "nf01",
        "nf04",
        "nf06",
        "provenance_check_required = true",
        "non-line-trip labels and handwired line-trip labels are counted separately",
        "phasor_rms, not emt",
        "generator_speed_proxy` is not direct frequency",
        "relay proxy is not engineering-grade protection",
    ]:
        assert required in text


def test_related_docs_mention_v2_export_without_overclaim() -> None:
    docs = [
        "docs/gcn_pio_validation_log.md",
        "docs/ieee39_non_line_trip_fault_smoke_tests.md",
        "docs/ieee39_non_line_trip_fault_type_expansion.md",
        "docs/ieee39_dynamic_aware_reranker_preview_training.md",
        "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
    ]
    for rel in docs:
        text = _read(rel)
        assert "v2" in text, rel
        assert "40" in text, rel
        assert "provenance" in text, rel
        for bad in [
            "reranker was retrained",
            "retrained the dynamic-aware reranker",
            "emt validation completed",
            "is a direct frequency measurement",
            "engineering-grade protection completed",
            "is a final dynamic performance conclusion",
        ]:
            assert bad not in text, f"{rel} contains overclaim: {bad}"


def test_label_export_doc_artifact_policy() -> None:
    text = _read("docs/ieee39_non_line_trip_label_export.md")
    for required in [".slx", "phasor_rms", "generator_speed_proxy", "not final dynamic performance conclusion"]:
        assert required in text
