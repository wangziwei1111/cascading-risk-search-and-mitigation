import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rl_mitigation.rl.action_mask import action_mask, apply_invalid_action_policy


def test_do_nothing_is_always_valid_and_outaged_lines_are_masked():
    line_status = np.array([1, 0, 1], dtype=np.int8)
    mask = action_mask(line_status)
    assert mask.tolist() == [True, True, False, True]


def test_invalid_action_without_mask_is_replaced_by_do_nothing_and_recorded():
    line_status = np.array([1, 0, 1], dtype=np.int8)
    effective_action, invalid = apply_invalid_action_policy(2, line_status, use_mask=False)
    assert effective_action == 0
    assert invalid is True

