import json
from pathlib import Path


def test_do_nothing_pretrain_is_stronger_than_random_and_records_target():
    diag_path = Path("results/rl_mitigation/paper/ieee14/pretrain/pretrain_diagnostics.json")
    data = json.loads(diag_path.read_text(encoding="utf-8"))
    assert "target_reached" in data
    assert data["mean_prob_do_nothing"] > data["random_action_probability"]
    if data["target_reached"]:
        assert data["target_do_nothing_prob_min"] <= data["mean_prob_do_nothing"] <= data["target_do_nothing_prob_max"]
    else:
        assert data["warning"]


def test_pretrain_history_exists():
    assert Path("results/rl_mitigation/paper/ieee14/pretrain/pretrain_history.csv").exists()

