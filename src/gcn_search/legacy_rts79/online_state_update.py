from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from pypower.idx_brch import BR_STATUS, PF
from pypower.idx_bus import BUS_I, PD
from pypower.idx_gen import GEN_BUS, PG

from rts79_cascade import copy_case, line_label_to_index_1based
from train_rts79_paper_gcn import _make_x_gcn, _make_x_gcn_physics


@dataclass(frozen=True)
class MeasuredGridState:
    branch_status: dict[str, int]
    branch_flow_mw: dict[str, float]
    bus_load_mw: dict[int, float]
    generator_output_mw: dict[int, float]
    timestamp: str | None = None
    source: str | None = None


def load_measured_state_json(path: str | Path) -> MeasuredGridState:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return MeasuredGridState(
        branch_status={str(k).upper(): _validate_status(v, f"branch_status[{k}]") for k, v in data.get("branch_status", {}).items()},
        branch_flow_mw={str(k).upper(): _validate_finite(v, f"branch_flow_mw[{k}]") for k, v in data.get("branch_flow_mw", {}).items()},
        bus_load_mw={int(k): _validate_finite(v, f"bus_load_mw[{k}]") for k, v in data.get("bus_load_mw", {}).items()},
        generator_output_mw={
            int(k): _validate_finite(v, f"generator_output_mw[{k}]") for k, v in data.get("generator_output_mw", {}).items()
        },
        timestamp=data.get("timestamp"),
        source=data.get("source"),
    )


def apply_measured_state_to_case(case: dict, measured_state: MeasuredGridState) -> dict:
    updated = copy_case(case)
    if updated["branch"].shape[1] <= PF:
        padded = np.zeros((updated["branch"].shape[0], PF + 1), dtype=updated["branch"].dtype)
        padded[:, : updated["branch"].shape[1]] = updated["branch"]
        updated["branch"] = padded
    branch_count = updated["branch"].shape[0]
    bus_numbers = set(int(row[BUS_I]) for row in updated["bus"])
    gen_buses = set(int(row[GEN_BUS]) for row in updated["gen"])

    for label, status in measured_state.branch_status.items():
        idx = _validate_line_label(label, branch_count)
        updated["branch"][idx, BR_STATUS] = status
    for label, flow in measured_state.branch_flow_mw.items():
        idx = _validate_line_label(label, branch_count)
        updated["branch"][idx, PF] = flow
    for bus_id, load in measured_state.bus_load_mw.items():
        if bus_id not in bus_numbers:
            raise ValueError(f"Invalid bus id in bus_load_mw: {bus_id}")
        updated["bus"][updated["bus"][:, BUS_I].astype(int) == bus_id, PD] = load
    for bus_id, output in measured_state.generator_output_mw.items():
        if bus_id not in gen_buses:
            raise ValueError(f"Invalid generator bus id in generator_output_mw: {bus_id}")
        updated["gen"][updated["gen"][:, GEN_BUS].astype(int) == bus_id, PG] = output
    if not np.isfinite(updated["branch"]).all() or not np.isfinite(updated["bus"]).all() or not np.isfinite(updated["gen"]).all():
        raise ValueError("Measured state update produced NaN/Inf in case arrays.")
    return updated


def make_online_gcn_input(
    case: dict,
    measured_state: MeasuredGridState | None,
    beta: float = 1.2,
    security_limit: float = 1.0,
    feature_mode: str = "physics",
) -> np.ndarray:
    updated = apply_measured_state_to_case(case, measured_state) if measured_state is not None else copy_case(case)
    if feature_mode == "physics":
        x = _make_x_gcn_physics(updated, beta, security_limit=security_limit)
    elif feature_mode == "paper":
        x = _make_x_gcn(updated, beta)
    else:
        raise ValueError(f"Unsupported feature_mode: {feature_mode}")
    if not np.isfinite(x).all():
        raise ValueError("Online GCN input contains NaN/Inf.")
    return x


def _validate_line_label(label: str, branch_count: int) -> int:
    idx = line_label_to_index_1based(label) - 1
    if idx < 0 or idx >= branch_count:
        raise ValueError(f"Invalid branch label: {label}")
    return idx


def _validate_status(value: Any, name: str) -> int:
    if int(value) not in {0, 1}:
        raise ValueError(f"{name} must be 0 or 1, got {value}")
    return int(value)


def _validate_finite(value: Any, name: str) -> float:
    number = float(value)
    if not np.isfinite(number):
        raise ValueError(f"{name} must be finite, got {value}")
    return number
