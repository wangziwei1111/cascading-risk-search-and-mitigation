"""Prepare ignored IEEE39 temporary lab-copy plans for bus-fault injection."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _bool_from_inventory(path: Path, key: str) -> bool:
    if not path.exists():
        return False
    try:
        return bool(json.loads(path.read_text(encoding="utf-8")).get(key, False))
    except Exception:
        return False


def temp_model_path(output_dir: Path, target_bus: str) -> Path:
    return (
        output_dir
        / "local_lab_copies"
        / f"IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{target_bus}_TEMP_LOCAL_ONLY.slx"
    )


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    source = args.source_model if args.source_model.is_absolute() else ROOT / args.source_model
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    temp_model = temp_model_path(output_dir, args.target_bus)
    duration = max(0.0, float(args.fault_clear_s) - float(args.fault_start_s))
    copied = False
    if not source.exists():
        raise FileNotFoundError(f"source model not found: {source}")
    if args.allow_local_slx_copy and not args.dry_run:
        temp_model.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, temp_model)
        copied = True
    return {
        "preview_only": True,
        "target_bus": args.target_bus,
        "source_model_path": _rel(source),
        "temporary_model_path": _rel(temp_model),
        "temporary_model_exists": temp_model.exists(),
        "temporary_model_copied_this_run": copied,
        "temporary_model_is_ignored": True,
        "source_slx_modified": False,
        "source_slx_committed": False,
        "temporary_slx_committed": False,
        "fault_start_s": float(args.fault_start_s),
        "fault_clear_s": float(args.fault_clear_s),
        "duration_s": duration,
        "proposed_injection_strategy": "temporary_lab_copy_bus_terminal_inventory_then_manual_review",
        "manual_review_required": True,
        "do_not_commit_temporary_slx": True,
        "dry_run": bool(args.dry_run),
        "allow_local_slx_copy": bool(args.allow_local_slx_copy),
        "formal_label_gate": "35 / 33 / 33",
        "v2_candidate_count": 40,
        "reranker_retrained": False,
        "gcn_trained": False,
        "labels_exported": False,
        "l12_touched": False,
        "notes": [
            "Source .slx is read-only for this workflow.",
            "Temporary .slx, if copied, is local/ignored and must not be committed.",
            "Smoke is allowed only after MATLAB inventory reports safe_to_run_smoke=true.",
        ],
    }


def write_plan(plan: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    plan_dir = output_dir / "temp_lab_plans"
    target = str(plan["target_bus"])
    json_path = plan_dir / f"ieee39_bus_fault_temp_lab_{target}_plan.json"
    md_path = plan_dir / f"ieee39_bus_fault_temp_lab_{target}_plan.md"
    _write_json(json_path, plan)
    lines = [
        f"# IEEE39 Bus-Fault Temporary Lab Plan {target}",
        "",
        "This is a temporary lab-copy injection plan only. It does not train GCN, does not retrain the reranker, does not export labels, and does not update label gates.",
        "",
        f"- target_bus: `{plan['target_bus']}`",
        f"- source_model_path: `{plan['source_model_path']}`",
        f"- temporary_model_path: `{plan['temporary_model_path']}`",
        f"- temporary_model_is_ignored: `{plan['temporary_model_is_ignored']}`",
        f"- source_slx_modified: `{plan['source_slx_modified']}`",
        f"- source_slx_committed: `{plan['source_slx_committed']}`",
        f"- temporary_slx_committed: `{plan['temporary_slx_committed']}`",
        f"- fault_start_s: `{plan['fault_start_s']}`",
        f"- fault_clear_s: `{plan['fault_clear_s']}`",
        f"- duration_s: `{plan['duration_s']}`",
        f"- manual_review_required: `{plan['manual_review_required']}`",
        "",
        "The model remains phasor_RMS, not EMT. `generator_speed_proxy` is not direct frequency. relay proxy / handwired breaker is not engineering-grade protection.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def write_feasibility_summary(output_dir: Path) -> tuple[Path, Path]:
    plan_dir = output_dir / "temp_lab_plans"
    plans = sorted(plan_dir.glob("ieee39_bus_fault_temp_lab_B*_plan.json"))
    attempted: list[str] = []
    found: list[str] = []
    safe: list[str] = []
    smoke_successful: list[str] = []
    smoke_failed: list[str] = []
    for plan_path in plans:
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        bus = str(plan["target_bus"])
        attempted.append(bus)
        inv_path = plan_dir / f"matlab_bus_fault_injection_inventory_{bus}.json"
        if _bool_from_inventory(inv_path, "injection_point_found"):
            found.append(bus)
        if _bool_from_inventory(inv_path, "safe_to_run_smoke"):
            safe.append(bus)
    payload = {
        "preview_only": True,
        "target_buses_attempted": attempted,
        "target_buses_with_injection_point_found": found,
        "target_buses_safe_to_run_smoke": safe,
        "target_buses_smoke_successful": smoke_successful,
        "target_buses_smoke_failed": smoke_failed,
        "source_slx_modified": False,
        "source_slx_committed": False,
        "temporary_slx_committed": False,
        "formal_label_gate_changed": False,
        "old_formal_gate": "35 / 33 / 33",
        "v2_candidate_count_changed": False,
        "v2_candidate_count": 40,
        "reranker_retrained": False,
        "gcn_trained": False,
        "labels_exported": False,
        "l12_touched": False,
        "recommended_next_step": (
            "Run temp lab smoke only for buses marked safe_to_run_smoke=true."
            if safe
            else "Manual Simulink review is needed to locate a safe bus injection point; do not train."
        ),
    }
    json_path = plan_dir / "ieee39_bus_fault_temp_lab_feasibility_summary.json"
    md_path = plan_dir / "ieee39_bus_fault_temp_lab_feasibility_summary.md"
    _write_json(json_path, payload)
    lines = [
        "# IEEE39 Bus-Fault Temporary Lab Feasibility Summary",
        "",
        f"- target_buses_attempted: `{', '.join(attempted) if attempted else 'none'}`",
        f"- target_buses_with_injection_point_found: `{', '.join(found) if found else 'none'}`",
        f"- target_buses_safe_to_run_smoke: `{', '.join(safe) if safe else 'none'}`",
        "- source_slx_modified: `false`",
        "- source_slx_committed: `false`",
        "- temporary_slx_committed: `false`",
        "- formal label gate: `35 / 33 / 33`",
        "- v2 candidate count: `40`",
        "- reranker_retrained: `false`",
        "- gcn_trained: `false`",
        "- labels_exported: `false`",
        "- L12 touched: `false`",
        "",
        payload["recommended_next_step"],
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-model", type=Path, required=True)
    parser.add_argument("--target-bus", required=True, choices=["B39", "B26"])
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--fault-start-s", type=float, default=0.50)
    parser.add_argument("--fault-clear-s", type=float, default=0.58)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-local-slx-copy", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    plan = build_plan(args)
    plan_json, plan_md = write_plan(plan, out)
    summary_json, summary_md = write_feasibility_summary(out)
    print(
        json.dumps(
            {
                "plan_json": _rel(plan_json),
                "plan_md": _rel(plan_md),
                "summary_json": _rel(summary_json),
                "summary_md": _rel(summary_md),
                "temporary_model_copied_this_run": plan["temporary_model_copied_this_run"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
