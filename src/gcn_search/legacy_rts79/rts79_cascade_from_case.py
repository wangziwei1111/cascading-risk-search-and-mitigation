from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS

from rts79_cascade import (
    Rts79CascadePathResult,
    _build_branch_table,
    balance_islands_by_load_shedding,
    copy_case,
    line_label_to_index_1based,
    open_branches,
    redispatch_minimize_load_shed,
    solve_islanded_dcpf,
)


def offline_line_labels(case: dict) -> list[str]:
    return [f"L{idx + 1:02d}" for idx, row in enumerate(case["branch"]) if int(row[BR_STATUS]) == 0]


def run_sequential_outages_from_case(
    initial_case: dict,
    outage_sequence: Iterable[str],
    beta: float = 1.2,
    security_limit: float = 1.0,
    max_rounds_per_event: int = 20,
) -> dict:
    labels = tuple(label.strip().upper() for label in outage_sequence)
    current_case = copy_case(initial_case)
    all_opened = set(offline_line_labels(current_case))
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
                raise RuntimeError(f"Islanded DCPF did not converge from given case at event={event_id}, round={round_id}")

            branch_table = _build_branch_table(result)
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
            current_case = open_branches(result, [line_label_to_index_1based(label) for label in newly_tripped])
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
        final_branch_table = redispatch_state.final_branch_table

    if final_result is None:
        final_result = current_case
        final_branch_table = _build_branch_table(current_case)
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


def simulate_cascade_path_from_case(
    initial_case: dict,
    outage_sequence: Iterable[str],
    beta: float = 1.2,
    security_limit: float = 1.0,
) -> Rts79CascadePathResult:
    state = run_sequential_outages_from_case(initial_case, outage_sequence, beta=beta, security_limit=security_limit)
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
