from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ieee39_graphical_status_docs_are_conservative() -> None:
    docs = [
        ROOT / "docs" / "ieee39_graphical_dynamic_model_selection.md",
        ROOT / "docs" / "ieee39_graphical_dynamic_model_plan.md",
        ROOT / "docs" / "ieee39_graphical_dynamic_model_status.md",
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8").lower()
        assert "ieee39" in text or "ieee 39" in text
        assert "is an engineering-grade conclusion" not in text
        assert "is an engineering-grade protection model" not in text
        assert "not an emt claim" in text or "do not call it emt" in text or "must not be described as emt" in text


def test_ieee39_status_mentions_schema_not_training() -> None:
    text = (ROOT / "docs" / "ieee39_graphical_dynamic_model_status.md").read_text(encoding="utf-8").lower()
    assert "no dynamic-aware reranker training was performed" in text
    assert "ieee39_dynamic_label_schema.json" in text
    assert "schema rows only" in text
