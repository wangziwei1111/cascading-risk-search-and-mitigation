import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rl_mitigation.cases import make_ieee118_case
from rl_mitigation.contingency.sampler import ContingencySampler
from rl_mitigation.envs import CascadeMitigationEnv


def test_ieee118_case_has_complete_action_and_state_spaces():
    case = make_ieee118_case()
    env = CascadeMitigationEnv(case, backend="pypower_ac", max_generations=1, use_action_mask=True)
    obs, _ = env.reset(seed=0)
    assert case["num_lines"] == 186
    assert env.action_space_n == 187
    assert obs.shape == (2 * case["num_lines"],)


def test_ieee118_star_motif_sampler_supports_k_values():
    case = make_ieee118_case()
    sampler = ContingencySampler(case, seed=0, include_n_minus_1=False, include_common_bus_n_minus_2=False, include_star_motifs=True, k_values=[2, 3, 4])
    orders = {len(item) for item in sampler.pool}
    assert {2, 3, 4}.issubset(orders)

