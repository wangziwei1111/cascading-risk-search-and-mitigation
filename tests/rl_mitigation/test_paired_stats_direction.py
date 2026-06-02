import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.evaluation.paired_stats import paired_metric_stats


def test_paired_stats_direction_policy_a_better_for_lower_metric():
    rows = []
    for sid in range(5):
        rows.append({"scenario_id": sid, "policy": "do_nothing", "negative_return": 10.0})
        rows.append({"scenario_id": sid, "policy": "agent", "negative_return": 5.0})
    stats = paired_metric_stats(rows, "agent", "do_nothing", "negative_return", n_bootstrap=20)
    assert stats["direction"] == "policy_a_better"
    assert stats["improved_ratio"] == 1.0
    assert stats["worse_ratio"] == 0.0


def test_paired_stats_direction_policy_a_worse_for_lower_metric():
    rows = []
    for sid in range(5):
        rows.append({"scenario_id": sid, "policy": "do_nothing", "negative_return": 5.0})
        rows.append({"scenario_id": sid, "policy": "agent", "negative_return": 10.0})
    stats = paired_metric_stats(rows, "agent", "do_nothing", "negative_return", n_bootstrap=20)
    assert stats["direction"] == "policy_a_worse"
    assert stats["improved_ratio"] == 0.0
    assert stats["worse_ratio"] == 1.0
