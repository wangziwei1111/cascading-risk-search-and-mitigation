from __future__ import annotations

import numpy as np


class SurrogatePowerFlowBackend:
    """Deterministic debug backend standing in for AC power flow.

    It redistributes stress from disconnected lines onto connected lines. This
    keeps the MDP and cascade mechanics testable until an AC pandapower backend
    is wired with exact paper data.
    """

    def __init__(self, base_flows: list[float], seed: int = 0):
        self.base_flows = np.asarray(base_flows, dtype=np.float32)
        self.rng = np.random.default_rng(seed)

    def solve(self, line_status: np.ndarray, generation: int) -> tuple[bool, np.ndarray]:
        connected = line_status.astype(bool)
        if not connected.any():
            return True, np.zeros_like(self.base_flows)
        outage_stress = float((~connected).sum()) * 0.09
        gen_stress = generation * 0.035
        flows = self.base_flows.copy() + outage_stress + gen_stress
        flows[~connected] = 0.0
        if connected.sum() <= 1:
            flows[connected] += 0.35
        return True, flows
