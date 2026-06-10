from __future__ import annotations

from pathlib import Path


def test_preliminary_diagnostic_report_is_conservative() -> None:
    report = Path("docs/pio_gcn_dynamic_preliminary_diagnostic_report.md")
    assert report.exists()
    text = report.read_text(encoding="utf-8").lower()
    for required in ["no dynamic recall", "not emt", "not full opf", "no observed learned dynamic advantage"]:
        assert required in text
    for forbidden in ["final dynamic proof", "engineering-grade conclusion", "learned superiority claim"]:
        assert forbidden not in text
