import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rl_mitigation.cases import make_ieee5_case
from rl_mitigation.dp.dfs_transition_builder import build_transition_counts
from rl_mitigation.dp.policy_iteration import policy_iteration


def test_ieee5_dp_transition_and_policy_smoke():
    case = make_ieee5_case()
    case["initial_outages"] = [0, 3]
    counts = build_transition_counts(case, max_depth=2)
    result = policy_iteration(counts, iterations=5)
    assert counts
    assert result["policy"]
    assert result["values"]

