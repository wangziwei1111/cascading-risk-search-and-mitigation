import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.oracle_policy import choose_best_initial_action
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios


def test_oracle_policy_returns_valid_initial_action():
    env = CascadeMitigationEnv(make_ieee14_case(), seed=1, backend="pypower_ac", initial_outage_mode="sampled")
    scenario = generate_eval_scenarios(env, episodes=1, seed=1)[0]
    action, row = choose_best_initial_action(env, scenario)
    assert 0 <= action < env.action_space_n
    assert action == int(row["action"])
    assert row["is_valid_action"]
    assert "negative_return" in row
