from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pypower.idx_bus import PD

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
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate IEEE 118 ordered N-2 cascade full-truth rows.")
    parser.add_argument("--seeds", type=int, nargs="+", required=True, help="One or more load-scenario seeds.")
    parser.add_argument("--load-scale", type=float, default=1.0, help="Base load multiplier before seeded perturbation.")
    parser.add_argument("--beta", type=float, default=1.2, help="Relay overload threshold multiplier.")
    parser.add_argument("--security-limit", type=float, default=1.0, help="Redispatch branch security limit multiplier.")
    parser.add_argument("--max-paths", type=int, default=None, help="Optional per-scenario path cap for debugging.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_fulltruth",
        help="Directory for full-truth outputs.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume by skipping rows already in the summary CSV.")
    parser.add_argument("--checkpoint-every", type=int, default=100, help="Write partial CSV outputs every N new rows.")
    return parser.parse_args()


def apply_ieee118_load_scenario(case: dict, *, seed: int, load_scale: float) -> dict:
    scenario_case = copy_case(case)
    bus = scenario_case["bus"].copy()
    rng = np.random.default_rng(seed)
    load_factors = rng.uniform(0.9, 1.1, size=bus.shape[0])
    bus[:, PD] = bus[:, PD] * load_scale * load_factors
    scenario_case["bus"] = bus
    return scenario_case


def ordered_n2_paths(line_labels: tuple[str, ...], max_paths: int | None) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for first_line in line_labels:
        for second_line in line_labels:
            if first_line == second_line:
                continue
            paths.append((first_line, second_line))
            if max_paths is not None and len(paths) >= max_paths:
                return paths
    return paths


def row_from_state(scenario_id: int, seed: int, first_line: str, second_line: str, state: dict) -> dict:
    online = state["final_branch_table"]["status"] == 1
    final_max_loading = float(state["final_branch_table"].loc[online, "loading_ratio"].max()) if online.any() else 0.0
    island_shed = float(state["island_load_shed_mw"])
    redispatch_shed = float(state["redispatch_load_shed_mw"])
    total_shed = island_shed + redispatch_shed
    final_outages = tuple(state["final_outage_labels"])
    return {
        "scenario_id": scenario_id,
        "seed": seed,
        "path": f"{first_line}->{second_line}",
        "first_line": first_line,
        "second_line": second_line,
        "converged": bool(state["converged"]),
        "critical": bool(total_shed > 1e-7),
        "total_load_shed_mw": total_shed,
        "island_load_shed_mw": island_shed,
        "redispatch_load_shed_mw": redispatch_shed,
        "final_max_loading_ratio": final_max_loading,
        "final_outage_labels": ",".join(final_outages),
        "num_final_outages": len(final_outages),
        "error": "",
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
        "error": str(error),
    }


def write_outputs(rows: list[dict], output_dir: Path) -> None:
    table = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    summary_path = output_dir / "ieee118_fulltruth_summary.csv"
    critical_path = output_dir / "ieee118_critical_paths.csv"
    table.to_csv(summary_path, index=False, encoding="utf-8-sig")
    table[table["critical"]].to_csv(critical_path, index=False, encoding="utf-8-sig")


def load_resume_rows(summary_path: Path) -> tuple[list[dict], set[tuple[int, int, str, str]]]:
    if not summary_path.exists():
        return [], set()
    existing = pd.read_csv(summary_path)
    rows = existing.to_dict("records")
    keys = {
        (int(row["scenario_id"]), int(row["seed"]), str(row["first_line"]), str(row["second_line"]))
        for row in rows
    }
    return rows, keys


def generate_fulltruth(args: argparse.Namespace) -> pd.DataFrame:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = build_case_adapter("ieee118")
    paths = ordered_n2_paths(adapter.line_labels, args.max_paths)
    summary_path = args.output_dir / "ieee118_fulltruth_summary.csv"
    rows, completed_keys = load_resume_rows(summary_path) if args.resume else ([], set())
    new_rows_since_checkpoint = 0

    for scenario_id, seed in enumerate(args.seeds, start=1):
        scenario_case = apply_ieee118_load_scenario(adapter.case, seed=int(seed), load_scale=args.load_scale)
        first_state_cache: dict[str, dict | Exception] = {}
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
                try:
                    second_state = run_sequential_outages_for_case(
                        first_state["case"],
                        adapter,
                        [second_line],
                        beta=args.beta,
                        security_limit=args.security_limit,
                    )
                    row = row_from_state(scenario_id, int(seed), first_line, second_line, second_state)
                except Exception as exc:
                    row = error_row(scenario_id, int(seed), first_line, second_line, exc)

            rows.append(row)
            completed_keys.add(key)
            new_rows_since_checkpoint += 1
            if args.checkpoint_every > 0 and new_rows_since_checkpoint >= args.checkpoint_every:
                write_outputs(rows, args.output_dir)
                new_rows_since_checkpoint = 0

    write_outputs(rows, args.output_dir)
    config = {
        "case_name": "ieee118",
        "seeds": [int(seed) for seed in args.seeds],
        "load_scale": args.load_scale,
        "load_random_low": 0.9,
        "load_random_high": 1.1,
        "beta": args.beta,
        "security_limit": args.security_limit,
        "max_paths": args.max_paths,
        "resume": bool(args.resume),
        "checkpoint_every": args.checkpoint_every,
        "total_candidate_paths_per_scenario": len(adapter.line_labels) * (len(adapter.line_labels) - 1),
        "generated_rows": len(rows),
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
