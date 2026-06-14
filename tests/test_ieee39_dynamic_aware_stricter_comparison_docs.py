from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_stricter_comparison_docs_are_conservative() -> None:
    docs = [
        ROOT / "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
        ROOT / "docs/gcn_pio_validation_log.md",
        ROOT / "docs/ieee39_dynamic_aware_reranker_preview_training.md",
        ROOT / "docs/ieee39_l12_islanding_timeout_case.md",
        ROOT / "docs/ieee39_measurement_extraction_and_timed_trip.md",
        ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_summary.md",
        ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_leakage_notes.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8").lower()
        compact = re.sub(r"\s+", " ", text)
        assert "preview" in text
        assert "not a final dynamic performance conclusion" in compact
        assert "l12" in text
        assert "excluded" in text
        assert "phasor_rms" in text
        assert "not emt" in text
        assert "generator_speed_proxy" in text
        assert "not direct frequency" in text
        assert "pilot breaker-like" in text
        assert "not engineering-grade" in text


def test_stricter_comparison_docs_do_not_overclaim() -> None:
    docs = [
        ROOT / "docs/ieee39_dynamic_aware_stricter_independent_test_comparison.md",
        ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_summary.md",
        ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison/stricter_comparison_leakage_notes.md",
    ]
    forbidden = [
        "emt validation completed",
        "is direct frequency",
        "engineering-grade protection completed",
        "final dynamic performance conclusion",
        "must commit `.slx`",
        "must commit `.mat`",
        "raw trajectories are committed",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8").lower()
        compact = re.sub(r"\s+", " ", text)
        for phrase in forbidden:
            if phrase == "final dynamic performance conclusion":
                assert "not a final dynamic performance conclusion" in compact
            else:
                assert phrase not in text
