import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.evaluation.survival import survival_by_policy


def test_survival_by_policy_long_table():
    rows = [
        {"policy": "do_nothing", "negative_return": 1.0},
        {"policy": "do_nothing", "negative_return": 3.0},
        {"policy": "agent", "negative_return": 2.0},
        {"policy": "agent", "negative_return": 4.0},
    ]
    out = survival_by_policy(rows)
    assert {"policy", "negative_return", "survival_probability"} <= set(out[0])
    assert {row["policy"] for row in out} == {"do_nothing", "agent"}
    do_nothing = [row for row in out if row["policy"] == "do_nothing"]
    agent = [row for row in out if row["policy"] == "agent"]
    assert do_nothing[0]["negative_return"] == 1.0
    assert agent[0]["negative_return"] == 2.0
