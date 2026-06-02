from __future__ import annotations

from .powerflow_backend import SurrogatePowerFlowBackend
from .pypower_ac_backend import PypowerACBackend


def make_backend(name: str, case: dict, seed: int = 0):
    backend = (name or "pypower_ac").lower()
    if backend == "pypower_ac":
        return PypowerACBackend(case, seed=seed)
    if backend in {"surrogate", "debug", "dc_debug_surrogate"}:
        return SurrogatePowerFlowBackend(case["base_flows"], seed=seed)
    raise ValueError(f"Unknown power-flow backend: {name}")
