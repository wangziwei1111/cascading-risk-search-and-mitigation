from __future__ import annotations

import numpy as np


def action_mask(line_status: np.ndarray) -> np.ndarray:
    mask = np.zeros(len(line_status) + 1, dtype=bool)
    mask[0] = True
    mask[1:] = line_status.astype(bool)
    return mask


def apply_invalid_action_policy(action: int, line_status: np.ndarray, use_mask: bool = False) -> tuple[int, bool]:
    if action == 0:
        return 0, False
    line_idx = action - 1
    invalid = line_idx < 0 or line_idx >= len(line_status) or line_status[line_idx] == 0
    if invalid and not use_mask:
        return 0, True
    return action, invalid
