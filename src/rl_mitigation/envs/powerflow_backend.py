from __future__ import annotations

import numpy as np

from .islanding import approximate_load_after_outages
from .powerflow_result import PowerFlowResult


class SurrogatePowerFlowBackend:
    """Deterministic debug backend standing in for AC power flow.

    It redistributes stress from disconnected lines onto connected lines. This
    keeps the MDP and cascade mechanics testable until an AC pandapower backend
    is wired with exact paper data.
    """

    def __init__(self, base_flows: list[float], seed: int = 0):
        self.base_flows = np.asarray(base_flows, dtype=np.float32)
        self.rng = np.random.default_rng(seed)

    def solve(self, line_status: np.ndarray, generation: int = 0, load_scale: float = 1.0, gen_scale: float = 1.0) -> PowerFlowResult:
        connected = line_status.astype(bool)
        if not connected.any():
            flows = np.zeros_like(self.base_flows)
        else:
            outage_stress = float((~connected).sum()) * 0.09
            gen_stress = generation * 0.035
            flows = self.base_flows.copy() + outage_stress + gen_stress
            flows[~connected] = 0.0
            if connected.sum() <= 1:
                flows[connected] += 0.35
        base_load = 1.0
        current_load = approximate_load_after_outages(base_load, line_status)
        load_shed = base_load - current_load
        return PowerFlowResult(
            converged=True,
            relative_flow=flows.astype(np.float32),
            branch_p_from=flows.astype(np.float32),
            branch_p_to=(-flows).astype(np.float32),
            line_status=line_status.astype(np.int8),
            current_load_mw=float(current_load),
            load_shed_mw=float(load_shed),
            load_shed_ratio=float(load_shed / base_load),
            island_count=1,
            island_records=[],
        )
