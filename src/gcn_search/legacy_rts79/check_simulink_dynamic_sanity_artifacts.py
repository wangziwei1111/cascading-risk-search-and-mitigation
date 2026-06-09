from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def check_simulink_dynamic_sanity_artifacts(
    sanity_csv: str | Path = "results/gcn_search/simulink_dynamic_calibration/no_disturbance_sanity.csv",
    output_json: str | Path = "results/gcn_search/simulink_dynamic_calibration/sanity_summary.json",
) -> dict:
    table = pd.read_csv(sanity_csv)
    if table.empty:
        raise RuntimeError(f"Sanity CSV is empty: {sanity_csv}")
    row = table.iloc[0]
    freq_dev = max(abs(float(row["frequency_nadir_hz"]) - 50.0), abs(float(row["frequency_zenith_hz"]) - 50.0))
    angle = float(row["max_rotor_angle_separation_deg"])
    loading = float(row["max_line_loading_ratio"])
    residual = float(row.get("initial_power_balance_residual", 0.0))
    passed = freq_dev <= 0.25 and angle <= 45.0 and loading <= 2.0 and residual <= 1e-5
    summary = {
        "sanity_csv": str(sanity_csv),
        "passed": bool(passed),
        "frequency_max_deviation_hz": float(freq_dev),
        "max_rotor_angle_separation_deg": angle,
        "max_line_loading_ratio": loading,
        "initial_power_balance_residual": residual,
        "criteria": {
            "frequency_max_deviation_hz": "<= 0.25",
            "max_rotor_angle_separation_deg": "<= 45",
            "max_line_loading_ratio": "<= 2.0",
            "initial_power_balance_residual": "<= 1e-5",
        },
    }
    out = Path(output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check simplified swing no-disturbance sanity artifacts.")
    parser.add_argument("--sanity-csv", default="results/gcn_search/simulink_dynamic_calibration/no_disturbance_sanity.csv")
    parser.add_argument("--output-json", default="results/gcn_search/simulink_dynamic_calibration/sanity_summary.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_simulink_dynamic_sanity_artifacts(args.sanity_csv, args.output_json)


if __name__ == "__main__":
    main()

