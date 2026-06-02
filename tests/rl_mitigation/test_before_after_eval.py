import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.evaluate_agent import run_policy, save_eval_csv
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.torch_networks import TorchActorCritic


def test_before_after_uses_same_scenarios(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), seed=0, backend="pypower_ac", initial_outage_mode="sampled")
    scenarios = generate_eval_scenarios(env, episodes=4, seed=0)
    model = TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    rows = []
    rows.extend(run_policy(env, episodes=4, model=model, with_agent=True, scenarios=scenarios))
    rows.extend(run_policy(env, episodes=4, model=model, with_agent=False, scenarios=scenarios))
    out = tmp_path / "eval.csv"
    save_eval_csv(rows, str(out))
    with open(out, newline="", encoding="utf-8") as f:
        loaded = list(csv.DictReader(f))
    required = {
        "scenario_id", "policy", "initial_outages", "initial_outage_type", "episode_return",
        "negative_return", "num_generations", "num_line_outages", "load_shed_MW",
        "load_shed_ratio", "num_proactive_actions", "num_invalid_actions", "pf_failed",
    }
    assert required <= set(loaded[0])
    by_id = {}
    for row in loaded:
        by_id.setdefault(row["scenario_id"], []).append(row)
    for pair in by_id.values():
        assert {row["policy"] for row in pair} == {"agent", "do_nothing"}
        assert len({row["initial_outages"] for row in pair}) == 1
        assert len({row["chronic_index"] for row in pair}) == 1
