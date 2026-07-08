from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_adapter import build_case_adapter, run_sequential_outages_for_case
from generate_ieee118_ordered_n2_fulltruth import apply_ieee118_load_scenario


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose IEEE118 full-truth error rows.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing ieee118_error_paths.csv.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for diagnosis outputs.")
    parser.add_argument("--seed", type=int, default=20260708, help="Seed used to reproduce first-step states.")
    parser.add_argument("--load-scale", type=float, default=1.0, help="Load scale used for reproduction.")
    parser.add_argument("--beta", type=float, default=1.2, help="Relay threshold used for reproduction.")
    parser.add_argument("--security-limit", type=float, default=1.0, help="Redispatch security limit used for reproduction.")
    return parser.parse_args()


def diagnose_first_steps(
    first_counts: pd.DataFrame,
    *,
    seed: int,
    load_scale: float,
    beta: float,
    security_limit: float,
) -> pd.DataFrame:
    adapter = build_case_adapter("ieee118")
    scenario_case = apply_ieee118_load_scenario(adapter.case, seed=seed, load_scale=load_scale)
    records: list[dict] = []
    for row in first_counts.itertuples(index=False):
        first_line = str(row.first_line)
        record = {"first_line": first_line, "error_count": int(row.error_count)}
        try:
            state = run_sequential_outages_for_case(
                scenario_case,
                adapter,
                [first_line],
                beta=beta,
                security_limit=security_limit,
            )
            record.update(
                {
                    "s1_reproduces_error": False,
                    "s1_error": "",
                    "s1_branch_cols": int(state["case"]["branch"].shape[1]),
                    "s1_num_final_outages": len(state["final_outage_labels"]),
                    "s1_final_outage_labels": ",".join(state["final_outage_labels"]),
                }
            )
        except Exception as exc:
            record.update(
                {
                    "s1_reproduces_error": True,
                    "s1_error": str(exc),
                    "s1_branch_cols": 0,
                    "s1_num_final_outages": 0,
                    "s1_final_outage_labels": "",
                }
            )
        records.append(record)
    return pd.DataFrame(
        records,
        columns=[
            "first_line",
            "error_count",
            "s1_reproduces_error",
            "s1_error",
            "s1_branch_cols",
            "s1_num_final_outages",
            "s1_final_outage_labels",
        ],
    )


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or args.input_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    error_path = args.input_dir / "ieee118_error_paths.csv"
    errors = pd.read_csv(error_path)
    if errors.empty:
        first_counts = pd.DataFrame(columns=["first_line", "error_count"])
        second_counts = pd.DataFrame(columns=["second_line", "error_count"])
    else:
        first_counts = errors.groupby("first_line").size().reset_index(name="error_count")
        second_counts = errors.groupby("second_line").size().reset_index(name="error_count")
    first_counts = first_counts.sort_values(["error_count", "first_line"], ascending=[False, True])
    second_counts = second_counts.sort_values(["error_count", "second_line"], ascending=[False, True])
    first_diagnosis = diagnose_first_steps(
        first_counts,
        seed=args.seed,
        load_scale=args.load_scale,
        beta=args.beta,
        security_limit=args.security_limit,
    )

    first_diagnosis.to_csv(output_dir / "ieee118_error_by_first_line.csv", index=False, encoding="utf-8-sig")
    second_counts.to_csv(output_dir / "ieee118_error_by_second_line.csv", index=False, encoding="utf-8-sig")
    summary = {
        "total_error_paths": int(len(errors)),
        "num_error_first_lines": int(first_counts.shape[0]),
        "num_error_second_lines": int(second_counts.shape[0]),
        "max_errors_per_first_line": int(first_counts["error_count"].max()) if not first_counts.empty else 0,
        "max_errors_per_second_line": int(second_counts["error_count"].max()) if not second_counts.empty else 0,
        "error_first_lines": first_counts["first_line"].astype(str).tolist(),
        "dominant_error_messages": errors["error"].fillna("").value_counts().head(10).to_dict() if "error" in errors else {},
        "s1_reproduced_error_count_after_current_fix": int(first_diagnosis["s1_reproduces_error"].sum()),
    }
    (output_dir / "ieee118_fulltruth_error_diagnosis.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"IEEE118 error diagnosis written to {output_dir}")
    print(f"total_error_paths={summary['total_error_paths']}")
    print(f"num_error_first_lines={summary['num_error_first_lines']}")
    print(f"s1_reproduced_error_count_after_current_fix={summary['s1_reproduced_error_count_after_current_fix']}")


if __name__ == "__main__":
    main()
