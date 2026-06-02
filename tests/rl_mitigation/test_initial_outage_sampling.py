import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.contingency.sampler import ContingencySampler
from rl_mitigation.envs import CascadeMitigationEnv


def test_fixed_mode_reuses_same_initial_outage():
    case = make_ieee14_case()
    env = CascadeMitigationEnv(case, initial_outage_mode="fixed", fixed_initial_outages=[2, 3], backend="pypower_ac")
    first = env.reset(seed=1)[1]["initial_outages"]
    second = env.reset(seed=2)[1]["initial_outages"]
    assert first == [2, 3]
    assert second == [2, 3]


def test_sampled_mode_varies_and_is_reproducible():
    case = make_ieee14_case()
    env = CascadeMitigationEnv(case, initial_outage_mode="sampled", backend="pypower_ac", seed=5)
    samples = [tuple(env.reset()[1]["initial_outages"]) for _ in range(8)]
    assert len(set(samples)) > 1
    env_a = CascadeMitigationEnv(case, initial_outage_mode="sampled", backend="pypower_ac", seed=9)
    env_b = CascadeMitigationEnv(case, initial_outage_mode="sampled", backend="pypower_ac", seed=9)
    assert env_a.reset()[1]["initial_outages"] == env_b.reset()[1]["initial_outages"]


def test_sampler_describes_n1_and_common_bus_n2():
    case = make_ieee14_case()
    sampler = ContingencySampler(case, seed=0)
    n1 = sampler.describe((0,))
    assert n1["order"] == 1
    assert n1["type"] == "N-1"
    pair = next(c for c in sampler.pool if len(c) == 2)
    desc = sampler.describe(pair)
    assert desc["order"] == 2
    assert desc["type"] == "common_bus_N-2"
    a, b = pair
    assert set(case["lines"][a]) & set(case["lines"][b])
