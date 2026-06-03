from pathlib import Path


def test_figure_index_documents_required_figures():
    text = Path("docs/rl_paper_figure_index.md").read_text(encoding="utf-8")
    for figure in ["Figure 1", "Figure 2", "Figure 3", "Figure 7", "Figure 8", "Figure 9", "Figure 10", "Figure 11", "Figure 12"]:
        assert figure in text

