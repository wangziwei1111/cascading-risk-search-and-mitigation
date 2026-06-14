from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").lower()


def test_non_line_trip_expansion_doc_boundaries() -> None:
    text = _read("docs/ieee39_non_line_trip_fault_type_expansion.md")
    for required in [
        "does not create new training-ready labels",
        "did not run simulink",
        "no `.slx` file was modified",
        "l12 was not fixed",
        "no dynamic-aware reranker retraining",
        "phasor_rms, not emt",
        "generator_speed_proxy` is not direct frequency",
        "not engineering-grade protection",
        "target-feature leakage",
    ]:
        assert required in text
    for bad in [
        "new training-ready labels were added",
        "emt validation completed",
        "direct frequency measurement",
        "engineering-grade protection completed",
        "final dynamic stability conclusion",
    ]:
        assert bad not in text


def test_related_docs_reference_non_line_trip_boundaries() -> None:
    docs = [
        "docs/gcn_pio_validation_log.md",
        "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
        "docs/ieee39_dynamic_aware_reranker_preview_training.md",
        "docs/ieee39_measurement_extraction_and_timed_trip.md",
        "docs/ieee39_l12_islanding_timeout_case.md",
    ]
    for rel in docs:
        text = _read(rel)
        assert "non-line-trip" in text, rel
        assert "not a final dynamic performance conclusion" in text or "not a new dynamic stability conclusion" in text or "not a final dynamic performance conclusion" in _read("docs/ieee39_non_line_trip_fault_type_expansion.md")


def test_docs_do_not_require_committing_large_simulink_artifacts() -> None:
    text = _read("docs/ieee39_non_line_trip_fault_type_expansion.md")
    for required in [".slx", ".mat", "raw trajectories", "full timeseries"]:
        assert required in text
    assert "do not commit `.slx`" in text
    assert "do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, full" in text
