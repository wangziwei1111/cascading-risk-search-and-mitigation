import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.torch_networks import TorchActorCritic
from scripts.rl_mitigation.diagnose_policy_actions import _diagnose_one, _summary


def test_policy_diagnostics_exposes_do_nothing_probability():
    env = CascadeMitigationEnv(make_ieee14_case(), seed=2, backend="pypower_ac", initial_outage_mode="sampled")
    scenario = generate_eval_scenarios(env, episodes=1, seed=2)[0]
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    row = _diagnose_one(env, model, scenario)
    summary = _summary([row])
    assert 0.0 <= row["prob_do_nothing"] <= 1.0
    assert 0.0 <= row["max_nonzero_action_prob"] <= 1.0
    assert {"mean_prob_do_nothing", "argmax_do_nothing_ratio", "top_nonzero_actions_frequency"} <= set(summary)
