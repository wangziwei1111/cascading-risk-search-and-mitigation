import json
from pathlib import Path


def test_paper_pipeline_summary_contains_major_system_steps():
    path = Path("results/rl_mitigation/paper/rl_paper_reproduction_summary.json")
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    steps = data.get("steps", {})
    for key in ["ieee5_dp", "figure1_trace", "ieee14_paper_pipeline", "ieee118_pretrain", "ieee118_ppo", "ieee118_eval", "ieee118_figures"]:
        assert key in steps


def test_ieee14_pipeline_report_exists():
    assert Path("results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_report.md").exists()
    assert Path("results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_summary.json").exists()

