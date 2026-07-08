from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import networkx as nx
import numpy as np
import pandas as pd
from pypower.case24_ieee_rts import case24_ieee_rts
from pypower.ext2int import ext2int
from pypower.idx_brch import BR_STATUS, F_BUS, PF, RATE_A, T_BUS
from pypower.idx_bus import BUS_I, PD, VA
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG, PMAX, PMIN
from pypower.makeBdc import makeBdc
from pypower.ppoption import ppoption
from pypower.rundcopf import rundcopf
from pypower.rundcpf import rundcpf
from scipy.optimize import linprog


@dataclass(frozen=True)
class Rts79InitialConfig:
    """Parameters used by the RTS-79 initial operating state module."""

    random_seed: int = 20260511
    load_scale: float = 1.1
    load_random_low: float = 0.9
    load_random_high: float = 1.1


@dataclass(frozen=True)
class Rts79InitialState:
    case: dict
    bus_table: pd.DataFrame
    branch_table: pd.DataFrame
    generator_table: pd.DataFrame
    objective_cost: float
    config: Rts79InitialConfig


@dataclass(frozen=True)
class Rts79PostOutageState:
    case: dict
    opened_line_labels: tuple[str, ...]
    branch_table: pd.DataFrame
    overloaded_lines: tuple[str, ...]
    objective_cost: float
    relay_threshold_beta: float


@dataclass(frozen=True)
class Rts79ProtectionCascadeState:
    case: dict
    initial_outage_labels: tuple[str, ...]
    final_outage_labels: tuple[str, ...]
    final_branch_table: pd.DataFrame
    round_table: pd.DataFrame
    relay_threshold_beta: float
    converged: bool


@dataclass(frozen=True)
class Rts79SequentialOutageState:
    case: dict
    initial_outage_sequence: tuple[str, ...]
    final_outage_labels: tuple[str, ...]
    final_branch_table: pd.DataFrame
    event_table: pd.DataFrame
    relay_trip_detail_table: pd.DataFrame
    bus_shed_table: pd.DataFrame
    redispatch_bus_shed_table: pd.DataFrame
    relay_threshold_beta: float
    island_load_shed_mw: float
    redispatch_load_shed_mw: float
    total_load_shed_mw: float
    converged: bool


@dataclass(frozen=True)
class Rts79IslandBalanceState:
    case: dict
    island_table: pd.DataFrame
    bus_shed_table: pd.DataFrame
    total_load_shed_mw: float


@dataclass(frozen=True)
class Rts79RedispatchState:
    case: dict
    island_table: pd.DataFrame
    bus_shed_table: pd.DataFrame
    final_branch_table: pd.DataFrame
    total_load_shed_mw: float
    security_limit: float
    success: bool


@dataclass(frozen=True)
class Rts79CascadePathResult:
    initial_outage_sequence: tuple[str, ...]
    final_outage_labels: tuple[str, ...]
    protection_event_table: pd.DataFrame
    relay_trip_detail_table: pd.DataFrame
    island_bus_shed_table: pd.DataFrame
    redispatch_bus_shed_table: pd.DataFrame
    final_branch_table: pd.DataFrame
    island_load_shed_mw: float
    redispatch_load_shed_mw: float
    total_load_shed_mw: float
    final_max_loading_ratio: float
    critical: bool
    converged: bool


@dataclass(frozen=True)
class Rts79N2SearchResult:
    summary_table: pd.DataFrame
    critical_table: pd.DataFrame
    num_paths: int
    num_critical_paths: int


@dataclass(frozen=True)
class Rts79MultiScenarioSearchResult:
    scenario_summary_table: pd.DataFrame
    critical_path_frequency_table: pd.DataFrame
    path_result_table: pd.DataFrame
    num_scenarios: int
    num_unique_critical_paths: int


def load_rts79_case() -> dict:
    """Load the IEEE RTS-79 / IEEE 24-bus RTS case from PYPOWER."""

    return case24_ieee_rts()


def apply_rts79_load_profile(
    case: dict,
    config: Rts79InitialConfig,
) -> tuple[dict, np.ndarray]:
    """Apply paper-style RTS-79 load uncertainty and the 1.1 severe-case scale."""

    profiled_case = {key: value.copy() if hasattr(value, "copy") else value for key, value in case.items()}
    bus = profiled_case["bus"].copy()
    rng = np.random.default_rng(config.random_seed)
    load_factors = rng.uniform(config.load_random_low, config.load_random_high, size=bus.shape[0])
    bus[:, PD] = bus[:, PD] * load_factors * config.load_scale
    profiled_case["bus"] = bus
    return profiled_case, load_factors


def open_branches(case: dict, line_indices_1based: Iterable[int]) -> dict:
    """Return a copy of the case with selected L01-style branch indices opened."""

    updated_case = {key: value.copy() if hasattr(value, "copy") else value for key, value in case.items()}
    branch = updated_case["branch"].copy()
    for idx1 in line_indices_1based:
        idx0 = int(idx1) - 1
        if idx0 < 0 or idx0 >= branch.shape[0]:
            raise IndexError(f"Line index L{int(idx1):02d} is outside the RTS-79 branch table")
        branch[idx0, BR_STATUS] = 0
    updated_case["branch"] = branch
    return updated_case


def copy_case(case: dict) -> dict:
    """Copy a PYPOWER case dict without mutating the caller's arrays."""

    return {key: value.copy() if hasattr(value, "copy") else value for key, value in case.items()}


def _ensure_branch_result_columns(case: dict, min_cols: int = PF + 1) -> dict:
    """Return a case whose branch matrix has enough result columns for PF assignment."""

    if case["branch"].shape[1] >= min_cols:
        return case
    expanded = copy_case(case)
    branch = expanded["branch"]
    padded = np.zeros((branch.shape[0], min_cols), dtype=branch.dtype)
    padded[:, : branch.shape[1]] = branch
    expanded["branch"] = padded
    return expanded


def line_label_to_index_1based(line_label: str) -> int:
    """Convert an L01-style RTS-79 line label to a one-based branch index."""

    normalized = line_label.strip().upper()
    if not normalized.startswith("L"):
        raise ValueError(f"Line label must look like L01, got {line_label!r}")
    return int(normalized[1:])


def run_initial_dcopf(config: Rts79InitialConfig | None = None) -> Rts79InitialState:
    """Build and solve the initial RTS-79 DCOPF operating state."""

    config = config or Rts79InitialConfig()
    base_case = load_rts79_case()
    profiled_case, load_factors = apply_rts79_load_profile(base_case, config)
    result = rundcopf(profiled_case, ppoption(VERBOSE=0, OUT_ALL=0))
    if not result["success"]:
        raise RuntimeError("RTS-79 initial DCOPF did not converge")

    bus_table = _build_bus_table(result, load_factors)
    branch_table = _build_branch_table(result)
    generator_table = _build_generator_table(result)
    return Rts79InitialState(
        case=result,
        bus_table=bus_table,
        branch_table=branch_table,
        generator_table=generator_table,
        objective_cost=float(result["f"]),
        config=config,
    )


def run_post_outage_dcopf(
    opened_line_labels: Iterable[str],
    config: Rts79InitialConfig | None = None,
    relay_threshold_beta: float = 1.2,
) -> Rts79PostOutageState:
    """Open selected RTS-79 branches, redispatch with DCOPF, and report overloads."""

    config = config or Rts79InitialConfig()
    base_case = load_rts79_case()
    profiled_case, _ = apply_rts79_load_profile(base_case, config)
    labels = tuple(label.strip().upper() for label in opened_line_labels)
    opened_indices = [line_label_to_index_1based(label) for label in labels]
    outage_case = open_branches(profiled_case, opened_indices)
    result = rundcopf(outage_case, ppoption(VERBOSE=0, OUT_ALL=0))
    if not result["success"]:
        raise RuntimeError(f"RTS-79 post-outage DCOPF did not converge for {', '.join(labels)}")

    branch_table = _build_branch_table(result)
    online = branch_table["status"] == 1
    overloaded_mask = online & (branch_table["loading_ratio"] > relay_threshold_beta)
    overloaded_lines = tuple(branch_table.loc[overloaded_mask, "line_label"].tolist())
    return Rts79PostOutageState(
        case=result,
        opened_line_labels=labels,
        branch_table=branch_table,
        overloaded_lines=overloaded_lines,
        objective_cost=float(result["f"]),
        relay_threshold_beta=relay_threshold_beta,
    )


def run_protection_cascade_dcpf(
    initial_outage_labels: Iterable[str],
    config: Rts79InitialConfig | None = None,
    relay_threshold_beta: float = 1.2,
    max_rounds: int = 20,
) -> Rts79ProtectionCascadeState:
    """Run the paper-style DC power-flow and relay-tripping loop after outages."""

    config = config or Rts79InitialConfig()
    initial_state = run_initial_dcopf(config)
    initial_labels = tuple(label.strip().upper() for label in initial_outage_labels)
    opened_indices = [line_label_to_index_1based(label) for label in initial_labels]
    current_case = open_branches(initial_state.case, opened_indices)
    all_opened = set(initial_labels)
    round_records: list[dict] = []
    final_result: dict | None = None
    final_branch_table: pd.DataFrame | None = None

    for round_id in range(1, max_rounds + 1):
        result, success = rundcpf(current_case, ppoption(VERBOSE=0, OUT_ALL=0))
        if not success:
            raise RuntimeError(
                "RTS-79 DCPF did not converge during protection cascade "
                f"round {round_id} for {', '.join(sorted(all_opened))}"
            )

        branch_table = _build_branch_table(result)
        online = branch_table["status"] == 1
        overloaded_mask = online & (branch_table["loading_ratio"] > relay_threshold_beta)
        newly_tripped = tuple(branch_table.loc[overloaded_mask, "line_label"].tolist())
        max_loading = float(branch_table.loc[online, "loading_ratio"].max()) if online.any() else 0.0
        round_records.append(
            {
                "round": round_id,
                "opened_before": ",".join(sorted(all_opened)),
                "newly_tripped": ",".join(newly_tripped),
                "num_newly_tripped": len(newly_tripped),
                "max_loading_ratio": max_loading,
            }
        )
        final_result = result
        final_branch_table = branch_table
        if not newly_tripped:
            break

        all_opened.update(newly_tripped)
        newly_tripped_indices = [line_label_to_index_1based(label) for label in newly_tripped]
        current_case = open_branches(result, newly_tripped_indices)
    else:
        raise RuntimeError(f"Protection cascade exceeded max_rounds={max_rounds}")

    assert final_result is not None
    assert final_branch_table is not None
    return Rts79ProtectionCascadeState(
        case=final_result,
        initial_outage_labels=initial_labels,
        final_outage_labels=tuple(sorted(all_opened)),
        final_branch_table=final_branch_table,
        round_table=pd.DataFrame(round_records),
        relay_threshold_beta=relay_threshold_beta,
        converged=True,
    )


def run_sequential_initial_outages_dcpf(
    initial_outage_sequence: Iterable[str],
    config: Rts79InitialConfig | None = None,
    relay_threshold_beta: float = 1.2,
    security_limit: float = 1.0,
    max_rounds_per_event: int = 20,
) -> Rts79SequentialOutageState:
    """Apply active outages in order; after each one, run protection, island balancing, and redispatch."""

    config = config or Rts79InitialConfig()
    labels = tuple(label.strip().upper() for label in initial_outage_sequence)
    if not labels:
        raise ValueError("At least one initial outage label is required")

    initial_state = run_initial_dcopf(config)
    current_case = initial_state.case
    all_opened: set[str] = set()
    event_records: list[dict] = []
    relay_detail_records: list[dict] = []
    bus_shed_tables: list[pd.DataFrame] = []
    redispatch_bus_shed_tables: list[pd.DataFrame] = []
    final_result: dict | None = None
    final_branch_table: pd.DataFrame | None = None
    redispatch_success = True

    for event_id, initial_label in enumerate(labels, start=1):
        if initial_label not in all_opened:
            current_case = open_branches(current_case, [line_label_to_index_1based(initial_label)])
            all_opened.add(initial_label)

        for round_id in range(1, max_rounds_per_event + 1):
            island_balance = balance_islands_by_load_shedding(current_case)
            if not island_balance.bus_shed_table.empty:
                shed_table = island_balance.bus_shed_table.copy()
                shed_table.insert(0, "event", event_id)
                shed_table.insert(1, "round", round_id)
                bus_shed_tables.append(shed_table)
                current_case = island_balance.case

            result, success = solve_islanded_dcpf(current_case)
            if not success or not np.isfinite(result["bus"]).all() or not np.isfinite(result["branch"]).all():
                raise RuntimeError(
                    "RTS-79 islanded DCPF did not converge during sequential outage "
                    f"event {event_id} round {round_id}"
                )

            branch_table = _build_branch_table(result)
            online = branch_table["status"] == 1
            overloaded_mask = online & (branch_table["loading_ratio"] > relay_threshold_beta)
            newly_tripped = tuple(branch_table.loc[overloaded_mask, "line_label"].tolist())
            for _, trip_row in branch_table.loc[overloaded_mask].iterrows():
                relay_detail_records.append(
                    {
                        "event": event_id,
                        "initial_outage": initial_label,
                        "round": round_id,
                        "line_label": trip_row["line_label"],
                        "from_bus": int(trip_row["from_bus"]),
                        "to_bus": int(trip_row["to_bus"]),
                        "F_MW": float(trip_row["F_MW"]),
                        "F_max_MW": float(trip_row["F_max_MW"]),
                        "loading_ratio": float(trip_row["loading_ratio"]),
                        "relay_threshold_beta": relay_threshold_beta,
                    }
                )
            max_loading = float(branch_table.loc[online, "loading_ratio"].max()) if online.any() else 0.0
            event_records.append(
                {
                    "event": event_id,
                    "initial_outage": initial_label,
                    "round": round_id,
                    "opened_before": ",".join(sorted(all_opened)),
                    "newly_tripped": ",".join(newly_tripped),
                    "num_newly_tripped": len(newly_tripped),
                    "max_loading_ratio": max_loading,
                }
            )
            final_result = result
            final_branch_table = branch_table
            if not newly_tripped:
                current_case = result
                break

            all_opened.update(newly_tripped)
            current_case = open_branches(result, [line_label_to_index_1based(label) for label in newly_tripped])
        else:
            raise RuntimeError(
                f"Protection cascade exceeded max_rounds_per_event={max_rounds_per_event} "
                f"after initial outage {initial_label}"
            )

        redispatch_state = redispatch_minimize_load_shed(current_case, security_limit=security_limit)
        redispatch_success = redispatch_success and redispatch_state.success
        if not redispatch_state.bus_shed_table.empty:
            redispatch_shed_table = redispatch_state.bus_shed_table.copy()
            redispatch_shed_table.insert(0, "event", event_id)
            redispatch_shed_table.insert(1, "initial_outage", initial_label)
            redispatch_bus_shed_tables.append(redispatch_shed_table)
        current_case = redispatch_state.case
        final_result = redispatch_state.case
        final_branch_table = redispatch_state.final_branch_table

    assert final_result is not None
    assert final_branch_table is not None
    island_bus_shed_table = pd.concat(bus_shed_tables, ignore_index=True) if bus_shed_tables else pd.DataFrame(
        columns=["event", "round", "island_id", "bus_label", "P_D_before_MW", "P_shed_MW", "P_D_after_MW"]
    )
    redispatch_bus_shed_table = (
        pd.concat(redispatch_bus_shed_tables, ignore_index=True)
        if redispatch_bus_shed_tables
        else pd.DataFrame(
            columns=[
                "event",
                "initial_outage",
                "island_id",
                "bus_label",
                "P_D_before_MW",
                "P_shed_MW",
                "P_D_after_MW",
            ]
        )
    )
    island_load_shed = float(island_bus_shed_table["P_shed_MW"].sum()) if not island_bus_shed_table.empty else 0.0
    redispatch_load_shed = (
        float(redispatch_bus_shed_table["P_shed_MW"].sum()) if not redispatch_bus_shed_table.empty else 0.0
    )
    return Rts79SequentialOutageState(
        case=final_result,
        initial_outage_sequence=labels,
        final_outage_labels=tuple(sorted(all_opened)),
        final_branch_table=final_branch_table,
        event_table=pd.DataFrame(event_records),
        relay_trip_detail_table=pd.DataFrame(
            relay_detail_records,
            columns=[
                "event",
                "initial_outage",
                "round",
                "line_label",
                "from_bus",
                "to_bus",
                "F_MW",
                "F_max_MW",
                "loading_ratio",
                "relay_threshold_beta",
            ],
        ),
        bus_shed_table=island_bus_shed_table,
        redispatch_bus_shed_table=redispatch_bus_shed_table,
        relay_threshold_beta=relay_threshold_beta,
        island_load_shed_mw=island_load_shed,
        redispatch_load_shed_mw=redispatch_load_shed,
        total_load_shed_mw=island_load_shed + redispatch_load_shed,
        converged=redispatch_success,
    )


def balance_islands_by_load_shedding(case: dict) -> Rts79IslandBalanceState:
    """Detect islands and proportionally shed load where island generation is insufficient."""

    balanced_case = copy_case(case)
    bus = balanced_case["bus"].copy()
    gen = balanced_case["gen"].copy()
    islands = _find_bus_islands(balanced_case)
    island_records: list[dict] = []
    bus_shed_records: list[dict] = []

    for island_id, island_bus_numbers in enumerate(islands, start=1):
        island_bus_set = set(island_bus_numbers)
        bus_mask = np.array([int(row[BUS_I]) in island_bus_set for row in bus])
        gen_mask = np.array(
            [(int(row[GEN_BUS]) in island_bus_set) and (row[GEN_STATUS] > 0) for row in gen]
        )
        island_load = float(bus[bus_mask, PD].sum())
        island_pmax = float(gen[gen_mask, PMAX].sum())
        load_shed = max(island_load - island_pmax, 0.0)

        island_records.append(
            {
                "island_id": island_id,
                "bus_labels": ",".join(f"B{bus_no:02d}" for bus_no in island_bus_numbers),
                "num_buses": len(island_bus_numbers),
                "P_D_before_MW": island_load,
                "P_Gmax_MW": island_pmax,
                "P_shed_MW": load_shed,
            }
        )

        if load_shed <= 0.0 or island_load <= 0.0:
            continue

        for row_idx in np.where(bus_mask)[0]:
            original_load = float(bus[row_idx, PD])
            if original_load <= 0.0:
                continue
            bus_shed = original_load / island_load * load_shed
            bus[row_idx, PD] = max(original_load - bus_shed, 0.0)
            bus_shed_records.append(
                {
                    "island_id": island_id,
                    "bus_label": f"B{int(bus[row_idx, BUS_I]):02d}",
                    "P_D_before_MW": original_load,
                    "P_shed_MW": bus_shed,
                    "P_D_after_MW": float(bus[row_idx, PD]),
                }
            )

    balanced_case["bus"] = bus
    balanced_case["gen"] = gen
    island_table = pd.DataFrame(island_records)
    bus_shed_table = pd.DataFrame(
        bus_shed_records,
        columns=["island_id", "bus_label", "P_D_before_MW", "P_shed_MW", "P_D_after_MW"],
    )
    return Rts79IslandBalanceState(
        case=balanced_case,
        island_table=island_table,
        bus_shed_table=bus_shed_table,
        total_load_shed_mw=float(bus_shed_table["P_shed_MW"].sum()) if not bus_shed_table.empty else 0.0,
    )


def redispatch_minimize_load_shed(case: dict, security_limit: float = 1.0) -> Rts79RedispatchState:
    """Redispatch each island with a DC linear program that minimizes total load shedding."""

    redispatched = _ensure_branch_result_columns(copy_case(case))
    merged_bus = redispatched["bus"].copy()
    merged_branch = redispatched["branch"].copy()
    merged_gen = redispatched["gen"].copy()
    islands = _find_bus_islands(redispatched)
    island_records: list[dict] = []
    bus_shed_records: list[dict] = []

    for island_id, island_bus_numbers in enumerate(islands, start=1):
        island_case, bus_positions, branch_positions, gen_positions = _extract_island_case(redispatched, island_bus_numbers)
        island_load_before = float(island_case["bus"][:, PD].sum())
        island_pmax = float(island_case["gen"][island_case["gen"][:, GEN_STATUS] > 0, PMAX].sum()) if island_case["gen"].size else 0.0
        island_result = _solve_island_redispatch_lp(island_case, security_limit=security_limit)

        merged_bus[bus_positions, PD] = island_result["bus"][:, PD]
        merged_bus[bus_positions, VA] = island_result["bus"][:, VA]
        if len(branch_positions) > 0:
            merged_branch[branch_positions, PF] = island_result["branch"][:, PF]
        if len(gen_positions) > 0:
            merged_gen[gen_positions, PG] = island_result["gen"][:, PG]

        shed_by_bus = island_result["shed_by_bus_mw"]
        total_shed = float(shed_by_bus.sum())
        island_records.append(
            {
                "island_id": island_id,
                "bus_labels": ",".join(f"B{bus_no:02d}" for bus_no in island_bus_numbers),
                "num_buses": len(island_bus_numbers),
                "P_D_before_MW": island_load_before,
                "P_Gmax_MW": island_pmax,
                "P_shed_MW": total_shed,
            }
        )
        for local_idx, shed in enumerate(shed_by_bus):
            if shed <= 1e-9:
                continue
            bus_shed_records.append(
                {
                    "island_id": island_id,
                    "bus_label": f"B{int(island_case['bus'][local_idx, BUS_I]):02d}",
                    "P_D_before_MW": float(island_result["original_pd_mw"][local_idx]),
                    "P_shed_MW": float(shed),
                    "P_D_after_MW": float(island_result["bus"][local_idx, PD]),
                }
            )

    redispatched["bus"] = merged_bus
    redispatched["branch"] = merged_branch
    redispatched["gen"] = merged_gen
    final_branch_table = _build_branch_table(redispatched)
    bus_shed_table = pd.DataFrame(
        bus_shed_records,
        columns=["island_id", "bus_label", "P_D_before_MW", "P_shed_MW", "P_D_after_MW"],
    )
    return Rts79RedispatchState(
        case=redispatched,
        island_table=pd.DataFrame(island_records),
        bus_shed_table=bus_shed_table,
        final_branch_table=final_branch_table,
        total_load_shed_mw=float(bus_shed_table["P_shed_MW"].sum()) if not bus_shed_table.empty else 0.0,
        security_limit=security_limit,
        success=True,
    )


def simulate_cascade_path(
    initial_outage_sequence: Iterable[str],
    config: Rts79InitialConfig | None = None,
    relay_threshold_beta: float = 1.2,
    security_limit: float = 1.0,
) -> Rts79CascadePathResult:
    """Run the complete deterministic RTS-79 cascade simulation for one ordered path."""

    sequence_state = run_sequential_initial_outages_dcpf(
        initial_outage_sequence,
        config=config,
        relay_threshold_beta=relay_threshold_beta,
        security_limit=security_limit,
    )
    online = sequence_state.final_branch_table["status"] == 1
    final_max_loading = (
        float(sequence_state.final_branch_table.loc[online, "loading_ratio"].max()) if online.any() else 0.0
    )
    island_load_shed = float(sequence_state.island_load_shed_mw)
    redispatch_load_shed = float(sequence_state.redispatch_load_shed_mw)
    total_load_shed = island_load_shed + redispatch_load_shed
    return Rts79CascadePathResult(
        initial_outage_sequence=sequence_state.initial_outage_sequence,
        final_outage_labels=sequence_state.final_outage_labels,
        protection_event_table=sequence_state.event_table,
        relay_trip_detail_table=sequence_state.relay_trip_detail_table,
        island_bus_shed_table=sequence_state.bus_shed_table,
        redispatch_bus_shed_table=sequence_state.redispatch_bus_shed_table,
        final_branch_table=sequence_state.final_branch_table,
        island_load_shed_mw=island_load_shed,
        redispatch_load_shed_mw=redispatch_load_shed,
        total_load_shed_mw=total_load_shed,
        final_max_loading_ratio=final_max_loading,
        critical=total_load_shed > 1e-7,
        converged=sequence_state.converged,
    )


def search_all_n2_cascade_paths(
    config: Rts79InitialConfig | None = None,
    relay_threshold_beta: float = 1.2,
    security_limit: float = 1.0,
    max_paths: int | None = None,
) -> Rts79N2SearchResult:
    """Search all ordered N-2 RTS-79 cascade paths."""

    base_case = load_rts79_case()
    num_lines = base_case["branch"].shape[0]
    line_labels = [f"L{i:02d}" for i in range(1, num_lines + 1)]
    records: list[dict] = []
    searched = 0

    for first_line in line_labels:
        for second_line in line_labels:
            if first_line == second_line:
                continue
            if max_paths is not None and searched >= max_paths:
                summary_table = pd.DataFrame(records)
                critical_table = summary_table[summary_table["critical"]].copy() if not summary_table.empty else summary_table
                return Rts79N2SearchResult(
                    summary_table=summary_table,
                    critical_table=critical_table,
                    num_paths=len(summary_table),
                    num_critical_paths=len(critical_table),
                )

            searched += 1
            path_label = f"{first_line}->{second_line}"
            try:
                result = simulate_cascade_path(
                    [first_line, second_line],
                    config=config,
                    relay_threshold_beta=relay_threshold_beta,
                    security_limit=security_limit,
                )
                records.append(
                    {
                        "path": path_label,
                        "first_line": first_line,
                        "second_line": second_line,
                        "converged": result.converged,
                        "critical": result.critical,
                        "total_load_shed_mw": result.total_load_shed_mw,
                        "island_load_shed_mw": result.island_load_shed_mw,
                        "redispatch_load_shed_mw": result.redispatch_load_shed_mw,
                        "final_max_loading_ratio": result.final_max_loading_ratio,
                        "final_outage_labels": ",".join(result.final_outage_labels),
                        "error": "",
                    }
                )
            except Exception as exc:
                records.append(
                    {
                        "path": path_label,
                        "first_line": first_line,
                        "second_line": second_line,
                        "converged": False,
                        "critical": False,
                        "total_load_shed_mw": np.nan,
                        "island_load_shed_mw": np.nan,
                        "redispatch_load_shed_mw": np.nan,
                        "final_max_loading_ratio": np.nan,
                        "final_outage_labels": "",
                        "error": str(exc),
                    }
                )

    summary_table = pd.DataFrame(records)
    critical_table = summary_table[summary_table["critical"]].copy()
    return Rts79N2SearchResult(
        summary_table=summary_table,
        critical_table=critical_table,
        num_paths=len(summary_table),
        num_critical_paths=len(critical_table),
    )


def search_n2_paths_for_load_scenarios(
    seeds: Iterable[int],
    load_scale: float = 1.1,
    load_random_low: float = 0.9,
    load_random_high: float = 1.1,
    relay_threshold_beta: float = 1.2,
    security_limit: float = 1.0,
    max_paths_per_scenario: int | None = None,
) -> Rts79MultiScenarioSearchResult:
    """批量搜索多个负荷场景下的有序 N-2 关键连锁故障路径。"""

    scenario_records: list[dict] = []
    path_tables: list[pd.DataFrame] = []
    for scenario_id, seed in enumerate(seeds, start=1):
        config = Rts79InitialConfig(
            random_seed=int(seed),
            load_scale=load_scale,
            load_random_low=load_random_low,
            load_random_high=load_random_high,
        )
        search_result = search_all_n2_cascade_paths(
            config=config,
            relay_threshold_beta=relay_threshold_beta,
            security_limit=security_limit,
            max_paths=max_paths_per_scenario,
        )
        scenario_table = search_result.summary_table.copy()
        scenario_table.insert(0, "scenario_id", scenario_id)
        scenario_table.insert(1, "seed", int(seed))
        path_tables.append(scenario_table)
        scenario_records.append(
            {
                "scenario_id": scenario_id,
                "seed": int(seed),
                "num_paths": search_result.num_paths,
                "num_critical_paths": search_result.num_critical_paths,
                "num_errors": int((search_result.summary_table["error"] != "").sum()),
                "max_total_load_shed_mw": float(search_result.summary_table["total_load_shed_mw"].max(skipna=True)),
                "load_scale": load_scale,
                "load_random_low": load_random_low,
                "load_random_high": load_random_high,
                "relay_threshold_beta": relay_threshold_beta,
                "security_limit": security_limit,
            }
        )

    path_result_table = pd.concat(path_tables, ignore_index=True) if path_tables else pd.DataFrame()
    if path_result_table.empty:
        frequency_table = pd.DataFrame(
            columns=[
                "path",
                "first_line",
                "second_line",
                "path_frequency",
                "mean_total_load_shed_mw",
                "max_total_load_shed_mw",
                "scenario_ids",
                "seeds",
            ]
        )
    else:
        critical = path_result_table[path_result_table["critical"]].copy()
        if critical.empty:
            frequency_table = pd.DataFrame(
                columns=[
                    "path",
                    "first_line",
                    "second_line",
                    "path_frequency",
                    "mean_total_load_shed_mw",
                    "max_total_load_shed_mw",
                    "scenario_ids",
                    "seeds",
                ]
            )
        else:
            frequency_table = (
                critical.groupby(["path", "first_line", "second_line"], as_index=False)
                .agg(
                    path_frequency=("path", "size"),
                    mean_total_load_shed_mw=("total_load_shed_mw", "mean"),
                    max_total_load_shed_mw=("total_load_shed_mw", "max"),
                    scenario_ids=("scenario_id", lambda values: ",".join(str(int(v)) for v in values)),
                    seeds=("seed", lambda values: ",".join(str(int(v)) for v in values)),
                )
                .sort_values(["path_frequency", "max_total_load_shed_mw", "path"], ascending=[False, False, True])
                .reset_index(drop=True)
            )

    scenario_summary_table = pd.DataFrame(scenario_records)
    return Rts79MultiScenarioSearchResult(
        scenario_summary_table=scenario_summary_table,
        critical_path_frequency_table=frequency_table,
        path_result_table=path_result_table,
        num_scenarios=len(scenario_summary_table),
        num_unique_critical_paths=len(frequency_table),
    )


def _solve_island_redispatch_lp(island_case: dict, security_limit: float = 1.0) -> dict:
    original_pd = island_case["bus"][:, PD].copy()
    if island_case["gen"].shape[0] == 0:
        result = _ensure_branch_result_columns(copy_case(island_case))
        result["bus"][:, PD] = 0.0
        result["bus"][:, VA] = 0.0
        if result["branch"].shape[0] > 0:
            result["branch"][:, PF] = 0.0
        result["shed_by_bus_mw"] = original_pd
        result["original_pd_mw"] = original_pd
        return result

    if island_case["bus"].shape[0] == 1:
        result = _ensure_branch_result_columns(copy_case(island_case))
        pmax_online = result["gen"][:, PMAX] * (result["gen"][:, GEN_STATUS] > 0)
        served = min(float(original_pd.sum()), float(pmax_online.sum()))
        shed = float(original_pd.sum()) - served
        result["bus"][:, PD] = served
        result["bus"][:, VA] = 0.0
        result["gen"][:, PG] = _dispatch_island_generation(result["gen"], served)
        result["shed_by_bus_mw"] = np.array([shed])
        result["original_pd_mw"] = original_pd
        return result

    internal = ext2int(copy_case(island_case))
    base_mva = float(internal["baseMVA"])
    bus = internal["bus"]
    branch = internal["branch"]
    gen = internal["gen"]
    nb = bus.shape[0]
    ng = gen.shape[0]
    nl = branch.shape[0]
    ntheta = nb
    npg = ng
    nshed = nb
    nvar = ntheta + npg + nshed
    theta_slice = slice(0, ntheta)
    pg_slice = slice(ntheta, ntheta + npg)
    shed_slice = slice(ntheta + npg, nvar)

    Bbus, Bf, Pbusinj, Pfinj = makeBdc(base_mva, bus, branch)
    Bbus = np.asarray(Bbus.todense() if hasattr(Bbus, "todense") else Bbus, dtype=float)
    Bf = np.asarray(Bf.todense() if hasattr(Bf, "todense") else Bf, dtype=float)
    Pbusinj = np.asarray(Pbusinj).reshape(-1)
    Pfinj = np.asarray(Pfinj).reshape(-1)

    c = np.zeros(nvar)
    c[shed_slice] = 1.0

    Aeq = np.zeros((nb, nvar))
    Aeq[:, theta_slice] = Bbus
    for g_idx, gen_row in enumerate(gen):
        bus_idx = int(gen_row[GEN_BUS])
        Aeq[bus_idx, ntheta + g_idx] -= 1.0 / base_mva
    Aeq[:, shed_slice] = -np.eye(nb) / base_mva
    beq = -bus[:, PD] / base_mva - Pbusinj

    Aub = np.zeros((2 * nl, nvar))
    rate_a = branch[:, RATE_A].astype(float) * security_limit
    Aub[:nl, theta_slice] = base_mva * Bf
    bub_upper = rate_a - base_mva * Pfinj
    Aub[nl:, theta_slice] = -base_mva * Bf
    bub_lower = rate_a + base_mva * Pfinj
    bub = np.concatenate([bub_upper, bub_lower])

    bounds: list[tuple[float | None, float | None]] = [(None, None)] * ntheta
    bounds[0] = (0.0, 0.0)
    for gen_row in gen:
        if gen_row[GEN_STATUS] <= 0:
            bounds.append((0.0, 0.0))
        else:
            bounds.append((float(gen_row[PMIN]), float(gen_row[PMAX])))
    for pd_mw in bus[:, PD]:
        bounds.append((0.0, float(pd_mw)))

    opt = linprog(c, A_ub=Aub, b_ub=bub, A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")
    if not opt.success:
        raise RuntimeError(f"Redispatch LP failed: {opt.message}")

    x = opt.x
    theta = x[theta_slice]
    pg = x[pg_slice]
    shed = x[shed_slice]
    flow = base_mva * (Bf @ theta + Pfinj)

    result = _ensure_branch_result_columns(copy_case(internal))
    result["bus"][:, PD] = np.maximum(bus[:, PD] - shed, 0.0)
    result["bus"][:, VA] = theta * 180.0 / np.pi
    result["gen"][:, PG] = pg
    result["branch"][:, PF] = flow
    result["shed_by_bus_mw"] = shed
    result["original_pd_mw"] = bus[:, PD].copy()
    return result


def solve_islanded_dcpf(case: dict) -> tuple[dict, bool]:
    """Run DCPF on each electrical island and merge bus angles/branch flows."""

    islands = _find_bus_islands(case)
    if len(islands) == 1:
        return rundcpf(case, ppoption(VERBOSE=0, OUT_ALL=0))

    merged = _ensure_branch_result_columns(copy_case(case))
    merged_bus = merged["bus"].copy()
    merged_branch = merged["branch"].copy()
    merged_gen = merged["gen"].copy()

    for island_bus_numbers in islands:
        island_case, bus_positions, branch_positions, gen_positions = _extract_island_case(case, island_bus_numbers)
        if island_case["bus"].shape[0] == 1:
            merged_bus[bus_positions[0], VA] = 0.0
            if len(gen_positions) > 0:
                island_load = float(island_case["bus"][:, PD].sum())
                merged_gen[gen_positions, PG] = _dispatch_island_generation(merged_gen[gen_positions], island_load)
            continue

        has_online_gen = island_case["gen"].shape[0] > 0 and np.any(island_case["gen"][:, GEN_STATUS] > 0)
        if not has_online_gen and float(island_case["bus"][:, PD].sum()) <= 1e-9:
            merged_bus[bus_positions, VA] = 0.0
            if len(branch_positions) > 0:
                merged_branch[branch_positions, PF] = 0.0
            continue

        island_result, success = rundcpf(island_case, ppoption(VERBOSE=0, OUT_ALL=0))
        if not success or not np.isfinite(island_result["bus"]).all() or not np.isfinite(island_result["branch"]).all():
            return merged, False
        merged_bus[bus_positions, VA] = island_result["bus"][:, VA]
        merged_branch[branch_positions, PF] = island_result["branch"][:, PF]
        merged_gen[gen_positions, PG] = island_result["gen"][:, PG]

    merged["bus"] = merged_bus
    merged["branch"] = merged_branch
    merged["gen"] = merged_gen
    return merged, True


def _extract_island_case(
    case: dict,
    island_bus_numbers: list[int],
) -> tuple[dict, np.ndarray, np.ndarray, np.ndarray]:
    island_set = set(island_bus_numbers)
    bus_positions = np.array([i for i, row in enumerate(case["bus"]) if int(row[BUS_I]) in island_set], dtype=int)
    branch_positions = np.array(
        [
            i
            for i, row in enumerate(case["branch"])
            if int(row[BR_STATUS]) == 1 and int(row[F_BUS]) in island_set and int(row[T_BUS]) in island_set
        ],
        dtype=int,
    )
    gen_positions = np.array([i for i, row in enumerate(case["gen"]) if int(row[GEN_BUS]) in island_set], dtype=int)
    island_case = {
        key: value.copy() if hasattr(value, "copy") else value
        for key, value in case.items()
        if key not in {"bus", "branch", "gen", "gencost", "areas"}
    }
    island_case["bus"] = case["bus"][bus_positions].copy()
    island_case["branch"] = case["branch"][branch_positions].copy()
    island_case["gen"] = case["gen"][gen_positions].copy()
    if "gencost" in case:
        island_case["gencost"] = case["gencost"][gen_positions].copy()
    if island_case["gen"].shape[0] > 0:
        island_load = float(island_case["bus"][:, PD].sum())
        island_case["gen"][:, PG] = _dispatch_island_generation(island_case["gen"], island_load)
    return island_case, bus_positions, branch_positions, gen_positions


def _dispatch_island_generation(gen: np.ndarray, island_load_mw: float) -> np.ndarray:
    if gen.shape[0] == 0:
        return np.array([])
    dispatched = np.zeros(gen.shape[0], dtype=float)
    online = gen[:, GEN_STATUS] > 0
    pmax = np.where(online, gen[:, PMAX], 0.0)
    pmin = np.where(online, gen[:, PMIN], 0.0)
    if pmax.sum() <= 0.0:
        return dispatched
    base = np.minimum(pmin, pmax)
    remaining_load = max(island_load_mw - base.sum(), 0.0)
    headroom = np.maximum(pmax - base, 0.0)
    if headroom.sum() > 0.0:
        dispatched = base + headroom / headroom.sum() * min(remaining_load, headroom.sum())
    else:
        dispatched = base
    return dispatched


def _find_bus_islands(case: dict) -> list[list[int]]:
    bus = case["bus"]
    branch = case["branch"]
    graph = nx.Graph()
    bus_numbers = [int(row[BUS_I]) for row in bus]
    graph.add_nodes_from(bus_numbers)
    for row in branch:
        if int(row[BR_STATUS]) == 1:
            graph.add_edge(int(row[F_BUS]), int(row[T_BUS]))
    return [sorted(component) for component in nx.connected_components(graph)]


def export_initial_state(state: Rts79InitialState, output_dir: str | Path) -> None:
    """Write the initial RTS-79 state tables to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    state.bus_table.to_csv(out / "rts79_initial_bus_state.csv", index=False, encoding="utf-8-sig")
    state.branch_table.to_csv(out / "rts79_initial_branch_state.csv", index=False, encoding="utf-8-sig")
    state.generator_table.to_csv(out / "rts79_initial_generator_state.csv", index=False, encoding="utf-8-sig")


def export_post_outage_state(state: Rts79PostOutageState, output_dir: str | Path) -> None:
    """Write a post-outage RTS-79 branch state table to CSV."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    outage_name = "_".join(state.opened_line_labels).lower()
    state.branch_table.to_csv(
        out / f"rts79_post_outage_{outage_name}_branch_state.csv",
        index=False,
        encoding="utf-8-sig",
    )


def export_protection_cascade_state(state: Rts79ProtectionCascadeState, output_dir: str | Path) -> None:
    """Write paper-style DCPF relay cascade tables to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    outage_name = "_".join(state.initial_outage_labels).lower()
    state.final_branch_table.to_csv(
        out / f"rts79_protection_cascade_{outage_name}_final_branch_state.csv",
        index=False,
        encoding="utf-8-sig",
    )
    state.round_table.to_csv(
        out / f"rts79_protection_cascade_{outage_name}_rounds.csv",
        index=False,
        encoding="utf-8-sig",
    )


def export_sequential_outage_state(state: Rts79SequentialOutageState, output_dir: str | Path) -> None:
    """Write N-k sequential outage cascade tables to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    outage_name = "_".join(state.initial_outage_sequence).lower()
    state.final_branch_table.to_csv(
        out / f"rts79_sequential_outage_{outage_name}_final_branch_state.csv",
        index=False,
        encoding="utf-8-sig",
    )
    state.event_table.to_csv(
        out / f"rts79_sequential_outage_{outage_name}_events.csv",
        index=False,
        encoding="utf-8-sig",
    )
    state.bus_shed_table.to_csv(
        out / f"rts79_sequential_outage_{outage_name}_bus_shed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    state.redispatch_bus_shed_table.to_csv(
        out / f"rts79_sequential_outage_{outage_name}_redispatch_bus_shed.csv",
        index=False,
        encoding="utf-8-sig",
    )


def export_island_balance_state(state: Rts79IslandBalanceState, output_dir: str | Path, label: str) -> None:
    """Write island load-shedding tables to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    state.island_table.to_csv(out / f"rts79_island_balance_{label}_islands.csv", index=False, encoding="utf-8-sig")
    state.bus_shed_table.to_csv(out / f"rts79_island_balance_{label}_bus_shed.csv", index=False, encoding="utf-8-sig")


def export_redispatch_state(state: Rts79RedispatchState, output_dir: str | Path, label: str) -> None:
    """Write redispatch result tables to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    state.island_table.to_csv(out / f"rts79_redispatch_{label}_islands.csv", index=False, encoding="utf-8-sig")
    state.bus_shed_table.to_csv(out / f"rts79_redispatch_{label}_bus_shed.csv", index=False, encoding="utf-8-sig")
    state.final_branch_table.to_csv(out / f"rts79_redispatch_{label}_branch_state.csv", index=False, encoding="utf-8-sig")


def export_cascade_path_result(result: Rts79CascadePathResult, output_dir: str | Path) -> None:
    """Write complete one-path cascade simulation results to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path_name = "_".join(result.initial_outage_sequence).lower()
    summary = pd.DataFrame(
        [
            {
                "initial_outage_sequence": "->".join(result.initial_outage_sequence),
                "final_outage_labels": ",".join(result.final_outage_labels),
                "island_load_shed_mw": result.island_load_shed_mw,
                "redispatch_load_shed_mw": result.redispatch_load_shed_mw,
                "total_load_shed_mw": result.total_load_shed_mw,
                "final_max_loading_ratio": result.final_max_loading_ratio,
                "critical": result.critical,
                "converged": result.converged,
            }
        ]
    )
    summary.to_csv(out / f"rts79_cascade_path_{path_name}_summary.csv", index=False, encoding="utf-8-sig")
    result.protection_event_table.to_csv(
        out / f"rts79_cascade_path_{path_name}_events.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.island_bus_shed_table.to_csv(
        out / f"rts79_cascade_path_{path_name}_island_bus_shed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.redispatch_bus_shed_table.to_csv(
        out / f"rts79_cascade_path_{path_name}_redispatch_bus_shed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.final_branch_table.to_csv(
        out / f"rts79_cascade_path_{path_name}_final_branch_state.csv",
        index=False,
        encoding="utf-8-sig",
    )


def export_n2_search_result(result: Rts79N2SearchResult, output_dir: str | Path) -> None:
    """Write ordered N-2 search summary tables to CSV files."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.summary_table.to_csv(out / "rts79_n2_search_summary.csv", index=False, encoding="utf-8-sig")
    result.critical_table.to_csv(out / "rts79_n2_search_critical_paths.csv", index=False, encoding="utf-8-sig")


def export_multi_scenario_search_result(result: Rts79MultiScenarioSearchResult, output_dir: str | Path) -> None:
    """导出多负荷场景搜索结果。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result.scenario_summary_table.to_csv(
        out / "rts79_multi_scenario_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.critical_path_frequency_table.to_csv(
        out / "rts79_multi_scenario_critical_paths.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.path_result_table.to_csv(
        out / "rts79_multi_scenario_all_path_results.csv",
        index=False,
        encoding="utf-8-sig",
    )


def check_paper_case_points(
    config: Rts79InitialConfig | None = None,
    relay_threshold_beta: float = 1.2,
    security_limit: float = 1.0,
    output_dir: str | Path = Path("outputs") / "paper_case_check",
) -> pd.DataFrame:
    """核对论文中点名讨论的 RTS-79 案例路径。"""

    cases = [("L10", "L05"), ("L27", "L02")]
    records: list[dict] = []
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for first_line, second_line in cases:
        result = simulate_cascade_path(
            [first_line, second_line],
            config=config,
            relay_threshold_beta=relay_threshold_beta,
            security_limit=security_limit,
        )
        path_name = f"{first_line}_{second_line}".lower()
        export_cascade_path_result(result, out / path_name)
        island_buses = (
            ",".join(result.island_bus_shed_table["bus_label"].tolist())
            if not result.island_bus_shed_table.empty
            else ""
        )
        redispatch_buses = (
            ",".join(result.redispatch_bus_shed_table["bus_label"].tolist())
            if not result.redispatch_bus_shed_table.empty
            else ""
        )
        relay_tripped = _collect_relay_tripped_lines(result.protection_event_table)
        records.append(
            {
                "path": f"{first_line}->{second_line}",
                "critical": result.critical,
                "total_load_shed_mw": result.total_load_shed_mw,
                "island_load_shed_mw": result.island_load_shed_mw,
                "redispatch_load_shed_mw": result.redispatch_load_shed_mw,
                "island_shed_buses": island_buses,
                "redispatch_shed_buses": redispatch_buses,
                "relay_tripped_lines": ",".join(relay_tripped),
                "final_outage_labels": ",".join(result.final_outage_labels),
                "final_max_loading_ratio": result.final_max_loading_ratio,
                "relay_threshold_beta": relay_threshold_beta,
                "security_limit": security_limit,
                "converged": result.converged,
            }
        )

    table = pd.DataFrame(records)
    table.to_csv(out / "rts79_paper_case_check_summary.csv", index=False, encoding="utf-8-sig")
    return table


def _collect_relay_tripped_lines(event_table: pd.DataFrame) -> list[str]:
    lines: list[str] = []
    if event_table.empty or "newly_tripped" not in event_table:
        return lines
    for value in event_table["newly_tripped"]:
        if not isinstance(value, str) or not value:
            continue
        lines.extend(part for part in value.split(",") if part)
    return sorted(set(lines))


def diagnose_final_outage_depth(summary_table: pd.DataFrame) -> pd.DataFrame:
    """统计最终停运线路数量分布。"""

    if summary_table.empty:
        return pd.DataFrame(columns=["final_outage_count", "num_paths", "num_critical_paths"])
    table = summary_table.copy()
    table["final_outage_count"] = table["final_outage_labels"].fillna("").apply(
        lambda value: 0 if not str(value) else len(str(value).split(","))
    )
    return (
        table.groupby("final_outage_count", as_index=False)
        .agg(num_paths=("path", "size"), num_critical_paths=("critical", "sum"))
        .sort_values("final_outage_count")
        .reset_index(drop=True)
    )


def diagnose_beta_depth_sensitivity(
    beta_values: Iterable[float],
    config: Rts79InitialConfig | None = None,
    security_limit: float = 1.0,
    output_dir: str | Path = Path("outputs") / "beta_depth_diagnosis",
) -> pd.DataFrame:
    """比较不同保护阈值 beta 下的路径深度和论文案例点表现。"""

    records: list[dict] = []
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for beta in beta_values:
        search_result = search_all_n2_cascade_paths(
            config=config,
            relay_threshold_beta=float(beta),
            security_limit=security_limit,
        )
        summary = search_result.summary_table.copy()
        summary["final_outage_count"] = summary["final_outage_labels"].fillna("").apply(
            lambda value: 0 if not str(value) else len(str(value).split(","))
        )
        max_count = int(summary["final_outage_count"].max()) if not summary.empty else 0
        top_paths = summary.sort_values(["final_outage_count", "total_load_shed_mw"], ascending=[False, False]).head(5)
        paper_cases = check_paper_case_points(
            config=config,
            relay_threshold_beta=float(beta),
            security_limit=security_limit,
            output_dir=out / f"paper_cases_beta_{str(beta).replace('.', '_')}",
        )
        l27_case = paper_cases.loc[paper_cases["path"] == "L27->L02"].iloc[0]
        records.append(
            {
                "relay_threshold_beta": float(beta),
                "security_limit": security_limit,
                "num_paths": search_result.num_paths,
                "num_critical_paths": search_result.num_critical_paths,
                "num_errors": int((summary["error"] != "").sum()),
                "max_final_outage_count": max_count,
                "top_depth_paths": ";".join(top_paths["path"].tolist()),
                "l27_l02_island_shed_buses": l27_case["island_shed_buses"],
                "l27_l02_redispatch_shed_buses": l27_case["redispatch_shed_buses"],
                "l27_l02_relay_tripped_lines": l27_case["relay_tripped_lines"],
                "l27_l02_total_load_shed_mw": l27_case["total_load_shed_mw"],
            }
        )
        diagnose_final_outage_depth(summary).to_csv(
            out / f"rts79_depth_distribution_beta_{str(beta).replace('.', '_')}.csv",
            index=False,
            encoding="utf-8-sig",
        )

    result = pd.DataFrame(records)
    result.to_csv(out / "rts79_beta_depth_sensitivity.csv", index=False, encoding="utf-8-sig")
    return result


def _build_bus_table(result: dict, load_factors: np.ndarray) -> pd.DataFrame:
    bus = result["bus"]
    return pd.DataFrame(
        {
            "bus_label": [f"B{int(row[BUS_I]):02d}" for row in bus],
            "bus_number": bus[:, BUS_I].astype(int),
            "load_factor": load_factors,
            "P_D_MW": bus[:, PD],
            "theta_deg": bus[:, VA],
        }
    )


def _build_branch_table(result: dict) -> pd.DataFrame:
    branch = result["branch"]
    rate_a = branch[:, RATE_A].astype(float)
    flow = branch[:, PF].astype(float)
    status = branch[:, BR_STATUS].astype(int)
    flow = np.where(status == 1, flow, 0.0)
    return pd.DataFrame(
        {
            "line_label": [f"L{i:02d}" for i in range(1, branch.shape[0] + 1)],
            "from_bus": branch[:, F_BUS].astype(int),
            "to_bus": branch[:, T_BUS].astype(int),
            "status": status,
            "F_MW": flow,
            "abs_F_MW": np.abs(flow),
            "F_max_MW": rate_a,
            "loading_ratio": np.divide(np.abs(flow), rate_a, out=np.zeros_like(flow), where=rate_a > 0),
        }
    )


def _build_generator_table(result: dict) -> pd.DataFrame:
    gen = result["gen"]
    return pd.DataFrame(
        {
            "generator_label": [f"G{i:02d}" for i in range(1, gen.shape[0] + 1)],
            "bus_number": gen[:, GEN_BUS].astype(int),
            "P_G_MW": gen[:, PG],
            "P_G_max_MW": gen[:, PMAX],
        }
    )


def main() -> None:
    state = run_initial_dcopf()
    export_initial_state(state, Path("outputs") / "initial_state")
    print("RTS-79 initial DCOPF success")
    print(f"objective_cost={state.objective_cost:.6f}")
    print(f"total_load_MW={state.bus_table['P_D_MW'].sum():.6f}")
    print(f"total_generation_MW={state.generator_table['P_G_MW'].sum():.6f}")
    print(f"max_loading_ratio={state.branch_table['loading_ratio'].max():.6f}")

    cascade = run_protection_cascade_dcpf(["L10"], config=state.config)
    export_protection_cascade_state(cascade, Path("outputs") / "protection_cascade")
    print("RTS-79 protection cascade DCPF success for L10")
    print(f"protection_cascade_rounds={len(cascade.round_table)}")
    print(f"protection_cascade_final_outages={list(cascade.final_outage_labels)}")
    print(f"protection_cascade_final_max_loading_ratio={cascade.final_branch_table['loading_ratio'].max():.6f}")

    try:
        sequential = run_sequential_initial_outages_dcpf(["L10", "L05"], config=state.config)
    except RuntimeError as exc:
        print("RTS-79 sequential N-2 DCPF stopped for L10 -> L05")
        print(f"sequential_stop_reason={exc}")
    else:
        export_sequential_outage_state(sequential, Path("outputs") / "sequential_outage")
        print("RTS-79 sequential N-2 DCPF success for L10 -> L05")
        print(f"sequential_events={len(sequential.event_table)}")
        print(f"sequential_final_outages={list(sequential.final_outage_labels)}")
        print(f"sequential_total_load_shed_MW={sequential.total_load_shed_mw:.6f}")
        print(f"sequential_final_max_loading_ratio={sequential.final_branch_table['loading_ratio'].max():.6f}")
        redispatch = redispatch_minimize_load_shed(sequential.case)
        export_redispatch_state(redispatch, Path("outputs") / "redispatch", "l10_l05")
        print("RTS-79 redispatch success for L10 -> L05")
        print(f"redispatch_additional_load_shed_MW={redispatch.total_load_shed_mw:.6f}")
        print(f"redispatch_final_max_loading_ratio={redispatch.final_branch_table['loading_ratio'].max():.6f}")

    path_result = simulate_cascade_path(["L10", "L05"], config=state.config)
    export_cascade_path_result(path_result, Path("outputs") / "cascade_path")
    print("RTS-79 full cascade path simulation success for L10 -> L05")
    print(f"path_total_load_shed_MW={path_result.total_load_shed_mw:.6f}")
    print(f"path_critical={path_result.critical}")
    print(f"path_final_max_loading_ratio={path_result.final_max_loading_ratio:.6f}")

    n2_preview = search_all_n2_cascade_paths(config=state.config, max_paths=20)
    export_n2_search_result(n2_preview, Path("outputs") / "n2_search_preview")
    print("RTS-79 N-2 search preview success")
    print(f"n2_preview_paths={n2_preview.num_paths}")
    print(f"n2_preview_critical_paths={n2_preview.num_critical_paths}")

    multi_preview = search_n2_paths_for_load_scenarios(seeds=[20260511, 20260512], max_paths_per_scenario=20)
    export_multi_scenario_search_result(multi_preview, Path("outputs") / "multi_scenario_preview")
    print("RTS-79 multi-scenario N-2 search preview success")
    print(f"multi_preview_scenarios={multi_preview.num_scenarios}")
    print(f"multi_preview_unique_critical_paths={multi_preview.num_unique_critical_paths}")


if __name__ == "__main__":
    main()
