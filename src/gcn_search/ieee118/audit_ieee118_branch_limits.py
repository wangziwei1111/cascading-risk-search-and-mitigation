from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from pypower.idx_brch import RATE_A, PF

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from case_adapter import build_case_adapter, run_initial_dcopf_for_case


def describe(series: pd.Series) -> dict:
    desc = pd.to_numeric(series, errors="coerce").describe()
    return {str(key): float(value) for key, value in desc.items()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit IEEE118 branch RATE_A and loading ratios.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_branch_limit_audit",
        help="Directory for branch limit audit outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = build_case_adapter("ieee118")
    raw_branch = adapter.case["branch"]
    rate_a = pd.Series(raw_branch[:, RATE_A].astype(float))
    initial = run_initial_dcopf_for_case("ieee118")
    branch_table = initial.branch_table.copy()
    loading = pd.Series(branch_table["loading_ratio"].astype(float))
    low_ratio_counts = {
        "le_0_05": int((loading <= 0.05).sum()),
        "le_0_10": int((loading <= 0.10).sum()),
        "le_0_20": int((loading <= 0.20).sum()),
    }
    max_loading = float(loading.max()) if not loading.empty else 0.0
    recommendation = (
        "PYPOWER case118 RATE_A values are uniformly 9900 MW, so initial loading ratios are very low. "
        "For OPA-style overload relay experiments, compare original RATE_A against synthetic thermal limits "
        "calibrated from base-case flows or target loading bands before drawing GCN efficiency conclusions."
    )
    summary = {
        "num_branches": int(raw_branch.shape[0]),
        "raw_branch_columns": int(raw_branch.shape[1]),
        "num_rate_a_nonpositive": int((rate_a <= 0).sum()),
        "rate_a": {
            "min": float(rate_a.min()),
            "mean": float(rate_a.mean()),
            "median": float(rate_a.median()),
            "max": float(rate_a.max()),
        },
        "initial_dcopf_branch_columns": int(initial.case["branch"].shape[1]),
        "initial_dcopf_branch_has_pf": bool(initial.case["branch"].shape[1] > PF),
        "initial_loading_ratio": {
            "min": float(loading.min()),
            "mean": float(loading.mean()),
            "median": float(loading.median()),
            "max": max_loading,
        },
        "low_loading_ratio_counts": low_ratio_counts,
        "beta_1_2_overload_unlikely_with_original_rate_a": bool(max_loading < 1.2),
        "recommendation": recommendation,
    }
    branch_table.to_csv(args.output_dir / "ieee118_initial_branch_loading.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_branch_limit_audit_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    print(f"IEEE118 branch limit audit written to {args.output_dir}")
    print(f"num_branches={summary['num_branches']}")
    print(f"rate_a_min={summary['rate_a']['min']}")
    print(f"initial_loading_ratio_max={summary['initial_loading_ratio']['max']}")


if __name__ == "__main__":
    main()
