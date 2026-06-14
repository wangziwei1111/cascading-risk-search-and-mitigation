from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
LINE_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
INVENTORY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
VALIDATION = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
    "ieee39_clean_breaker_lab_batch_validation_summary.csv"
)
SIMULATION = ROOT / (
    "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/"
    "ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
)
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_JSON = OUT_DIR / "ieee39_l12_islanding_diagnosis.json"
OUT_MD = OUT_DIR / "ieee39_l12_islanding_diagnosis.md"
LINE_ID = "L12"


def main() -> None:
    diagnosis = diagnose_l12()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(diagnosis, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(diagnosis), encoding="utf-8")
    print(json.dumps(diagnosis, ensure_ascii=False, indent=2))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")


def diagnose_l12() -> dict[str, Any]:
    line_map = pd.read_csv(LINE_MAP)
    inventory = pd.read_csv(INVENTORY)
    validation = pd.read_csv(VALIDATION)
    simulation = pd.read_csv(SIMULATION)

    l12_map = line_map[line_map["line_id"].astype(str).eq(LINE_ID)].iloc[0]
    l12_validation = validation[validation["line_id"].astype(str).eq(LINE_ID)].iloc[0]
    l12_simulation = simulation[simulation["tripped_line"].astype(str).eq(LINE_ID)].iloc[0]

    bus_a = str(l12_map["from_bus"])
    bus_b = str(l12_map["to_bus"])
    graph = build_graph(inventory, skip_edge=frozenset((bus_a, bus_b)))
    component = connected_component(graph, bus_a)
    all_components = connected_components(graph)
    largest_component = max(all_components, key=len) if all_components else set()
    reference_buses = {"B1", "B39"}
    contains_reference = bool(component & reference_buses)
    contains_main_grid = len(component) == len(largest_component)
    islanding_candidate = not contains_reference and not contains_main_grid

    recommended_manual_checks = [
        "Check whether L12_HandwiredTimedBreaker is truly in series with Grid/B19 to B16.",
        "Check whether the original B19-B16 connection is actually opened when the breaker trips.",
        "Check whether any bypass path remains around the L12 breaker.",
        "Check whether L12_TripCommand controls only the L12 breaker.",
        "Check whether the Step command direction is 0 -> 1.",
        "Check whether the breaker control port is connected to the intended control input.",
        "Check whether opening B19-B16 creates an abnormal B19-side Simscape island.",
        "If this is a natural islanding branch, keep L12 as an islanding special case rather than a standard training-ready single-line label.",
    ]

    suspected_reason = (
        f"Removing {bus_a}-{bus_b} leaves the {bus_a}-side component with "
        f"{len(component)} bus(es): {sorted(component)}. "
        "This component does not contain the selected reference/main-grid buses "
        f"{sorted(reference_buses)} and is not the largest remaining component."
        if islanding_candidate
        else (
            f"Removing {bus_a}-{bus_b} leaves {bus_a} connected to the reference/main grid "
            "under the simplified inventory graph; the timeout may be caused by wiring, control, "
            "or Simscape numerical issues rather than a simple topological island."
        )
    )

    return {
        "line_id": LINE_ID,
        "line_block_path": str(l12_map["line_block_path"]),
        "validation_passed": boolish(l12_validation["validation_passed"]),
        "simulation_success": boolish(l12_simulation["simulation_success"]),
        "measurement_extraction_status": str(l12_simulation["measurement_extraction_status"]),
        "training_ready_candidate": boolish(l12_simulation["training_ready_candidate"]),
        "timeout_or_error_message": str(l12_simulation.get("timeout_or_error_message", "")),
        "breaker_block_found": boolish(l12_validation["breaker_block_found"]),
        "trip_command_found": boolish(l12_validation["trip_command_found"]),
        "breaker_near_line": boolish(l12_validation["breaker_near_line"]),
        "islanding_candidate": bool(islanding_candidate),
        "removed_edge": [bus_a, bus_b],
        "b19_component_after_l12_open": sorted(component),
        "component_size": len(component),
        "component_contains_reference_or_main_grid": bool(contains_reference or contains_main_grid),
        "largest_component_size_after_l12_open": len(largest_component),
        "suspected_reason": suspected_reason,
        "recommended_manual_checks": recommended_manual_checks,
        "recommended_next_action": (
            "Manually inspect and optionally rewire L12; if it is a natural islanding case, "
            "keep it as a special-case timeout label and do not merge as standard training-ready line trip."
        ),
        "should_merge_as_training_ready": False,
        "should_retrain_reranker": False,
        "caveats": [
            "Topology diagnosis is based on the wrapper Grid line inventory, not a full dynamic stability proof.",
            "phasor_RMS, not EMT",
            "generator_speed_proxy, not direct frequency",
            "pilot breaker-like validation, not engineering-grade protection",
            "L12 remains a suspected islanding / timeout special case, not a verified stable or unstable conclusion.",
        ],
    }


def build_graph(inventory: pd.DataFrame, skip_edge: frozenset[str]) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    candidates = inventory[inventory["is_line_like_candidate"].astype(str).str.lower().isin({"1", "true"})]
    for _, row in candidates.iterrows():
        bus_a = str(row["bus_from_candidate"])
        bus_b = str(row["bus_to_candidate"])
        if not bus_a or not bus_b or bus_a.lower() == "nan" or bus_b.lower() == "nan":
            continue
        if frozenset((bus_a, bus_b)) == skip_edge:
            continue
        graph[bus_a].add(bus_b)
        graph[bus_b].add(bus_a)
    return graph


def connected_component(graph: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(sorted(graph.get(node, set()) - seen))
    return seen


def connected_components(graph: dict[str, set[str]]) -> list[set[str]]:
    remaining = set(graph)
    components: list[set[str]] = []
    while remaining:
        start = sorted(remaining)[0]
        component = connected_component(graph, start)
        components.append(component)
        remaining -= component
    return components


def boolish(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def render_markdown(diagnosis: dict[str, Any]) -> str:
    checks = "\n".join(f"- {item}" for item in diagnosis["recommended_manual_checks"])
    caveats = "\n".join(f"- {item}" for item in diagnosis["caveats"])
    component = ", ".join(diagnosis["b19_component_after_l12_open"])
    return f"""# IEEE39 L12 Islanding / Timeout Diagnosis

## Status

- line_id: `{diagnosis['line_id']}`
- line block path: `{diagnosis['line_block_path']}`
- validation_passed: `{str(diagnosis['validation_passed']).lower()}`
- simulation_success: `{str(diagnosis['simulation_success']).lower()}`
- measurement_extraction_status: `{diagnosis['measurement_extraction_status']}`
- training_ready_candidate: `{str(diagnosis['training_ready_candidate']).lower()}`
- should_merge_as_training_ready: `{str(diagnosis['should_merge_as_training_ready']).lower()}`
- should_retrain_reranker: `{str(diagnosis['should_retrain_reranker']).lower()}`

L12 is not merged into the formal fault summary as a training-ready line-trip
label. It remains a suspected islanding / timeout special case.

## Topology Diagnosis

- removed edge: `{diagnosis['removed_edge'][0]}-{diagnosis['removed_edge'][1]}`
- B19-side component after opening L12: `{component}`
- component size: `{diagnosis['component_size']}`
- component_contains_reference_or_main_grid: `{str(diagnosis['component_contains_reference_or_main_grid']).lower()}`
- islanding_candidate: `{str(diagnosis['islanding_candidate']).lower()}`

{diagnosis['suspected_reason']}

This does not prove a stable or unstable dynamic conclusion. It only indicates
that L12 should be treated carefully as an islanding / timeout case.

## Recommended Manual Checks

{checks}

## Recommended Next Action

{diagnosis['recommended_next_action']}

## Optional Commands After Manual Repair

MATLAB:

```matlab
cd matlab/simulink_ieee39
configure_ieee39_short_filegen_paths()
validate_ieee39_clean_breaker_lab_lines_batch(["L12"])
```

PowerShell:

```powershell
python scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py --line-ids L12 --model-path-pattern "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{{line_id}}.slx" --timeout-seconds 240 --simulation-stop-time 0.5
```

Do not rerun this automatically before the user confirms L12 has been inspected
or rewired.

## Caveats

{caveats}

Do not commit `.slx`, `.slxc`, `slprj`, `.mat`, raw trajectories, or full
timeseries.
"""


if __name__ == "__main__":
    main()
