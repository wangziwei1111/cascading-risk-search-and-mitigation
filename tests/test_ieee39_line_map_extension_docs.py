from __future__ import annotations

from pathlib import Path


def test_ieee39_line_map_extension_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    doc = root / "docs/ieee39_line_map_extension_workflow.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8").lower()
    for required in [
        "l01-l05",
        "num_training_ready_labels = 12",
        "num_training_ready_handwired_line_trip_labels = 10",
        "allowed_for_dynamic_aware_training = true",
        "preview training",
        "l06",
        "grid/b14 to b15",
        "l07",
        "grid/b15 to b16",
        "l08",
        "grid/b16 to b17",
        "l09",
        "grid/b16 to b24",
        "l10",
        "grid/b17 to b27",
        "l11-l34",
        "do not invent a block path",
        "one line uses one independent per-line clean lab .slx",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "pilot breaker-like",
        "not engineering-grade",
        ".slx files are local-only",
        "does not auto-insert breakers",
    ]:
        assert required in text
    for forbidden in [
        "train the dynamic-aware reranker now",
        "engineering-grade protection completed",
        "emt validation completed",
        "real scada",
    ]:
        assert forbidden not in text
