from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def make_mock_simulink_dynamic_results(case_manifest: str | Path, output_csv: str | Path) -> dict:
    manifest = pd.read_csv(case_manifest)
    rows = []
    for idx, item in manifest.reset_index(drop=True).iterrows():
        base = idx + 1
        opa_critical = str(item.get("opa_is_critical", "")).lower() in {"true", "1", "yes"}
        nadir = 48.7 if opa_critical else 49.4 + 0.05 * (base % 3)
        max_angle = 190.0 if base % 5 == 0 else 80.0 + 8.0 * (base % 7)
        max_loading = 1.55 if opa_critical and base % 2 == 0 else 1.05 + 0.07 * (base % 4)
        unstable = bool(nadir < 49.0 or max_angle > 180.0 or max_loading > 1.5)
        rows.append(
            {
                "case_id": item["case_id"],
                "sim_completed": True,
                "converged": True,
                "frequency_nadir_hz": float(nadir),
                "frequency_zenith_hz": float(50.25 + 0.02 * (base % 4)),
                "max_rotor_angle_separation_deg": float(max_angle),
                "max_line_loading_ratio": float(max_loading),
                "dynamic_trip_count": 2,
                "dynamic_unstable": unstable,
                "unstable_reason": _reason(nadir, max_angle, max_loading),
                "result_source": "mock",
                "mock_result": True,
                "mock_note": "Mock result for CI/no-MATLAB testing only; not a real Simulink dynamic simulation.",
            }
        )
    out = Path(output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8-sig")
    return {"output_csv": str(out), "num_cases": int(len(rows))}


def _reason(nadir: float, max_angle: float, max_loading: float) -> str:
    reasons = []
    if nadir < 49.0:
        reasons.append("frequency_nadir_below_49hz")
    if max_angle > 180.0:
        reasons.append("rotor_angle_separation_above_180deg")
    if max_loading > 1.5:
        reasons.append("line_loading_above_1p5")
    return ";".join(reasons) if reasons else "stable_by_mock_thresholds"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate mock Simulink dynamic result CSV for no-MATLAB CI tests.")
    parser.add_argument("--case-manifest", required=True)
    parser.add_argument("--output-csv", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    make_mock_simulink_dynamic_results(args.case_manifest, args.output_csv)


if __name__ == "__main__":
    main()
