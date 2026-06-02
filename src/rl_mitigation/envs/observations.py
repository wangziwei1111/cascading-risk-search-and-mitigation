from __future__ import annotations

import numpy as np


def build_observation(line_status: np.ndarray, relative_flow: np.ndarray) -> np.ndarray:
    return np.concatenate([line_status.astype(np.float32), relative_flow.astype(np.float32)])
