import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.rl_mitigation.export_policy_multimetric_summary import _summary


def test_policy_multimetric_summary_fields():
    rows = [
        {"scenario_id": 0, "policy": "do_nothing", "negative_return": 10, "pf_failed": False, "num_generations": 1, "num_line_outages": 2, "load_shed_MW": 0, "load_shed_ratio": 0, "num_proactive_actions": 0},
        {"scenario_id": 0, "policy": "agent", "negative_return": 8, "pf_failed": False, "num_generations": 1, "num_line_outages": 1, "load_shed_MW": 0, "load_shed_ratio": 0, "num_proactive_actions": 1},
    ]
    row = _summary(rows, "agent", "test", "deterministic")
    required = {
        "policy", "split", "eval_mode", "episodes", "mean_negative_return",
        "p95_negative_return", "pf_failed_ratio", "mean_num_generations",
        "mean_num_line_outages", "mean_load_shed_MW", "mean_load_shed_ratio",
        "mean_num_proactive_actions", "improved_ratio_negative_return",
        "worse_ratio_negative_return", "improved_ratio_line_outages",
        "improved_ratio_load_shed",
    }
    assert required <= set(row)
    assert row["improved_ratio_negative_return"] == 1.0
