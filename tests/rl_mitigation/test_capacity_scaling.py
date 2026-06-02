import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs.pypower_ac_backend import PypowerACBackend


def test_scaled_from_base_flow_rate_a_shape_and_base_margin():
    backend = PypowerACBackend(
        make_ieee14_case(),
        rate_a_mode="scaled_from_base_flow",
        rate_a_scale=1.15,
        min_rate_a_mw=20.0,
        default_rate_a_mw=100.0,
    )
    assert len(backend.calibrated_rate_a) == 20
    base = backend.solve(np.ones(20, dtype=np.int8))
    assert base.converged
    assert (base.relative_flow < 1.0).mean() >= 0.8


def test_capacity_scaling_creates_some_overload_under_contingencies():
    backend = PypowerACBackend(
        make_ieee14_case(),
        rate_a_mode="scaled_from_base_flow",
        rate_a_scale=1.15,
        min_rate_a_mw=20.0,
        default_rate_a_mw=100.0,
    )
    overloaded = 0
    for outage in [0, 1, 2, 3, 4, 5, 6]:
        status = np.ones(20, dtype=np.int8)
        status[outage] = 0
        result = backend.solve(status)
        overloaded += int(result.converged and (result.relative_flow >= 1.0).any())
    assert overloaded > 0
