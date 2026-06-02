import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.contingency.sampler import ContingencySampler, common_bus_n_minus_2, n_minus_1


def test_ieee14_contingencies_and_seed():
    case = make_ieee14_case()
    assert len(n_minus_1(case)) == 20
    assert common_bus_n_minus_2(case)
    a = ContingencySampler(case, seed=7).sample(5)
    b = ContingencySampler(case, seed=7).sample(5)
    assert a == b
