from pathlib import Path


def test_figure_index_has_smoke_formal_and_claim_boundary_columns():
    text = Path("docs/rl_paper_figure_index.md").read_text(encoding="utf-8")
    assert "Smoke/Formal" in text
    assert "Claim boundary" in text
    for figure in ["Figure 1", "Figure 2", "Figure 3", "Figure 7", "Figure 8", "Figure 9", "Figure 10", "Figure 11", "Figure 12"]:
        assert figure in text

