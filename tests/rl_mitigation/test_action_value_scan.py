import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.action_value import scan_scenario_actions
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios


def test_action_value_scan_enumerates_actions_and_marks_validity():
    env = CascadeMitigationEnv(make_ieee14_case(), seed=0, backend="pypower_ac", initial_outage_mode="sampled")
    scenario = generate_eval_scenarios(env, episodes=1, seed=0)[0]
    rows = scan_scenario_actions(env, scenario)
    assert len(rows) == env.action_space_n
    assert {int(row["action"]) for row in rows} == set(range(env.action_space_n))
    assert any(row["is_valid_action"] for row in rows)
    assert {"scenario_id", "negative_return", "cascade_trace_json", "action_type"} <= set(rows[0])
