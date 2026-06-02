from __future__ import annotations

import numpy as np


def approximate_load_after_outages(base_load: float, line_status: np.ndarray) -> float:
    outage_ratio = 1.0 - float(line_status.mean()) if len(line_status) else 1.0
    shed_ratio = min(0.75, 0.45 * outage_ratio)
    return base_load * (1.0 - shed_ratio)
