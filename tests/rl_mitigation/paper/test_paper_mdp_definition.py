import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv


def test_paper_state_is_line_status_plus_relative_flow_only():
    case = make_ieee14_case()
    env = CascadeMitigationEnv(case, initial_outage_mode="fixed", fixed_initial_outages=[0], use_action_mask=True)
    obs, _ = env.reset(seed=0)
    n = case["num_lines"]
    assert env.observation_space_shape == (2 * n,)
    assert obs.shape == (2 * n,)
    assert np.all(np.isin(obs[:n], [0.0, 1.0]))
    assert obs[n:].shape == (n,)


def test_paper_action_space_is_complete_do_nothing_plus_one_line_actions():
    case = make_ieee14_case()
    env = CascadeMitigationEnv(case, initial_outage_mode="fixed", fixed_initial_outages=[0])
    assert env.action_space_n == case["num_lines"] + 1
    assert list(range(env.action_space_n)) == list(range(case["num_lines"] + 1))

