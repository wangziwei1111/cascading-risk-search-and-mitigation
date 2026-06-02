import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.rl.action_mask import action_mask


def test_action_mask_rules():
    mask = action_mask(np.array([1, 0, 1]))
    assert mask.tolist() == [True, True, False, True]
    all_down = action_mask(np.array([0, 0]))
    assert all_down.tolist() == [True, False, False]
