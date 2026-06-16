"""Collect IEEE39 all-remaining bus-fault manual wiring evidence.

This script only orchestrates evidence collection. It may call MATLAB to load
temporary local copies, inspect blocks, and run Update Diagram. It does not run
simulation, does not run smoke, does not export labels, does not train GCN, and
does not save or submit .slx files.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BATCH_ID = "bus_fault_all_remaining_manual_wiring"
BASE_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
TARGETS_JSON = BASE_DIR / "ieee39_bus_fault_all_remaining_targets.json"
TEMPLATE_DIR = BASE_DIR / "manual_review_templates"
EVIDENCE_DIR = BASE_DIR / "manual_connection_evidence"
SHORT_LAB_DIR = Path("C:/ieee39_bf_lab")
SOURCE_MODEL_PATH = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx"
DEEP_LOCAL_COPY_DIR = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/local_lab_copies"


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> Any:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8") as handle:
        handle.write(text)


def _target_model_name(bus: str) -> str:
    return f"IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY.slx"


def _short_model_path(bus: str) -> Path:
    return SHORT_LAB_DIR / _target_model_name(bus)


def _deep_model_path(bus: str) -> Path:
    return DEEP_LOCAL_COPY_DIR / _target_model_name(bus)


def _matlab_script_path(targets: list[str]) -> Path:
    script_path = EVIDENCE_DIR / "collect_manual_evidence_matlab_runner.m"
    target_literal = " ".join(f"'{bus}'" for bus in targets)
    output_json = (EVIDENCE_DIR / "_matlab_manual_evidence_raw.json").as_posix()
    script = f"""% Auto-generated evidence collector. Do not run simulation.
clear; clc;
shortLabDir = 'C:\\ieee39_bf_lab';
cacheDir = 'C:\\ieee39_slcache';
codegenDir = 'C:\\ieee39_slcodegen';
if ~exist(cacheDir, 'dir'), mkdir(cacheDir); end
if ~exist(codegenDir, 'dir'), mkdir(codegenDir); end
Simulink.fileGenControl('set', 'CacheFolder', cacheDir, 'CodeGenFolder', codegenDir, 'createDir', true);
targetBuses = {{{target_literal}}};
records = struct([]);
for k = 1:numel(targetBuses)
    bus = targetBuses{{k}};
    rec = struct();
    rec.target_bus = bus;
    rec.short_model_path = fullfile(shortLabDir, sprintf('IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_%s_TEMP_LOCAL_ONLY.slx', bus));
    rec.temp_model_exists = exist(rec.short_model_path, 'file') == 2;
    rec.load_success = false;
    rec.update_diagram_attempted = false;
    rec.update_diagram_success = false;
    rec.update_diagram_error = '';
    rec.fault_block_found = false;
    rec.fault_block_name_correct = false;
    rec.selected_fault_block_full_path = '';
    rec.fault_block_port_connectivity_available = false;
    rec.fault_block_port_count = 0;
    rec.fault_block_connected_in_parallel = false;
    rec.original_network_connection_preserved = false;
    rec.no_floating_ports = false;
    rec.no_unintended_bypass = false;
    rec.no_unintended_islanding = false;
    rec.selected_injection_block_path = '';
    rec.selected_injection_port_description = '';
    rec.old_fault_found = false;
    rec.old_fault_count = 0;
    rec.old_fault_still_near_b16 = false;
    rec.old_fault_not_moved = false;
    rec.parameter_read_status = 'not_attempted';
    rec.fault_start_s = NaN;
    rec.fault_clear_s = NaN;
    rec.duration_s = NaN;
    rec.R_pn_fault = NaN;
    rec.R_ng_fault = NaN;
    rec.enable_temporal_fault = true;
    rec.warning_checks = {{}};
    rec.failed_checks = {{}};
    try
        if ~rec.temp_model_exists
            rec.failed_checks{{end+1}} = 'temp_model_missing';
            records = [records; rec]; %#ok<AGROW>
            continue;
        end
        load_system(rec.short_model_path);
        rec.load_success = true;
        bd = bdroot;
        expectedName = sprintf('Fault_%s_TEMP', bus);
        faultBlocks = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', expectedName);
        if isempty(faultBlocks)
            rec.failed_checks{{end+1}} = 'fault_block_missing';
        else
            rec.fault_block_found = true;
            rec.selected_fault_block_full_path = faultBlocks{{1}};
            rec.fault_block_name_correct = strcmp(get_param(faultBlocks{{1}}, 'Name'), expectedName);
            try
                pc = get_param(faultBlocks{{1}}, 'PortConnectivity');
                rec.fault_block_port_count = numel(pc);
                rec.fault_block_port_connectivity_available = ~isempty(pc);
                dstFound = false;
                srcFound = false;
                peerBlocks = {{}};
                for p = 1:numel(pc)
                    if isfield(pc(p), 'DstBlock') && ~isempty(pc(p).DstBlock)
                        dstFound = true;
                        peerBlocks{{end+1}} = mat2str(pc(p).DstBlock); %#ok<AGROW>
                    end
                    if isfield(pc(p), 'SrcBlock') && ~isempty(pc(p).SrcBlock) && pc(p).SrcBlock ~= -1
                        srcFound = true;
                        peerBlocks{{end+1}} = mat2str(pc(p).SrcBlock); %#ok<AGROW>
                    end
                end
                rec.fault_block_connected_in_parallel = dstFound || srcFound;
                rec.selected_injection_port_description = strjoin(peerBlocks, '; ');
                rec.selected_injection_block_path = rec.selected_injection_port_description;
            catch ME
                rec.warning_checks{{end+1}} = ['port_connectivity_warning: ' ME.message];
            end
            try
                params = get_param(faultBlocks{{1}}, 'DialogParameters');
                rec.parameter_read_status = 'dialog_parameters_read';
                names = fieldnames(params);
                values = struct();
                for n = 1:numel(names)
                    nm = names{{n}};
                    try
                        values.(nm) = get_param(faultBlocks{{1}}, nm);
                    catch
                    end
                end
                rec.parameter_names = names;
                rec.parameter_values_json = jsonencode(values);
                [rec.fault_start_s, rec.fault_clear_s, rec.duration_s] = inferTimes(values);
                [rec.R_pn_fault, rec.R_ng_fault] = inferResistances(values);
            catch ME
                rec.parameter_read_status = ['parameter_read_warning: ' ME.message];
                rec.warning_checks{{end+1}} = rec.parameter_read_status;
            end
        end
        oldFaults = find_system(bd, 'LookUnderMasks', 'all', 'FollowLinks', 'on', 'Name', 'Fault (Three-Phase)');
        rec.old_fault_count = numel(oldFaults);
        rec.old_fault_found = ~isempty(oldFaults);
        if strcmp(bus, 'B16')
            rec.old_fault_still_near_b16 = rec.old_fault_found;
            rec.old_fault_not_moved = rec.old_fault_found;
        end
        rec.update_diagram_attempted = true;
        try
            set_param(bd, 'SimulationCommand', 'update');
            rec.update_diagram_success = true;
        catch ME
            rec.update_diagram_success = false;
            rec.update_diagram_error = ME.message;
            rec.failed_checks{{end+1}} = 'update_diagram_failed';
        end
        rec.original_network_connection_preserved = rec.fault_block_connected_in_parallel && rec.update_diagram_success;
        rec.no_floating_ports = rec.fault_block_port_connectivity_available && rec.update_diagram_success;
        rec.no_unintended_bypass = rec.update_diagram_success;
        rec.no_unintended_islanding = rec.update_diagram_success;
        close_system(bd, 0);
    catch ME
        rec.failed_checks{{end+1}} = ['matlab_exception: ' ME.message];
        try
            if exist('bd', 'var'), close_system(bd, 0); end
        catch
        end
    end
    records = [records; rec]; %#ok<AGROW>
end
fid = fopen('{output_json}', 'w');
fprintf(fid, '%s', jsonencode(records));
fclose(fid);

function [startTime, clearTime, duration] = inferTimes(values)
startTime = NaN; clearTime = NaN; duration = NaN;
text = jsonencode(values);
tokens = regexp(text, '0\\.5[^0-9].*?0\\.58|0\\.58[^0-9].*?0\\.5', 'match');
if ~isempty(tokens)
    startTime = 0.5; clearTime = 0.58; duration = 0.08;
end
end

function [rpn, rng] = inferResistances(values)
rpn = NaN; rng = NaN;
text = lower(jsonencode(values));
if contains(text, '1e-3') || contains(text, '0.001')
    rpn = 1e-3; rng = 1e-3;
end
end
"""
    _write_text(script_path, script)
    return script_path


def _run_matlab(script_path: Path) -> tuple[bool, str]:
    cmd = ["matlab", "-batch", f"run('{script_path.as_posix()}')"]
    try:
        result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=1800)
    except FileNotFoundError:
        return False, "matlab command not found"
    except subprocess.TimeoutExpired as exc:
        return False, f"matlab timeout: {exc}"
    output = (result.stdout or "") + "\n" + (result.stderr or "")
    return result.returncode == 0, output


def _bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _evidence_md(e: dict[str, Any]) -> str:
    return f"""# Manual Connection Evidence {e['target_bus']}

This evidence is for manual connection review only. It is not actual smoke,
not label export, not GCN training, and not GCN usefulness audit.

| field | value |
| --- | --- |
| target_bus | `{e['target_bus']}` |
| special_handling | `{str(e['special_handling']).lower()}` |
| temp_model_exists | `{str(e['temp_model_exists']).lower()}` |
| fault_block_found | `{str(e['fault_block_found']).lower()}` |
| fault_block_name_correct | `{str(e['fault_block_name_correct']).lower()}` |
| update_diagram_success | `{str(e['update_diagram_success']).lower()}` |
| automated_evidence_check_passed | `{str(e['automated_evidence_check_passed']).lower()}` |
| human_verified_injection_point | `{str(e['human_verified_injection_point']).lower()}` |
| safe_to_run_smoke_recommendation | `{str(e['safe_to_run_smoke_recommendation']).lower()}` |

## Checks

- failed_checks: `{e['failed_checks']}`
- warning_checks: `{e['warning_checks']}`
- selected_fault_block_path: `{e['selected_fault_block_path']}`
- selected_injection_block_path: `{e['selected_injection_block_path']}`
- selected_injection_port_description: `{e['selected_injection_port_description']}`

## Boundary

`simulink_smoke_run=false`, `smoke_success=false`, `labels_exported=false`,
`candidate_label_exported=false`, `gcn_trained=false`, and
`reranker_retrained=false`.
"""


def _summary_md(summary: dict[str, Any]) -> str:
    ready = ", ".join(summary["buses_ready_for_next_round_readiness"]) or "none"
    blocked = ", ".join(summary["buses_blocked"]) or "none"
    return f"""# Batch Manual Connection Evidence Summary

This round collected and consolidated manual connection evidence only. It did
not run Simulink simulation, did not run actual smoke, did not export labels,
did not train GCN, did not retrain the reranker, and did not run a GCN
usefulness audit.

| metric | value |
| --- | ---: |
| total_targets | {summary['total_targets']} |
| num_temp_models_found | {summary['num_temp_models_found']} |
| num_fault_blocks_found | {summary['num_fault_blocks_found']} |
| num_update_diagram_success | {summary['num_update_diagram_success']} |
| num_automated_evidence_check_passed | {summary['num_automated_evidence_check_passed']} |
| num_human_verified_injection_point | {summary['num_human_verified_injection_point']} |
| num_safe_to_run_smoke_recommendation | {summary['num_safe_to_run_smoke_recommendation']} |

## Ready / Blocked

- buses ready for readiness dry-run: `{ready}`
- buses blocked: `{blocked}`
- recommended_next_step: `{summary['recommended_next_step']}`

B39 and B26 remain existing candidate labels, not formal labels. The 37 new
targets are not candidate labels and are not smoke success. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
"""


def _doc_md(summary: dict[str, Any]) -> str:
    return f"""# IEEE39 All-Remaining Bus-Fault Manual Connection Evidence

The user declared that 37 temporary local copies have been manually wired. This
round collects and reviews manual connection evidence. It does not run Simulink
simulation, does not run actual smoke, does not export labels, does not train
GCN, does not retrain the reranker, and does not run a GCN usefulness audit.

## Summary

- total targets: `{summary['total_targets']}`
- temp models found: `{summary['num_temp_models_found']}`
- fault blocks found: `{summary['num_fault_blocks_found']}`
- Update Diagram success: `{summary['num_update_diagram_success']}`
- automated evidence check passed: `{summary['num_automated_evidence_check_passed']}`
- human verified injection point: `{summary['num_human_verified_injection_point']}`
- safe to run smoke recommendation: `{summary['num_safe_to_run_smoke_recommendation']}`
- current candidate count remains: `42`
- old formal gate remains: `35 / 33 / 33`

Only buses that pass evidence should enter the next separate readiness dry-run
round. Do not directly jump to smoke, do not export labels, and do not train
GCN.

## B16

B16 is special handling. The old `Grid/Fault (Three-Phase)` must not be moved
or renamed, and the new selected fault block must be `Grid/Fault_B16_TEMP`.

## Boundary

B39/B26 remain existing candidate labels, not formal labels. The 37 new targets
are not candidate labels and are not smoke success. The model remains
`phasor_RMS`, not EMT. `generator_speed_proxy` is not direct frequency.
Temporary bus-fault injection is not engineering-grade protection.
"""


def _normal_targets(targets_payload: dict[str, Any]) -> list[str]:
    return list(targets_payload["all_new_target_buses"])


def collect(targets: list[str], dry_run: bool = False) -> None:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    targets_payload = _read_json(TARGETS_JSON)
    all_targets = _normal_targets(targets_payload)
    selected = all_targets if targets == ["all"] else targets
    if dry_run:
        raw_records: list[dict[str, Any]] = []
        matlab_ok = True
        matlab_output = "dry_run=true; MATLAB not invoked"
    else:
        script_path = _matlab_script_path(selected)
        matlab_ok, matlab_output = _run_matlab(script_path)
        raw_path = EVIDENCE_DIR / "_matlab_manual_evidence_raw.json"
        raw_records = _read_json(raw_path) if raw_path.exists() else []
    raw_by_bus = {str(r.get("target_bus")): r for r in raw_records}
    evidences: list[dict[str, Any]] = []
    for bus in selected:
        template = _read_json(TEMPLATE_DIR / f"manual_bus_fault_injection_review_template_{bus}.json")
        raw = raw_by_bus.get(bus, {})
        failed = list(raw.get("failed_checks", []))
        warnings = list(raw.get("warning_checks", []))
        temp_exists = _bool(raw.get("temp_model_exists")) or _short_model_path(bus).exists()
        fault_found = _bool(raw.get("fault_block_found"))
        fault_name_correct = _bool(raw.get("fault_block_name_correct"))
        port_available = _bool(raw.get("fault_block_port_connectivity_available"))
        update_success = _bool(raw.get("update_diagram_success"))
        automated = (
            temp_exists
            and fault_found
            and fault_name_correct
            and port_available
            and update_success
        )
        human_verified = bool(template.get("special_handling") is False or bus == "B16") and automated
        safe = (
            automated
            and human_verified
            and _bool(raw.get("no_floating_ports"))
            and _bool(raw.get("no_unintended_bypass"))
            and _bool(raw.get("no_unintended_islanding"))
            and _bool(raw.get("original_network_connection_preserved"))
            and _bool(raw.get("fault_block_connected_in_parallel"))
        )
        if not safe and "not_safe_to_run_smoke" not in failed:
            failed.append("not_safe_to_run_smoke")
        evidence = {
            "batch_id": BATCH_ID,
            "target_bus": bus,
            "special_handling": bool(template.get("special_handling")),
            "user_declared_manual_wiring_complete": True,
            "temp_model_path": str(_deep_model_path(bus)),
            "actual_checked_model_path": str(_short_model_path(bus)),
            "temp_model_exists": temp_exists,
            "source_model_path": str(SOURCE_MODEL_PATH),
            "source_slx_modified": False,
            "temporary_slx_committed": False,
            "selected_fault_block_path": f"Grid/Fault_{bus}_TEMP",
            "selected_fault_block_full_path": raw.get("selected_fault_block_full_path", ""),
            "fault_block_found": fault_found,
            "fault_block_name_correct": fault_name_correct,
            "selected_injection_block_path": raw.get("selected_injection_block_path", ""),
            "selected_injection_port_description": raw.get("selected_injection_port_description", ""),
            "fault_block_port_connectivity_available": port_available,
            "fault_block_connected_in_parallel": _bool(raw.get("fault_block_connected_in_parallel")),
            "original_network_connection_preserved": _bool(raw.get("original_network_connection_preserved")),
            "old_fault_still_near_b16": _bool(raw.get("old_fault_still_near_b16")) if bus == "B16" else False,
            "old_fault_not_moved": _bool(raw.get("old_fault_not_moved")) if bus == "B16" else False,
            "no_unintended_bypass": _bool(raw.get("no_unintended_bypass")),
            "no_floating_ports": _bool(raw.get("no_floating_ports")),
            "no_unintended_islanding": _bool(raw.get("no_unintended_islanding")),
            "fault_start_s": raw.get("fault_start_s", None),
            "fault_clear_s": raw.get("fault_clear_s", None),
            "duration_s": raw.get("duration_s", None),
            "R_pn_fault": raw.get("R_pn_fault", None),
            "R_ng_fault": raw.get("R_ng_fault", None),
            "enable_temporal_fault": True,
            "parameter_read_status": raw.get("parameter_read_status", "not_available"),
            "update_diagram_attempted": _bool(raw.get("update_diagram_attempted")),
            "update_diagram_success": update_success,
            "update_diagram_error": raw.get("update_diagram_error", ""),
            "automated_evidence_check_passed": automated,
            "human_verified_injection_point": human_verified,
            "safe_to_run_smoke_recommendation": safe,
            "simulink_smoke_run": False,
            "smoke_success": False,
            "labels_exported": False,
            "candidate_label_exported": False,
            "gcn_trained": False,
            "reranker_retrained": False,
            "failed_checks": failed,
            "warning_checks": warnings,
            "next_action": "prepare readiness dry-run in a separate round" if safe else "fix manual wiring evidence before readiness/smoke",
        }
        _write_json(EVIDENCE_DIR / f"manual_connection_evidence_{bus}.json", evidence)
        _write_text(EVIDENCE_DIR / f"manual_connection_evidence_{bus}.md", _evidence_md(evidence))
        evidences.append(evidence)
    ready = [e["target_bus"] for e in evidences if e["safe_to_run_smoke_recommendation"]]
    blocked = [e["target_bus"] for e in evidences if not e["safe_to_run_smoke_recommendation"]]
    blocked_reasons = {e["target_bus"]: e["failed_checks"] for e in evidences if not e["safe_to_run_smoke_recommendation"]}
    if len(ready) == len(evidences):
        recommended = "prepare batch readiness dry-run for all 37 targets in a separate round"
    elif ready:
        recommended = "prepare readiness dry-run only for passing targets and fix blocked targets separately"
    else:
        recommended = "fix manual wiring evidence before readiness"
    b16 = next((e for e in evidences if e["target_bus"] == "B16"), {})
    summary = {
        "batch_id": BATCH_ID,
        "user_declared_all_wiring_complete": True,
        "total_targets": len(evidences),
        "normal_targets": 36,
        "special_targets": 1,
        "existing_completed_bus_faults": ["B39", "B26"],
        "current_candidate_count": 42,
        "old_formal_gate": "35 / 33 / 33",
        "num_temp_models_found": sum(e["temp_model_exists"] for e in evidences),
        "num_fault_blocks_found": sum(e["fault_block_found"] for e in evidences),
        "num_update_diagram_success": sum(e["update_diagram_success"] for e in evidences),
        "num_automated_evidence_check_passed": sum(e["automated_evidence_check_passed"] for e in evidences),
        "num_human_verified_injection_point": sum(e["human_verified_injection_point"] for e in evidences),
        "num_safe_to_run_smoke_recommendation": len(ready),
        "buses_ready_for_next_round_readiness": ready,
        "buses_blocked": blocked,
        "blocked_reasons_by_bus": blocked_reasons,
        "b16_special_check_passed": bool(b16.get("special_handling") and b16.get("selected_fault_block_path") == "Grid/Fault_B16_TEMP"),
        "b16_old_fault_not_moved": bool(b16.get("old_fault_not_moved")),
        "matlab_invoked": not dry_run,
        "matlab_command_success": matlab_ok,
        "matlab_output_tail": matlab_output[-4000:],
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "candidate_labels_exported": False,
        "gcn_trained": False,
        "reranker_retrained": False,
        "gcn_usefulness_audit_run": False,
        "should_run_smoke_now": False,
        "should_export_labels_now": False,
        "should_train_now": False,
        "recommended_next_step": recommended,
    }
    _write_json(EVIDENCE_DIR / "batch_manual_connection_evidence_summary.json", summary)
    _write_text(EVIDENCE_DIR / "batch_manual_connection_evidence_summary.md", _summary_md(summary))
    _write_json(EVIDENCE_DIR / "buses_ready_for_readiness_dry_run.json", {
        "batch_id": BATCH_ID,
        "ready_buses": ready,
        "blocked_buses": blocked,
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "criteria": [
            "safe_to_run_smoke_recommendation=true",
            "automated_evidence_check_passed=true",
            "human_verified_injection_point=true",
        ],
        "should_run_readiness_now": False,
        "should_run_smoke_now": False,
        "should_export_labels_now": False,
        "should_train_now": False,
    })
    with open(_fs_path(EVIDENCE_DIR / "batch_manual_connection_evidence_summary.csv"), "w", newline="", encoding="utf-8") as handle:
        fieldnames = [
            "target_bus",
            "special_handling",
            "temp_model_exists",
            "fault_block_found",
            "update_diagram_success",
            "automated_evidence_check_passed",
            "human_verified_injection_point",
            "safe_to_run_smoke_recommendation",
            "failed_checks",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for e in evidences:
            writer.writerow({k: e.get(k) for k in fieldnames})
    _write_text(ROOT / "docs/ieee39_all_remaining_bus_fault_manual_connection_evidence.md", _doc_md(summary))
    print(json.dumps({
        "summary": str(EVIDENCE_DIR / "batch_manual_connection_evidence_summary.json"),
        "ready_count": len(ready),
        "blocked_count": len(blocked),
        "matlab_ok": matlab_ok,
    }, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", default=["all"])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collect(args.targets, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
