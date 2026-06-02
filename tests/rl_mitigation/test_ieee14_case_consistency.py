import sys
from pathlib import Path

import numpy as np
from pypower.case14 import case14
from pypower.idx_brch import F_BUS, T_BUS
from pypower.idx_bus import BUS_I, PD
from pypower.idx_gen import GEN_BUS

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.contingency.sampler import ContingencySampler
from rl_mitigation.envs.pypower_ac_backend import PypowerACBackend


def test_ieee14_case_matches_pypower_case14():
    case = make_ieee14_case()
    ppc = case14()
    bus_to_zero = {int(row[BUS_I]): idx for idx, row in enumerate(ppc["bus"])}
    expected_lines = [(bus_to_zero[int(row[F_BUS])], bus_to_zero[int(row[T_BUS])]) for row in ppc["branch"]]
    expected_loads = [(bus_to_zero[int(row[BUS_I])], float(row[PD])) for row in ppc["bus"] if float(row[PD]) > 0]
    expected_gens = [bus_to_zero[int(row[GEN_BUS])] for row in ppc["gen"]]
    assert case["num_lines"] == len(ppc["branch"])
    assert case["num_buses"] == len(ppc["bus"])
    assert case["lines"] == expected_lines
    assert [(row["bus"], row["p"]) for row in case["loads"]] == expected_loads
    assert [row["bus"] for row in case["generators"]] == expected_gens


def test_sampler_indices_and_backend_flow_length_match_case():
    case = make_ieee14_case()
    sampler = ContingencySampler(case, seed=0)
    assert all(0 <= idx < case["num_lines"] for contingency in sampler.sample(20) for idx in contingency)
    result = PypowerACBackend(case).solve(np.ones(case["num_lines"], dtype=np.int8))
    assert len(result.relative_flow) == case["num_lines"]
