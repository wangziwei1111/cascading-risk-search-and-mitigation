from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_l12_docs_keep_timeout_out_of_training_ready_set() -> None:
    docs = [
        ROOT / "docs/ieee39_l12_islanding_timeout_case.md",
        ROOT / "docs/gcn_pio_validation_log.md",
        ROOT / "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md",
        ROOT / "docs/ieee39_line_map_extension_workflow.md",
        ROOT / "docs/ieee39_measurement_extraction_and_timed_trip.md",
        ROOT / "docs/ieee39_clean_breaker_lab_workflow.md",
        ROOT / "docs/ieee39_per_line_clean_breaker_lab_workflow.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8").lower()
        compact_text = re.sub(r"\s+", " ", text)
        assert "l12" in text
        assert "timeout" in text
        assert (
            "not training-ready" in text
            or "training_ready_candidate = false" in text
            or "training_ready_candidate: `false`" in text
        )
        assert (
            "not a verified stable or unstable" in compact_text
            or "not a stable or unstable dynamic conclusion" in compact_text
            or "does not prove that l12 is dynamically stable or unstable" in compact_text
        )
        assert "phasor_rms" in text
        assert "not emt" in text
        assert "generator_speed_proxy" in text
        assert "not direct frequency" in text
        assert "pilot breaker-like" in text
        assert "not engineering-grade" in text
        assert ".slx" in text


def test_l12_docs_do_not_overclaim_or_require_model_commit() -> None:
    docs = [
        ROOT / "docs/ieee39_l12_islanding_timeout_case.md",
        ROOT / "docs/gcn_pio_validation_log.md",
        ROOT / "docs/ieee39_batch_per_line_clean_breaker_lab_workflow.md",
    ]
    forbidden = [
        "l12 is training-ready",
        "l12 training-ready",
        "l12 was merged",
        "emt validation completed",
        "is a direct frequency measurement",
        "direct frequency measurement completed",
        "engineering-grade protection completed",
        "should commit `.slx`",
        "must commit `.slx`",
        "verified stable conclusion",
        "verified unstable conclusion",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8").lower()
        for phrase in forbidden:
            assert phrase not in text
