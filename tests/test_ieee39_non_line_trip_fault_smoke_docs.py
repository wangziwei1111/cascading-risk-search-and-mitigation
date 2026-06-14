from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").lower()


def test_smoke_doc_boundaries() -> None:
    text = _read("docs/ieee39_non_line_trip_fault_smoke_tests.md")
    for required in [
        "nf01",
        "nf02",
        "nf03",
        "nf04",
        "nf06",
        "`nf07-nf10` remain `manual_required`",
        "did not modify `.slx`",
        "did not fix l12",
        "did not update the formal training-ready label count",
        "did not retrain the dynamic-aware reranker",
        "smoke-test success is not a formal merge into training-ready dynamic labels",
        "phasor_rms, not emt",
        "generator_speed_proxy` is not direct frequency",
        "relay proxy is not engineering-grade protection",
    ]:
        assert required in text


def test_smoke_docs_do_not_overclaim_or_merge_labels() -> None:
    docs = [
        "docs/ieee39_non_line_trip_fault_smoke_tests.md",
        "docs/ieee39_non_line_trip_fault_type_expansion.md",
        "docs/gcn_pio_validation_log.md",
        "docs/ieee39_measurement_extraction_and_timed_trip.md",
        "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
    ]
    for rel in docs:
        text = _read(rel)
        assert "non-line-trip" in text, rel
        for bad in [
            "merged into training-ready labels",
            "merged into formal dynamic labels",
            "emt validation completed",
            "is a direct frequency measurement",
            "engineering-grade protection completed",
            "is a final dynamic performance conclusion",
        ]:
            assert bad not in text, f"{rel} contains overclaim: {bad}"


def test_smoke_doc_forbidden_artifact_policy() -> None:
    text = _read("docs/ieee39_non_line_trip_fault_smoke_tests.md")
    for required in [".slx", ".slxc", "slprj", ".mat", "raw trajectories", "full\n  timeseries"]:
        assert required in text
    assert "do not commit `.slx`" in text
