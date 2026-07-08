from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from pypower.case118 import case118
from pypower.idx_brch import BR_STATUS, F_BUS, PF, RATE_A, T_BUS
from pypower.ppoption import ppoption
from pypower.rundcopf import rundcopf

from rts79_cascade import (
    Rts79CascadePathResult,
    Rts79InitialConfig,
    apply_rts79_load_profile,
    balance_islands_by_load_shedding,
    copy_case,
    load_rts79_case,
    open_branches,
    redispatch_minimize_load_shed,
    solve_islanded_dcpf,
)


@dataclass(frozen=True)
class CaseAdapter:
    case_name: str
    case: dict
    line_labels: tuple[str, ...]
    legacy_line_labels: tuple[str, ...]

    @property
    def num_branches(self) -> int:
        return len(self.line_labels)

    def normalize_line_label(self, line_label: str) -> str:
        normalized = line_label.strip().upper()
        if not normalized.startswith("L"):
            raise ValueError(f"Line label must look like L001, got {line_label!r}")
        idx1 = int(normalized[1:])
        if idx1 < 1 or idx1 > self.num_branches:
            raise IndexError(f"Line label {line_label!r} is outside the {self.case_name} branch table")
        return self.line_labels[idx1 - 1]

    def line_label_to_index_1based(self, line_label: str) -> int:
        return int(self.normalize_line_label(line_label)[1:])


@dataclass(frozen=True)
class GenericInitialState:
    case_name: str
    case: dict
    branch_table: pd.DataFrame
    objective_cost: float
    adapter: CaseAdapter


def build_case_adapter(case_name: str, *, rts79_config: Rts79InitialConfig | None = None) -> CaseAdapter:
    normalized = case_name.strip().lower()
    if normalized in {"rts79", "rts-79", "case24", "case24_ieee_rts"}:
        base_case = load_rts79_case()
        if rts79_config is not None:
            base_case, _ = apply_rts79_load_profile(base_case, rts79_config)
        case_key = "rts79"
    elif normalized in {"ieee118", "case118"}:
        base_case = case118()
        case_key = "ieee118"
    else:
        raise ValueError(f"Unsupported case_name={case_name!r}; expected 'rts79' or 'ieee118'")

    num_branches = int(base_case["branch"].shape[0])
    return CaseAdapter(
        case_name=case_key,
        case=base_case,
        line_labels=tuple(f"L{idx:03d}" for idx in range(1, num_branches + 1)),
        legacy_line_labels=tuple(f"L{idx:02d}" for idx in range(1, num_branches + 1)),
    )


def run_initial_dcopf_for_case(
    case_name: str,
    *,
    rts79_config: Rts79InitialConfig | None = None,
) -> GenericInitialState:
    adapter = build_case_adapter(case_name, rts79_config=rts79_config)
    result = rundcopf(copy_case(adapter.case), ppoption(VERBOSE=0, OUT_ALL=0))
    if not result["success"]:
        raise RuntimeError(f"{adapter.case_name} initial DCOPF did not converge")
    return GenericInitialState(
        case_name=adapter.case_name,
        case=result,
        branch_table=build_branch_table(result, adapter),
        objective_cost=float(result["f"]),
        adapter=adapter,
    )


def run_sequential_outages_for_case(
    initial_case: dict,
    adapter: CaseAdapter,
    outage_sequence: Iterable[str],
    *,
    beta: float = 1.2,
    security_limit: float = 1.0,
    max_rounds_per_event: int = 20,
) -> dict:
    labels = tuple(adapter.normalize_line_label(label) for label in outage_sequence)
    if not labels:
        raise ValueError("At least one outage label is required")

    current_case = copy_case(initial_case)
    all_opened = set(offline_line_labels(current_case, adapter))
    event_records: list[dict] = []
    relay_detail_records: list[dict] = []
    bus_shed_tables: list[pd.DataFrame] = []
    redispatch_bus_shed_tables: list[pd.DataFrame] = []
    final_result: dict | None = None
    final_branch_table: pd.DataFrame | None = None
    redispatch_success = True

    for event_id, initial_label in enumerate(labels, start=1):
        if initial_label not in all_opened:
            current_case = open_branches(current_case, [adapter.line_label_to_index_1based(initial_label)])
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
                    f"{adapter.case_name} islanded DCPF did not converge at event={event_id}, round={round_id}"
                )

            branch_table = build_branch_table(result, adapter)
            online = branch_table["status"] == 1
            overloaded = online & (branch_table["loading_ratio"] > beta)
            newly_tripped = tuple(branch_table.loc[overloaded, "line_label"].tolist())
            for _, trip_row in branch_table.loc[overloaded].iterrows():
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
                        "relay_threshold_beta": beta,
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
            current_case = open_branches(result, [adapter.line_label_to_index_1based(label) for label in newly_tripped])
        else:
            raise RuntimeError(f"Protection cascade exceeded max_rounds_per_event={max_rounds_per_event}")

        redispatch_state = redispatch_minimize_load_shed(current_case, security_limit=security_limit)
        redispatch_success = redispatch_success and redispatch_state.success
        if not redispatch_state.bus_shed_table.empty:
            redispatch_shed = redispatch_state.bus_shed_table.copy()
            redispatch_shed.insert(0, "event", event_id)
            redispatch_shed.insert(1, "initial_outage", initial_label)
            redispatch_bus_shed_tables.append(redispatch_shed)
        current_case = redispatch_state.case
        final_result = redispatch_state.case
        final_branch_table = build_branch_table(redispatch_state.case, adapter)

    assert final_result is not None
    assert final_branch_table is not None
    island_bus_shed_table = pd.concat(bus_shed_tables, ignore_index=True) if bus_shed_tables else pd.DataFrame()
    redispatch_bus_shed_table = pd.concat(redispatch_bus_shed_tables, ignore_index=True) if redispatch_bus_shed_tables else pd.DataFrame()
    return {
        "case": final_result,
        "initial_outage_sequence": labels,
        "final_outage_labels": tuple(sorted(all_opened)),
        "final_branch_table": final_branch_table,
        "event_table": pd.DataFrame(event_records),
        "relay_trip_detail_table": pd.DataFrame(relay_detail_records),
        "island_bus_shed_table": island_bus_shed_table,
        "redispatch_bus_shed_table": redispatch_bus_shed_table,
        "island_load_shed_mw": float(island_bus_shed_table["P_shed_MW"].sum()) if "P_shed_MW" in island_bus_shed_table else 0.0,
        "redispatch_load_shed_mw": float(redispatch_bus_shed_table["P_shed_MW"].sum()) if "P_shed_MW" in redispatch_bus_shed_table else 0.0,
        "converged": bool(redispatch_success),
    }


def simulate_cascade_path_for_case(
    case_name: str,
    outage_sequence: Iterable[str],
    *,
    beta: float = 1.2,
    security_limit: float = 1.0,
    rts79_config: Rts79InitialConfig | None = None,
) -> Rts79CascadePathResult:
    initial_state = run_initial_dcopf_for_case(case_name, rts79_config=rts79_config)
    state = run_sequential_outages_for_case(
        initial_state.case,
        initial_state.adapter,
        outage_sequence,
        beta=beta,
        security_limit=security_limit,
    )
    online = state["final_branch_table"]["status"] == 1
    final_max_loading = float(state["final_branch_table"].loc[online, "loading_ratio"].max()) if online.any() else 0.0
    total_shed = float(state["island_load_shed_mw"]) + float(state["redispatch_load_shed_mw"])
    return Rts79CascadePathResult(
        initial_outage_sequence=state["initial_outage_sequence"],
        final_outage_labels=state["final_outage_labels"],
        protection_event_table=state["event_table"],
        relay_trip_detail_table=state["relay_trip_detail_table"],
        island_bus_shed_table=state["island_bus_shed_table"],
        redispatch_bus_shed_table=state["redispatch_bus_shed_table"],
        final_branch_table=state["final_branch_table"],
        island_load_shed_mw=float(state["island_load_shed_mw"]),
        redispatch_load_shed_mw=float(state["redispatch_load_shed_mw"]),
        total_load_shed_mw=total_shed,
        final_max_loading_ratio=final_max_loading,
        critical=total_shed > 1e-7,
        converged=bool(state["converged"]),
    )


def search_ordered_n2_paths_for_case(
    case_name: str,
    *,
    num_paths: int,
    seed: int,
    beta: float = 1.2,
    security_limit: float = 1.0,
) -> pd.DataFrame:
    if num_paths < 1:
        raise ValueError("num_paths must be positive")

    initial_state = run_initial_dcopf_for_case(case_name)
    labels = list(initial_state.adapter.line_labels)
    rng = np.random.default_rng(seed)
    candidate_indices = [(i, j) for i in range(len(labels)) for j in range(len(labels)) if i != j]
    chosen = rng.choice(len(candidate_indices), size=min(num_paths, len(candidate_indices)), replace=False)
    records: list[dict] = []
    for path_id, choice in enumerate(chosen, start=1):
        first_idx, second_idx = candidate_indices[int(choice)]
        first_line = labels[first_idx]
        second_line = labels[second_idx]
        path = f"{first_line}->{second_line}"
        try:
            state = run_sequential_outages_for_case(
                initial_state.case,
                initial_state.adapter,
                [first_line, second_line],
                beta=beta,
                security_limit=security_limit,
            )
            online = state["final_branch_table"]["status"] == 1
            final_max_loading = (
                float(state["final_branch_table"].loc[online, "loading_ratio"].max()) if online.any() else 0.0
            )
            total_shed = float(state["island_load_shed_mw"]) + float(state["redispatch_load_shed_mw"])
            records.append(
                {
                    "path_id": path_id,
                    "path": path,
                    "first_line": first_line,
                    "second_line": second_line,
                    "converged": bool(state["converged"]),
                    "critical": total_shed > 1e-7,
                    "total_load_shed_mw": total_shed,
                    "island_load_shed_mw": float(state["island_load_shed_mw"]),
                    "redispatch_load_shed_mw": float(state["redispatch_load_shed_mw"]),
                    "final_max_loading_ratio": final_max_loading,
                    "final_outage_labels": ",".join(state["final_outage_labels"]),
                    "error": "",
                }
            )
        except Exception as exc:
            records.append(
                {
                    "path_id": path_id,
                    "path": path,
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
    return pd.DataFrame(records)


def offline_line_labels(case: dict, adapter: CaseAdapter) -> tuple[str, ...]:
    return tuple(adapter.line_labels[idx] for idx, row in enumerate(case["branch"]) if int(row[BR_STATUS]) == 0)


def build_branch_table(result: dict, adapter: CaseAdapter) -> pd.DataFrame:
    branch = result["branch"]
    rate_a = branch[:, RATE_A].astype(float)
    flow = branch[:, PF].astype(float)
    status = branch[:, BR_STATUS].astype(int)
    flow = np.where(status == 1, flow, 0.0)
    return pd.DataFrame(
        {
            "line_label": list(adapter.line_labels),
            "legacy_line_label": list(adapter.legacy_line_labels),
            "from_bus": branch[:, F_BUS].astype(int),
            "to_bus": branch[:, T_BUS].astype(int),
            "status": status,
            "F_MW": flow,
            "abs_F_MW": np.abs(flow),
            "F_max_MW": rate_a,
            "loading_ratio": np.divide(np.abs(flow), rate_a, out=np.zeros_like(flow), where=rate_a > 0),
        }
    )
