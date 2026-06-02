from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class PowerFlowResult:
    converged: bool
    relative_flow: np.ndarray
    branch_p_from: np.ndarray
    branch_p_to: np.ndarray
    line_status: np.ndarray
    current_load_mw: float
    load_shed_mw: float
    load_shed_ratio: float
    island_count: int
    island_records: list[dict] = field(default_factory=list)
