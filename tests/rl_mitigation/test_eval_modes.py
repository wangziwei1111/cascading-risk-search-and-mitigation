import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.evaluate_agent import run_policy
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.torch_networks import TorchActorCritic


def test_eval_modes_are_accepted_and_preserve_scenarios():
    env = CascadeMitigationEnv(make_ieee14_case(), seed=3, backend="pypower_ac", initial_outage_mode="sampled")
    scenarios = generate_eval_scenarios(env, episodes=2, seed=3)
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    deterministic = run_policy(env, episodes=2, model=model, with_agent=True, scenarios=scenarios, eval_mode="deterministic")
    stochastic = run_policy(env, episodes=2, model=model, with_agent=True, scenarios=scenarios, eval_mode="stochastic")
    assert len(deterministic) == 2
    assert len(stochastic) == 2
    assert [row["scenario_id"] for row in deterministic] == [row["scenario_id"] for row in stochastic]
    assert {row["policy"] for row in deterministic + stochastic} == {"agent"}
