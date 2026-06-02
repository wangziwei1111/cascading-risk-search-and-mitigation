import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.evaluation.paired_stats import paired_improvement_summary, paired_metric_stats


def test_paired_stats_lower_is_better():
    rows = [
        {"scenario_id": 0, "policy": "do_nothing", "negative_return": 10},
        {"scenario_id": 0, "policy": "agent", "negative_return": 8},
        {"scenario_id": 1, "policy": "do_nothing", "negative_return": 5},
        {"scenario_id": 1, "policy": "agent", "negative_return": 7},
    ]
    stats = paired_metric_stats(rows, "agent", "do_nothing", "negative_return", n_bootstrap=10)
    summary = paired_improvement_summary(rows, "agent", "do_nothing")
    assert stats["num_scenarios"] == 2
    assert stats["improved_ratio"] == 0.5
    assert stats["worse_ratio"] == 0.5
    assert summary["mean_improvement_vs_do_nothing"] == 0.0
    assert summary["improved_scenario_ratio_vs_do_nothing"] == 0.5
