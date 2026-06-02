from __future__ import annotations

import copy

import numpy as np
from pypower.api import ppoption, runpf
from pypower.case14 import case14
from pypower.idx_brch import BR_STATUS, F_BUS, PF, PT, RATE_A, T_BUS
from pypower.idx_bus import BUS_I, PD
from pypower.idx_gen import GEN_BUS, PG, PMAX

from .islanding import build_island_records
from .powerflow_result import PowerFlowResult


class PypowerACBackend:
    """AC power-flow backend based on PYPOWER's MATPOWER case14."""

    def __init__(self, case: dict, seed: int = 0, default_rate_a: float = 100.0):
        self.case = case
        self.rng = np.random.default_rng(seed)
        self.default_rate_a = float(default_rate_a)
        self.base_ppc = case14()
        self.lines = [(int(row[F_BUS]) - 1, int(row[T_BUS]) - 1) for row in self.base_ppc["branch"]]
        if len(self.lines) != case["num_lines"]:
            raise ValueError(f"PYPOWER case14 has {len(self.lines)} branches, expected {case['num_lines']}")
        self.base_load_mw = float(np.sum(self.base_ppc["bus"][:, PD]))

    def solve(self, line_status: np.ndarray, load_scale: float = 1.0, gen_scale: float = 1.0) -> PowerFlowResult:
        line_status = np.asarray(line_status, dtype=np.int8).copy()
        ppc = copy.deepcopy(self.base_ppc)
        ppc["branch"][:, BR_STATUS] = line_status
        ppc["bus"][:, PD] *= float(load_scale)
        ppc["gen"][:, PG] *= float(gen_scale)
        ppc["gen"][:, PMAX] *= float(gen_scale)
        ppc, island_records = self._apply_island_balance(ppc, line_status, load_scale, gen_scale)
        options = ppoption(VERBOSE=0, OUT_ALL=0)
        try:
            result, success = runpf(ppc, options)
        except Exception:
            return self._failed_result(line_status, island_records)
        if not bool(success):
            return self._failed_result(line_status, island_records)
        branch = result["branch"]
        rate_a = branch[:, RATE_A].astype(float)
        rate_a = np.where(rate_a > 0, rate_a, self.default_rate_a)
        branch_p_from = branch[:, PF].astype(float)
        branch_p_to = branch[:, PT].astype(float)
        relative_flow = np.maximum(np.abs(branch_p_from), np.abs(branch_p_to)) / rate_a
        relative_flow[line_status == 0] = 0.0
        current_load = float(np.sum(result["bus"][:, PD]))
        load_shed = max(0.0, self.base_load_mw * float(load_scale) - current_load)
        return PowerFlowResult(
            converged=True,
            relative_flow=relative_flow.astype(np.float32),
            branch_p_from=branch_p_from.astype(np.float32),
            branch_p_to=branch_p_to.astype(np.float32),
            line_status=line_status,
            current_load_mw=current_load,
            load_shed_mw=float(load_shed),
            load_shed_ratio=float(load_shed / max(1e-9, self.base_load_mw * float(load_scale))),
            island_count=len(island_records),
            island_records=island_records,
        )

    def _apply_island_balance(self, ppc: dict, line_status: np.ndarray, load_scale: float, gen_scale: float) -> tuple[dict, list[dict]]:
        island_records = build_island_records(self.case, line_status, load_scale=load_scale, gen_scale=gen_scale)
        bus_id_to_row = {int(bus_id): idx for idx, bus_id in enumerate(ppc["bus"][:, BUS_I])}
        gen_rows_by_bus: dict[int, list[int]] = {}
        for gen_row, gen in enumerate(ppc["gen"]):
            gen_rows_by_bus.setdefault(int(gen[GEN_BUS]), []).append(gen_row)
        for record in island_records:
            buses = {bus + 1 for bus in record["buses"]}
            scale_load = 0.0 if record["load_before_mw"] <= 0 else record["load_after_mw"] / record["load_before_mw"]
            for bus_id in buses:
                ppc["bus"][bus_id_to_row[bus_id], PD] *= scale_load
            gen_rows = [row for bus_id in buses for row in gen_rows_by_bus.get(bus_id, [])]
            gen_before = float(np.sum(ppc["gen"][gen_rows, PG])) if gen_rows else 0.0
            if gen_rows and gen_before > 0:
                scale_gen = record["gen_after_mw"] / gen_before
                ppc["gen"][gen_rows, PG] *= scale_gen
        return ppc, island_records

    def _failed_result(self, line_status: np.ndarray, island_records: list[dict]) -> PowerFlowResult:
        zeros = np.zeros(len(line_status), dtype=np.float32)
        load_shed = sum(record["load_shed_mw"] for record in island_records)
        current_load = sum(record["load_after_mw"] for record in island_records)
        return PowerFlowResult(
            converged=False,
            relative_flow=zeros,
            branch_p_from=zeros,
            branch_p_to=zeros,
            line_status=np.asarray(line_status, dtype=np.int8),
            current_load_mw=float(current_load),
            load_shed_mw=float(load_shed),
            load_shed_ratio=float(load_shed / max(1e-9, self.base_load_mw)),
            island_count=len(island_records),
            island_records=island_records,
        )
