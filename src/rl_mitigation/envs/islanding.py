from __future__ import annotations

from collections import defaultdict, deque

import numpy as np


def connected_components(num_buses: int, lines: list[tuple[int, int]], line_status: np.ndarray) -> list[list[int]]:
    adjacency: dict[int, list[int]] = {bus: [] for bus in range(num_buses)}
    for idx, (a, b) in enumerate(lines):
        if line_status[idx]:
            adjacency[a].append(b)
            adjacency[b].append(a)
    seen: set[int] = set()
    components: list[list[int]] = []
    for bus in range(num_buses):
        if bus in seen:
            continue
        queue = deque([bus])
        seen.add(bus)
        comp = []
        while queue:
            cur = queue.popleft()
            comp.append(cur)
            for nxt in adjacency[cur]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        components.append(sorted(comp))
    return components


def build_island_records(case: dict, line_status: np.ndarray, load_scale: float = 1.0, gen_scale: float = 1.0) -> list[dict]:
    components = connected_components(case["num_buses"], case["lines"], line_status)
    loads_by_bus: dict[int, list[tuple[int, float]]] = defaultdict(list)
    gens_by_bus: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for idx, load in enumerate(case.get("loads", [])):
        loads_by_bus[int(load["bus"])].append((idx, float(load["p"]) * load_scale))
    for idx, gen in enumerate(case.get("generators", [])):
        pmax = float(gen.get("pmax", gen.get("p", 0.0))) * gen_scale
        gens_by_bus[int(gen["bus"])].append((idx, pmax))

    records = []
    for island_id, buses in enumerate(components):
        bus_set = set(buses)
        branch_indices = [
            idx for idx, (a, b) in enumerate(case["lines"])
            if line_status[idx] and a in bus_set and b in bus_set
        ]
        load_items = [item for bus in buses for item in loads_by_bus.get(bus, [])]
        gen_items = [item for bus in buses for item in gens_by_bus.get(bus, [])]
        load_before = sum(p for _, p in load_items)
        gen_before = sum(p for _, p in gen_items)
        if load_before <= 0:
            load_after = 0.0
            gen_after = 0.0
            load_shed = 0.0
            balance_case = "no_load"
        elif gen_before <= 0:
            load_after = 0.0
            gen_after = 0.0
            load_shed = load_before
            balance_case = "no_generation"
        elif gen_before < load_before:
            load_after = gen_before
            gen_after = gen_before
            load_shed = load_before - gen_before
            balance_case = "generation_deficit"
        else:
            load_after = load_before
            gen_after = load_before
            load_shed = 0.0
            balance_case = "generation_surplus"
        records.append({
            "island_id": island_id,
            "buses": buses,
            "branches": branch_indices,
            "generators": [idx for idx, _ in gen_items],
            "loads": [idx for idx, _ in load_items],
            "load_before_mw": float(load_before),
            "load_after_mw": float(load_after),
            "load_shed_mw": float(load_shed),
            "gen_before_mw": float(gen_before),
            "gen_after_mw": float(gen_after),
            "balance_case": balance_case,
        })
    return records


def total_load_after_islanding(case: dict, line_status: np.ndarray, load_scale: float = 1.0, gen_scale: float = 1.0) -> tuple[float, float, list[dict]]:
    records = build_island_records(case, line_status, load_scale=load_scale, gen_scale=gen_scale)
    current_load = sum(record["load_after_mw"] for record in records)
    load_shed = sum(record["load_shed_mw"] for record in records)
    return float(current_load), float(load_shed), records


def approximate_load_after_outages(base_load: float, line_status: np.ndarray) -> float:
    outage_ratio = 1.0 - float(line_status.mean()) if len(line_status) else 1.0
    shed_ratio = min(0.75, 0.45 * outage_ratio)
    return base_load * (1.0 - shed_ratio)
