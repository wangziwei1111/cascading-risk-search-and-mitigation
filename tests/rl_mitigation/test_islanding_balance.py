import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.envs.islanding import approximate_load_after_outages


def test_load_decreases_with_outages():
    full = approximate_load_after_outages(100.0, np.array([1, 1, 1, 1]))
    partial = approximate_load_after_outages(100.0, np.array([1, 0, 0, 1]))
    assert full == 100.0
    assert partial < full
