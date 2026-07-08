from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pypower.idx_brch import PF, RATE_A
from pypower.idx_bus import PD
from pypower.ppoption import ppoption
from pypower.rundcopf import rundcopf

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from case_adapter import build_case_adapter, run_sequential_outages_for_case
from rts79_cascade import copy_case


OUTPUT_COLUMNS = [
    "scenario_id",
    "seed",
    "path",
    "first_line",
    "second_line",
    "converged",
    "critical",
    "total_load_shed_mw",
    "island_load_shed_mw",
    "redispatch_load_shed_mw",
    "final_max_loading_ratio",
    "final_outage_labels",
    "num_final_outages",
    "max_event_loading_ratio",
    "max_pre_redispatch_loading_ratio",
    "num_relay_trips",
    "relay_trip_labels",
    "num_passive_outages",
    "has_overload_cascade",
    "critical_mechanism",
    "error",
    "first_step_critical",
    "first_step_total_load_shed_mw",
    "valid_ordered_n2",
    "skip_reason",
]

FIRST_STEP_COLUMNS = [
    "scenario_id",
    "seed",
    "first_line",
    "first_step_converged",
    "first_step_critical",
    "first_step_total_load_shed_mw",
    "first_step_island_load_shed_mw",
    "first_step_redispatch_load_shed_mw",
    "first_step_final_outage_labels",
    "first_step_num_relay_trips",
    "first_step_relay_trip_labels",
    "first_step_critical_mechanism",
    "num_skipped_second_lines",
    "skip_reason",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate IEEE 118 ordered N-2 cascade full-truth rows.")
    parser.add_argument("--seeds", type=int, nargs="+", required=True, help="One or more load-scenario seeds.")
    parser.add_argument("--load-scale", type=float, default=1.0, help="Base load multiplier before seeded perturbation.")
    parser.add_argument("--beta", type=float, default=1.2, help="Relay overload threshold multiplier.")
    parser.add_argument("--security-limit", type=float, default=1.0, help="Redispatch branch security limit multiplier.")
    parser.add_argument(
        "--limit-mode",
        choices=["original_rate_a", "flow_scaled"],
        default="original_rate_a",
        help="Thermal limit mode for IEEE118 branches.",
    )
    parser.add_argument("--flow-limit-scale", type=float, default=1.3, help="Multiplier for abs(PF0) in flow_scaled mode.")
    parser.add_argument("--min-rate-a", type=float, default=25.0, help="Minimum RATE_A in flow_scaled mode.")
    parser.add_argument("--max-paths", type=int, default=None, help="Optional per-scenario path cap for debugging.")
    parser.add_argument(
        "--sample-mode",
        choices=["first", "random"],
        default="first",
        help="Path sampling mode. 'first' preserves ordered truncation; 'random' samples without replacement.",
    )
    parser.add_argument("--sample-size", type=int, default=None, help="Number of ordered N-2 paths to sample per scenario.")
    parser.add_argument("--sample-seed", type=int, default=None, help="Random seed for --sample-mode random.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_fulltruth",
        help="Directory for full-truth outputs.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume by skipping rows already in the summary CSV.")
    parser.add_argument("--retry-errors", action="store_true", help="With --resume, recompute rows whose error field is non-empty.")
    parser.add_argument("--checkpoint-every", type=int, default=100, help="Write partial CSV outputs every N new rows.")
    parser.add_argument(
        "--first-step-critical-policy",
        choices=["skip", "expand"],
        default="skip",
        help="Skip second outages when the first outage is already critical, or expand for historical no-early-stop runs.",
    )
    return parser.parse_args(argv)


def apply_ieee118_load_scenario(case: dict, *, seed: int, load_scale: float) -> dict:
    scenario_case = copy_case(case)
    bus = scenario_case["bus"].copy()
    rng = np.random.default_rng(seed)
    load_factors = rng.uniform(0.9, 1.1, size=bus.shape[0])
    bus[:, PD] = bus[:, PD] * load_scale * load_factors
    scenario_case["bus"] = bus
    return scenario_case


def apply_thermal_limit_mode(
    case: dict,
    *,
    limit_mode: str,
    flow_limit_scale: float,
    min_rate_a: float,
) -> dict:
    if limit_mode == "original_rate_a":
        return copy_case(case)
    if limit_mode != "flow_scaled":
        raise ValueError(f"Unsupported limit_mode={limit_mode!r}")
    result = rundcopf(copy_case(case), ppoption(VERBOSE=0, OUT_ALL=0))
    if not result["success"]:
        raise RuntimeError("IEEE118 initial DCOPF failed while calibrating flow_scaled thermal limits")
    branch = result["branch"].copy()
    pf0 = np.abs(branch[:, PF].astype(float))
    branch[:, RATE_A] = np.maximum(flow_limit_scale * pf0, float(min_rate_a))
    result["branch"] = branch
    return result


def all_ordered_n2_paths(line_labels: tuple[str, ...]) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for first_line in line_labels:
        for second_line in line_labels:
            if first_line == second_line:
                continue
            paths.append((first_line, second_line))
    return paths


def select_ordered_n2_paths(
    line_labels: tuple[str, ...],
    *,
    max_paths: int | None,
    sample_mode: str,
    sample_size: int | None,
    sample_seed: int | None,
) -> list[tuple[str, str]]:
    paths = all_ordered_n2_paths(line_labels)
    if sample_size is not None and sample_size < 0:
        raise ValueError("--sample-size must be non-negative")
    if max_paths is not None and max_paths < 0:
        raise ValueError("--max-paths must be non-negative")

    if sample_mode == "first":
        limit = sample_size if sample_size is not None else max_paths
        return paths[:limit] if limit is not None else paths
    if sample_mode == "random":
        if sample_size is None:
            raise ValueError("--sample-size is required when --sample-mode random")
        sample_count = min(sample_size, len(paths))
        rng = np.random.default_rng(sample_seed)
        indices = rng.choice(len(paths), size=sample_count, replace=False)
        return [paths[int(index)] for index in indices]
    raise ValueError(f"Unsupported sample_mode={sample_mode!r}")


def summarize_state(state: dict, active_outage_labels: set[str] | None = None) -> dict:
    online = state["final_branch_table"]["status"] == 1
    final_max_loading = float(state["final_branch_table"].loc[online, "loading_ratio"].max()) if online.any() else 0.0
    island_shed = float(state["island_load_shed_mw"])
    redispatch_shed = float(state["redispatch_load_shed_mw"])
    total_shed = island_shed + redispatch_shed
    final_outages = tuple(state["final_outage_labels"])
    event_table = state["event_table"]
    relay_table = state["relay_trip_detail_table"]
    max_event_loading = (
        float(pd.to_numeric(event_table["max_loading_ratio"], errors="coerce").max())
        if not event_table.empty and "max_loading_ratio" in event_table
        else final_max_loading
    )
    relay_trip_labels = (
        tuple(sorted(relay_table["line_label"].dropna().astype(str).unique()))
        if not relay_table.empty and "line_label" in relay_table
        else tuple()
    )
    num_relay_trips = int(len(relay_table)) if not relay_table.empty else 0
    num_passive_outages = max(len(final_outages) - len(active_outage_labels or set()), 0)
    has_overload_cascade = num_relay_trips > 0
    if total_shed <= 1e-7:
        critical_mechanism = "non_critical"
    elif has_overload_cascade:
        critical_mechanism = "relay_cascade"
    else:
        critical_mechanism = "island_only"
    return {
        "converged": bool(state["converged"]),
        "critical": bool(total_shed > 1e-7),
        "total_load_shed_mw": total_shed,
        "island_load_shed_mw": island_shed,
        "redispatch_load_shed_mw": redispatch_shed,
        "final_max_loading_ratio": final_max_loading,
        "final_outage_labels": ",".join(final_outages),
        "num_final_outages": len(final_outages),
        "max_event_loading_ratio": max_event_loading,
        "max_pre_redispatch_loading_ratio": max_event_loading,
        "num_relay_trips": num_relay_trips,
        "relay_trip_labels": ",".join(relay_trip_labels),
        "num_passive_outages": num_passive_outages,
        "has_overload_cascade": has_overload_cascade,
        "critical_mechanism": critical_mechanism,
    }


def row_from_state(
    scenario_id: int,
    seed: int,
    first_line: str,
    second_line: str,
    state: dict,
    *,
    first_step_summary: dict | None = None,
) -> dict:
    summary = summarize_state(state, {first_line, second_line})
    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "path": f"{first_line}->{second_line}",
        "first_line": first_line,
        "second_line": second_line,
        **summary,
        "error": "",
        "first_step_critical": bool(first_step_summary.get("first_step_critical", False)) if first_step_summary else False,
        "first_step_total_load_shed_mw": float(first_step_summary.get("first_step_total_load_shed_mw", 0.0)) if first_step_summary else 0.0,
        "valid_ordered_n2": True,
        "skip_reason": "",
    }


def first_step_row_from_state(
    scenario_id: int,
    seed: int,
    first_line: str,
    state: dict,
    *,
    num_second_candidates: int,
    skipped: bool,
) -> dict:
    summary = summarize_state(state, {first_line})
    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "first_line": first_line,
        "first_step_converged": bool(summary["converged"]),
        "first_step_critical": bool(summary["critical"]),
        "first_step_total_load_shed_mw": float(summary["total_load_shed_mw"]),
        "first_step_island_load_shed_mw": float(summary["island_load_shed_mw"]),
        "first_step_redispatch_load_shed_mw": float(summary["redispatch_load_shed_mw"]),
        "first_step_final_outage_labels": str(summary["final_outage_labels"]),
        "first_step_num_relay_trips": int(summary["num_relay_trips"]),
        "first_step_relay_trip_labels": str(summary["relay_trip_labels"]),
        "first_step_critical_mechanism": str(summary["critical_mechanism"]),
        "num_skipped_second_lines": int(num_second_candidates if skipped else 0),
        "skip_reason": "first_step_critical" if skipped else "",
    }


def error_row(scenario_id: int, seed: int, first_line: str, second_line: str, error: Exception | str) -> dict:
    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "path": f"{first_line}->{second_line}",
        "first_line": first_line,
        "second_line": second_line,
        "converged": False,
        "critical": False,
        "total_load_shed_mw": np.nan,
        "island_load_shed_mw": np.nan,
        "redispatch_load_shed_mw": np.nan,
        "final_max_loading_ratio": np.nan,
        "final_outage_labels": "",
        "num_final_outages": 0,
        "max_event_loading_ratio": np.nan,
        "max_pre_redispatch_loading_ratio": np.nan,
        "num_relay_trips": 0,
        "relay_trip_labels": "",
        "num_passive_outages": 0,
        "has_overload_cascade": False,
        "critical_mechanism": "error",
        "error": str(error),
        "first_step_critical": False,
        "first_step_total_load_shed_mw": np.nan,
        "valid_ordered_n2": False,
        "skip_reason": "error",
    }


def write_outputs(rows: list[dict], output_dir: Path, first_step_rows: list[dict] | None = None) -> None:
    table = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    summary_path = output_dir / "ieee118_fulltruth_summary.csv"
    critical_path = output_dir / "ieee118_critical_paths.csv"
    table.to_csv(summary_path, index=False, encoding="utf-8-sig")
    table[table["critical"]].to_csv(critical_path, index=False, encoding="utf-8-sig")
    if first_step_rows is not None:
        pd.DataFrame(first_step_rows, columns=FIRST_STEP_COLUMNS).to_csv(
            output_dir / "ieee118_first_step_summary.csv",
            index=False,
            encoding="utf-8-sig",
        )


def load_resume_rows(summary_path: Path, retry_errors: bool = False) -> tuple[list[dict], set[tuple[int, int, str, str]]]:
    if not summary_path.exists():
        return [], set()
    existing = pd.read_csv(summary_path)
    if retry_errors and "error" in existing:
        error_mask = existing["error"].fillna("").astype(str).str.len() > 0
        existing = existing.loc[~error_mask].copy()
    rows = existing.to_dict("records")
    keys = {
        (int(row["scenario_id"]), int(row["seed"]), str(row["first_line"]), str(row["second_line"]))
        for row in rows
    }
    return rows, keys


def load_resume_first_step_rows(output_dir: Path) -> list[dict]:
    path = output_dir / "ieee118_first_step_summary.csv"
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict("records")


def generate_fulltruth(args: argparse.Namespace) -> pd.DataFrame:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = build_case_adapter("ieee118")
    paths = select_ordered_n2_paths(
        adapter.line_labels,
        max_paths=args.max_paths,
        sample_mode=args.sample_mode,
        sample_size=args.sample_size,
        sample_seed=args.sample_seed,
    )
    summary_path = args.output_dir / "ieee118_fulltruth_summary.csv"
    rows, completed_keys = load_resume_rows(summary_path, retry_errors=args.retry_errors) if args.resume else ([], set())
    first_step_rows: list[dict] = load_resume_first_step_rows(args.output_dir) if args.resume else []
    new_rows_since_checkpoint = 0

    for scenario_id, seed in enumerate(args.seeds, start=1):
        scenario_case = apply_ieee118_load_scenario(adapter.case, seed=int(seed), load_scale=args.load_scale)
        scenario_case = apply_thermal_limit_mode(
            scenario_case,
            limit_mode=args.limit_mode,
            flow_limit_scale=args.flow_limit_scale,
            min_rate_a=args.min_rate_a,
        )
        first_state_cache: dict[str, dict | Exception] = {}
        first_step_summary_by_line: dict[str, dict] = {
            str(row["first_line"]): row
            for row in first_step_rows
            if int(row.get("scenario_id", scenario_id)) == scenario_id and int(row.get("seed", seed)) == int(seed)
        }
        skipped_first_lines: set[str] = {
            line
            for line, row in first_step_summary_by_line.items()
            if args.first_step_critical_policy == "skip"
            and str(row.get("first_step_critical", False)).strip().lower() in {"true", "1", "yes"}
        }
        paths_by_first: dict[str, list[str]] = {}
        for first_line, second_line in paths:
            paths_by_first.setdefault(first_line, []).append(second_line)
        for first_line, second_line in paths:
            key = (scenario_id, int(seed), first_line, second_line)
            if key in completed_keys:
                continue

            if first_line not in first_state_cache:
                try:
                    first_state_cache[first_line] = run_sequential_outages_for_case(
                        scenario_case,
                        adapter,
                        [first_line],
                        beta=args.beta,
                        security_limit=args.security_limit,
                    )
                except Exception as exc:
                    first_state_cache[first_line] = exc

            first_state = first_state_cache[first_line]
            if isinstance(first_state, Exception):
                row = error_row(scenario_id, int(seed), first_line, second_line, first_state)
            else:
                if first_line not in first_step_summary_by_line:
                    first_summary_row = first_step_row_from_state(
                        scenario_id,
                        int(seed),
                        first_line,
                        first_state,
                        num_second_candidates=len(paths_by_first.get(first_line, [])),
                        skipped=bool(summarize_state(first_state, {first_line})["critical"] and args.first_step_critical_policy == "skip"),
                    )
                    first_step_summary_by_line[first_line] = first_summary_row
                    first_step_rows.append(first_summary_row)
                    if first_summary_row["first_step_critical"] and args.first_step_critical_policy == "skip":
                        skipped_first_lines.add(first_line)

                if first_line in skipped_first_lines:
                    continue

                try:
                    second_state = run_sequential_outages_for_case(
                        first_state["case"],
                        adapter,
                        [second_line],
                        beta=args.beta,
                        security_limit=args.security_limit,
                    )
                    row = row_from_state(
                        scenario_id,
                        int(seed),
                        first_line,
                        second_line,
                        second_state,
                        first_step_summary=first_step_summary_by_line.get(first_line),
                    )
                except Exception as exc:
                    row = error_row(scenario_id, int(seed), first_line, second_line, exc)

            rows.append(row)
            completed_keys.add(key)
            new_rows_since_checkpoint += 1
            if args.checkpoint_every > 0 and new_rows_since_checkpoint >= args.checkpoint_every:
                write_outputs(rows, args.output_dir, first_step_rows)
                new_rows_since_checkpoint = 0

    write_outputs(rows, args.output_dir, first_step_rows)
    config = {
        "case_name": "ieee118",
        "seeds": [int(seed) for seed in args.seeds],
        "load_scale": args.load_scale,
        "load_random_low": 0.9,
        "load_random_high": 1.1,
        "beta": args.beta,
        "security_limit": args.security_limit,
        "limit_mode": args.limit_mode,
        "flow_limit_scale": args.flow_limit_scale,
        "min_rate_a": args.min_rate_a,
        "max_paths": args.max_paths,
        "sample_mode": args.sample_mode,
        "sample_size": args.sample_size,
        "sample_seed": args.sample_seed,
        "selected_paths_per_scenario": len(paths),
        "resume": bool(args.resume),
        "retry_errors": bool(args.retry_errors),
        "checkpoint_every": args.checkpoint_every,
        "first_step_critical_policy": args.first_step_critical_policy,
        "total_candidate_paths_per_scenario": len(adapter.line_labels) * (len(adapter.line_labels) - 1),
        "generated_rows": len(rows),
        "num_first_step_rows": len(first_step_rows),
        "num_first_step_critical_lines": int(sum(bool(row["first_step_critical"]) for row in first_step_rows)),
        "num_skipped_ordered_n2_paths": int(sum(int(row["num_skipped_second_lines"]) for row in first_step_rows)),
    }
    (args.output_dir / "ieee118_fulltruth_config.json").write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )
    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> None:
    args = parse_args()
    table = generate_fulltruth(args)
    print(f"IEEE 118 full-truth rows written to {args.output_dir / 'ieee118_fulltruth_summary.csv'}")
    print(f"num_rows={len(table)}")
    print(f"num_converged={int(table['converged'].sum()) if not table.empty else 0}")
    print(f"num_critical={int(table['critical'].sum()) if not table.empty else 0}")


if __name__ == "__main__":
    main()
