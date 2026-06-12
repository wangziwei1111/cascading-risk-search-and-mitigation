from __future__ import annotations

from pathlib import Path


def test_multi_handwired_docs_are_conservative() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "docs/ieee39_multi_handwired_breaker_expansion.md").read_text(encoding="utf-8").lower()
    for required in [
        "handwired .slx",
        "must not be committed",
        "pilot breaker-like",
        "not engineering-grade",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "preliminary preview training",
    ]:
        assert required in text
    for forbidden in ["emt validation completed", "engineering-grade protection completed", "formal dynamic superiority"]:
        assert forbidden not in text
