"""Prepare IEEE39 all-remaining bus-fault manual GUI wiring package.

This script writes planning artifacts only. It does not run Simulink, does not
create or save .slx files, does not export labels, does not train GCN, and does
not retrain any reranker.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "bus_fault_all_remaining_manual_wiring"
OUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
TEMPLATE_DIR = OUT_DIR / "manual_review_templates"
SOURCE_MODEL_PATH = "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx"
TEMP_MODEL_TEMPLATE = (
    "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies/"
    "IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY.slx"
)
EXISTING_BUS_FAULT_CANDIDATES = ["B39", "B26"]
NORMAL_TARGET_BUSES = [
    *[f"B{i}" for i in range(1, 16)],
    *[f"B{i}" for i in range(17, 26)],
    *[f"B{i}" for i in range(27, 39)],
]
SPECIAL_TARGET_BUSES = ["B16"]
ALL_NEW_TARGET_BUSES = NORMAL_TARGET_BUSES + SPECIAL_TARGET_BUSES


def _write_json(path: Path, payload: Any) -> None:
    os.makedirs(_windows_long_path(path.parent), exist_ok=True)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_text(path: Path, text: str) -> None:
    os.makedirs(_windows_long_path(path.parent), exist_ok=True)
    with open(_windows_long_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)


def _windows_long_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _fault_name(bus: str) -> str:
    return f"Grid/Fault_{bus}_TEMP"


def _temp_model_path(bus: str) -> str:
    return TEMP_MODEL_TEMPLATE.format(bus=bus)


def _template_payload(bus: str) -> dict[str, Any]:
    special = bus in SPECIAL_TARGET_BUSES
    return {
        "target_bus": bus,
        "batch_id": BATCH_ID,
        "special_handling": special,
        "special_handling_reason": "Old Grid/Fault (Three-Phase) is near B16; do not move or rename it." if special else "",
        "suggested_fault_block_name": _fault_name(bus),
        "temp_model_path": _temp_model_path(bus),
        "source_model_path": SOURCE_MODEL_PATH,
        "fault_start_s": 0.5,
        "fault_clear_s": 0.58,
        "duration_s": 0.08,
        "R_pn_fault": "1e-3 Ohm",
        "R_ng_fault": "1e-3 Ohm",
        "enable_temporal_fault": True,
        "source_model_saved": False,
        "temporary_model_saved": False,
        "temporary_model_committed": False,
        "source_slx_modified": False,
        "temporary_slx_committed": False,
        "selected_injection_block_path": "",
        "selected_injection_port_description": "",
        "selected_fault_block_path": "",
        "fault_block_connected_in_parallel": False,
        "original_network_connection_preserved": False,
        "old_fault_still_near_b16": False,
        "old_fault_not_moved": False,
        "no_unintended_bypass": False,
        "no_floating_ports": False,
        "no_unintended_islanding": False,
        "update_diagram_attempted": False,
        "update_diagram_success": False,
        "update_diagram_error": "",
        "measurement_signals_expected_available": False,
        "human_verified_injection_point": False,
        "safe_to_run_smoke_recommendation": False,
        "simulink_smoke_run": False,
        "smoke_success": False,
        "candidate_label_exported": False,
        "labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "next_action": "manual GUI wiring and Update Diagram only",
    }


def _targets_payload() -> dict[str, Any]:
    return {
        "batch_id": BATCH_ID,
        "existing_bus_fault_candidates": EXISTING_BUS_FAULT_CANDIDATES,
        "current_candidate_count": 42,
        "old_formal_gate": "35 / 33 / 33",
        "l12_excluded": True,
        "nf06_provenance_warning_preserved": True,
        "normal_target_buses": NORMAL_TARGET_BUSES,
        "special_target_buses": SPECIAL_TARGET_BUSES,
        "all_new_target_buses": ALL_NEW_TARGET_BUSES,
        "num_normal_targets": len(NORMAL_TARGET_BUSES),
        "num_special_targets": len(SPECIAL_TARGET_BUSES),
        "num_all_new_targets": len(ALL_NEW_TARGET_BUSES),
        "excluded_from_wiring": EXISTING_BUS_FAULT_CANDIDATES,
        "reason_excluded_from_wiring": "already have quality-reviewed candidate labels",
        "special_handling_notes": [
            "B16 has existing old Fault (Three-Phase) nearby",
            "do not rename or move old Fault (Three-Phase)",
            "create a separate Grid/Fault_B16_TEMP only inside B16 temporary local copy",
        ],
        "batch_goal": "collect more independent bus-fault candidates before GCN usefulness audit",
        "should_run_smoke_now": False,
        "should_export_labels_now": False,
        "should_train_now": False,
        "gcn_usefulness_audit_now": False,
        "simulink_run": False,
        "labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
    }


def _targets_md(payload: dict[str, Any]) -> str:
    normal = ", ".join(payload["normal_target_buses"])
    special = ", ".join(payload["special_target_buses"])
    all_targets = "\n".join(f"- {bus}: `{_fault_name(bus)}` -> `{_temp_model_path(bus)}`" for bus in payload["all_new_target_buses"])
    return f"""# IEEE39 All-Remaining Bus-Fault Manual Wiring Targets

This is a planning package only. It does not run Simulink, does not export
labels, does not train GCN, does not run a GCN usefulness audit, and does not
retrain the reranker.

## Counts

- existing completed bus-fault candidates: `{', '.join(EXISTING_BUS_FAULT_CANDIDATES)}`
- current candidate count: `42`
- old formal gate: `35 / 33 / 33`
- normal targets: `{payload['num_normal_targets']}`
- special targets: `{payload['num_special_targets']}`
- total new targets: `{payload['num_all_new_targets']}`

## Target Groups

- normal target buses: `{normal}`
- special target buses: `{special}`
- excluded from wiring: `B39`, `B26`

## All New Targets

{all_targets}

## B16 Special Handling

B16 is special because the old `Grid/Fault (Three-Phase)` is near B16. Do not
rename it, move it, or treat it as `Grid/Fault_B16_TEMP`. Create a separate
`Grid/Fault_B16_TEMP` only inside the B16 ignored temporary local copy.

## Boundaries

B39 and B26 remain candidate labels, not formal labels. No new target is human
verified, smoke success, or candidate-label exported in this round. The model
remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
"""


def _commands_md() -> str:
    rows = "\n".join(
        f"| {bus} | `{_temp_model_path(bus)}` | `{_fault_name(bus)}` | "
        f"`{TEMPLATE_DIR.as_posix()}/manual_bus_fault_injection_review_template_{bus}.json` | "
        f"`{str(bus in SPECIAL_TARGET_BUSES).lower()}` |"
        for bus in ALL_NEW_TARGET_BUSES
    )
    bus_list = "', '".join(ALL_NEW_TARGET_BUSES)
    return f"""# IEEE39 All-Remaining Bus-Fault Manual GUI Wiring Commands

This document is for manual GUI wiring only. Do not run Simulink. Use Update
Diagram only, then record evidence in the per-bus template.

## A. Target Summary

| bus | temp copy path | fault block name | template path | special handling |
| --- | --- | --- | --- | --- |
{rows}

## B. Create Or Open Temporary Local Copies

```matlab
sourceModel = '{SOURCE_MODEL_PATH}';
targetBuses = {{'{bus_list}'}};
for k = 1:numel(targetBuses)
    bus = targetBuses{{k}};
    tempModel = sprintf('{TEMP_MODEL_TEMPLATE}', bus);
    if exist(tempModel, 'file')
        fprintf('Temp copy exists, inspect before editing: %s\\n', tempModel);
    else
        copyfile(sourceModel, tempModel);
        fprintf('Created ignored temp copy: %s\\n', tempModel);
    end
    open_system(tempModel);
end
```

`local_lab_copies` is an ignored local path. Do not commit `.slx`, `.slxc`,
`slprj`, `.mat`, raw trajectories, or full timeseries.

## C. Basic Inspection Commands

```matlab
targetBuses = {{'{bus_list}'}};
for k = 1:numel(targetBuses)
    bus = targetBuses{{k}};
    tempModel = sprintf('{TEMP_MODEL_TEMPLATE}', bus);
    open_system(tempModel);
    bd = bdroot;
    fprintf('\\n=== %s ===\\n', bus);
    busCandidates = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', ['*' bus '*']);
    oldFaults = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', '*Fault (Three-Phase)*');
    newFault = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', ['Fault_' bus '_TEMP']);
    disp(busCandidates);
    disp(oldFaults);
    disp(newFault);
    for n = 1:numel(busCandidates)
        try
            fprintf('%s | BlockType=%s | MaskType=%s\\n', busCandidates{{n}}, get_param(busCandidates{{n}}, 'BlockType'), get_param(busCandidates{{n}}, 'MaskType'));
            disp(get_param(busCandidates{{n}}, 'PortConnectivity'));
        catch ME
            fprintf('Inspection warning for %s: %s\\n', busCandidates{{n}}, ME.message);
        end
    end
end
```

## D. Post-Wiring Update-Diagram Checks

```matlab
targetBuses = {{'{bus_list}'}};
for k = 1:numel(targetBuses)
    bus = targetBuses{{k}};
    tempModel = sprintf('{TEMP_MODEL_TEMPLATE}', bus);
    open_system(tempModel);
    bd = bdroot;
    expectedFaultName = ['Fault_' bus '_TEMP'];
    newFault = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', expectedFaultName);
    if isempty(newFault)
        warning('Missing Grid/Fault_%s_TEMP in %s', bus, bd);
        continue;
    end
    disp(get_param(newFault{{1}}, 'PortConnectivity'));
    if strcmp(bus, 'B16')
        oldFaults = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', '*Fault (Three-Phase)*');
        disp(oldFaults);
    end
    set_param(bd, 'SimulationCommand', 'update');
    save_system(bd);
end
```

Do not press Run. Saving is allowed only for the ignored temporary local copy.

## E. Unified Fault Parameters

For every `Grid/Fault_<BUS>_TEMP`, set:

- fault_start_time: `0.5`
- fault_duration: `0.08`
- R_pn_fault: `1e-3`
- R_ng_fault: `1e-3`

Use `try/catch` because parameter names may differ by block mask.

```matlab
paramAttempts = {{
    'SwitchTimes', '[0.5 0.58]';
    'FaultResistance', '1e-3';
    'GroundResistance', '1e-3';
    'Rpn', '1e-3';
    'Rng', '1e-3'
}};
for p = 1:size(paramAttempts, 1)
    try
        set_param(newFault{{1}}, paramAttempts{{p,1}}, paramAttempts{{p,2}});
    catch ME
        fprintf('Parameter not accepted: %s (%s)\\n', paramAttempts{{p,1}}, ME.message);
    end
end
```

## F. B16 Special Warning

- Do not rename old `Grid/Fault (Three-Phase)`.
- Do not move the old fault block.
- The new fault must be named only `Grid/Fault_B16_TEMP`.
- The old fault should remain near `Grid/Bus16_1` and `Grid/B16 to B17`.
- B16 evidence must be reviewed separately before smoke.
"""


def _schema() -> dict[str, Any]:
    fields = [
        "batch_id",
        "target_bus",
        "special_handling",
        "temp_model_path",
        "selected_injection_block_path",
        "selected_injection_port_description",
        "selected_fault_block_path",
        "fault_block_connected_in_parallel",
        "original_network_connection_preserved",
        "old_fault_still_near_b16",
        "old_fault_not_moved",
        "no_unintended_bypass",
        "no_floating_ports",
        "no_unintended_islanding",
        "update_diagram_attempted",
        "update_diagram_success",
        "update_diagram_error",
        "fault_start_s",
        "fault_clear_s",
        "duration_s",
        "R_pn_fault",
        "R_ng_fault",
        "enable_temporal_fault",
        "source_model_saved",
        "temporary_model_saved",
        "temporary_model_committed",
        "source_slx_modified",
        "temporary_slx_committed",
        "simulink_smoke_run",
        "smoke_success",
        "candidate_label_exported",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "human_verified_injection_point",
        "safe_to_run_smoke_recommendation",
        "failed_checks",
        "next_action",
    ]
    properties: dict[str, Any] = {field: {"type": ["string", "number", "boolean", "array"]} for field in fields}
    for field in [
        "special_handling",
        "fault_block_connected_in_parallel",
        "original_network_connection_preserved",
        "old_fault_still_near_b16",
        "old_fault_not_moved",
        "no_unintended_bypass",
        "no_floating_ports",
        "no_unintended_islanding",
        "update_diagram_attempted",
        "update_diagram_success",
        "enable_temporal_fault",
        "source_model_saved",
        "temporary_model_saved",
        "temporary_model_committed",
        "source_slx_modified",
        "temporary_slx_committed",
        "simulink_smoke_run",
        "smoke_success",
        "candidate_label_exported",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "human_verified_injection_point",
        "safe_to_run_smoke_recommendation",
    ]:
        properties[field] = {"type": "boolean"}
    properties["failed_checks"] = {"type": "array", "items": {"type": "string"}}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "IEEE39 bus-fault manual connection evidence",
        "type": "object",
        "required": fields,
        "properties": properties,
        "additionalProperties": True,
    }


def _gate_sequence_md() -> str:
    return """# IEEE39 Batch Bus-Fault Gate Sequence

This gate sequence applies independently to each target bus. Batch wiring is
allowed, but every bus must still pass its own evidence and quality checks.

## Required Sequence

1. manual connection evidence
2. manual evidence consolidation
3. readiness dry-run
4. actual temporary smoke
5. smoke quality review
6. candidate label export
7. no-training composition review
8. preview/no-leakage comparison
9. consider GCN usefulness audit only after the above gates

## Rules

- A failed bus must not block unrelated buses.
- A failed bus must not be mixed into candidate labels.
- A not-verified bus must not be marked safe_to_run_smoke.
- Quality review must not be skipped before export.
- This round does not run Simulink, does not export labels, does not train GCN,
  and does not run a GCN usefulness audit.
"""


def _doc_md() -> str:
    return f"""# IEEE39 All-Remaining Bus-Fault Manual Wiring Plan

This round prepares a manual GUI wiring package for all remaining IEEE39
bus-fault targets. It is only a preparation plan.

## What This Does

The user can open one ignored temporary local copy per target bus and manually
wire one new `Grid/Fault_<BUS>_TEMP` block in parallel at the chosen bus
injection point. B39 and B26 already have quality-reviewed candidate labels, so
they are excluded from this wiring batch.

## Targets

- existing completed bus faults: `B39`, `B26`
- normal new targets: `B1-B15`, `B17-B25`, `B27-B38`
- special target: `B16`
- total new target count: `37`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Each target bus uses one independent ignored temporary local copy. Do not put
multiple target fault blocks into one `.slx` file.

## B16 Special Handling

B16 is marked special because the old `Grid/Fault (Three-Phase)` is near B16.
Do not rename or move the old fault. Create a separate
`Grid/Fault_B16_TEMP` only inside the B16 temporary local copy.

## Initial Status Of Every New Target

- human_verified_injection_point: `false`
- safe_to_run_smoke_recommendation: `false`
- smoke_success: `false`
- candidate_label_exported: `false`

## Boundaries

This round does not run Simulink, does not run smoke, does not export labels,
does not train GCN, does not retrain the reranker, and does not run a GCN
usefulness audit. B39 and B26 remain candidate labels, not formal labels. The
model remains `phasor_RMS`, not EMT. `generator_speed_proxy` is not direct
frequency. Temporary bus-fault injection is not engineering-grade protection.

## Artifacts

- `{OUT_DIR.relative_to(ROOT).as_posix()}/ieee39_bus_fault_all_remaining_targets.json`
- `{OUT_DIR.relative_to(ROOT).as_posix()}/ieee39_bus_fault_all_remaining_targets.md`
- `{OUT_DIR.relative_to(ROOT).as_posix()}/all_remaining_manual_gui_wiring_commands.md`
- `{OUT_DIR.relative_to(ROOT).as_posix()}/batch_manual_connection_evidence_schema.json`
- `{OUT_DIR.relative_to(ROOT).as_posix()}/batch_gate_sequence.md`
- `{TEMPLATE_DIR.relative_to(ROOT).as_posix()}/manual_bus_fault_injection_review_template_<BUS>.json`
"""


def run() -> None:
    payload = _targets_payload()
    _write_json(OUT_DIR / "ieee39_bus_fault_all_remaining_targets.json", payload)
    _write_text(OUT_DIR / "ieee39_bus_fault_all_remaining_targets.md", _targets_md(payload))
    _write_text(OUT_DIR / "all_remaining_manual_gui_wiring_commands.md", _commands_md())
    _write_json(OUT_DIR / "batch_manual_connection_evidence_schema.json", _schema())
    _write_text(OUT_DIR / "batch_gate_sequence.md", _gate_sequence_md())
    _write_text(ROOT / "docs/ieee39_all_remaining_bus_fault_manual_wiring_plan.md", _doc_md())
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    for bus in ALL_NEW_TARGET_BUSES:
        _write_json(TEMPLATE_DIR / f"manual_bus_fault_injection_review_template_{bus}.json", _template_payload(bus))
    print(json.dumps({"output_dir": str(OUT_DIR), "num_templates": len(ALL_NEW_TARGET_BUSES)}, indent=2))


if __name__ == "__main__":
    run()
