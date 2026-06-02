from __future__ import annotations

import numpy as np
from pypower.case14 import case14
from pypower.idx_brch import F_BUS, RATE_A, T_BUS
from pypower.idx_bus import BUS_I, PD
from pypower.idx_gen import GEN_BUS, PMAX


def make_case_from_pypower_case14() -> dict:
    ppc = case14()
    bus = ppc["bus"]
    branch = ppc["branch"]
    gen = ppc["gen"]
    bus_to_zero = {int(row[BUS_I]): idx for idx, row in enumerate(bus)}
    lines = [(bus_to_zero[int(row[F_BUS])], bus_to_zero[int(row[T_BUS])]) for row in branch]
    loads = [
        {"bus": bus_to_zero[int(row[BUS_I])], "p": float(row[PD])}
        for row in bus
        if float(row[PD]) > 0.0
    ]
    generators = [
        {"bus": bus_to_zero[int(row[GEN_BUS])], "pmax": float(row[PMAX])}
        for row in gen
    ]
    return {
        "name": "ieee14_pypower_case14",
        "source": "pypower.case14",
        "num_buses": len(bus),
        "num_lines": len(branch),
        "lines": lines,
        "loads": loads,
        "generators": generators,
        "base_load_mw": float(np.sum(bus[:, PD])),
        "branch_rate_a_original": branch[:, RATE_A].astype(float).tolist(),
        "base_flows": [0.5] * len(lines),
        "line_limits": [1.0] * len(lines),
        "initial_outages": [0],
    }
