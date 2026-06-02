import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs.pypower_ac_backend import PypowerACBackend


def test_ieee14_ac_backend_base_case_converges():
    backend = PypowerACBackend(make_ieee14_case(), seed=0)
    result = backend.solve(np.ones(20, dtype=np.int8))
    assert result.converged
    assert len(result.relative_flow) == 20
    assert result.current_load_mw > 0


def test_ieee14_ac_backend_n_minus_1_status_and_fields():
    backend = PypowerACBackend(make_ieee14_case(), seed=0)
    status = np.ones(20, dtype=np.int8)
    status[3] = 0
    result = backend.solve(status)
    assert len(result.relative_flow) == 20
    assert result.relative_flow[3] == 0
    assert hasattr(result, "load_shed_mw")
    assert isinstance(result.island_records, list)
