import json
from pathlib import Path


def test_pipeline_summary_has_mode_and_source_eval():
    path = Path("results/rl_mitigation/paper/rl_paper_reproduction_summary.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["smoke_or_mode"] in {"smoke", "medium", "formal"}
    assert data["main_result_dir"] == "results/rl_mitigation/paper"
    assert "source_eval_csv" in data
    assert "figure_status" in data


def test_smoke_and_medium_names_do_not_overlap():
    smoke = Path("results/rl_mitigation/paper/ieee14/eval/eval_100_before_after_smoke.csv")
    medium = Path("results/rl_mitigation/paper/ieee14/eval/eval_300_before_after_medium.csv")
    formal = Path("results/rl_mitigation/paper/ieee14/eval/eval_1000_before_after.csv")
    assert smoke.name.endswith("_smoke.csv")
    assert medium.name.endswith("_medium.csv")
    assert not formal.name.endswith("_smoke.csv")
    assert not formal.name.endswith("_medium.csv")
