from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


FREQUENCY_THRESHOLDS = [48.0, 48.5, 49.0, 49.5]
ANGLE_THRESHOLDS = [180, 360, 540, 720, 900]


def analyze_dynamic_threshold_sensitivity(
    negative_control_results_root: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_threshold_sensitivity",
    frequency_thresholds: list[float] | None = None,
    angle_thresholds: list[float] | None = None,
) -> dict:
    root = Path(negative_control_results_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    frequency_thresholds = frequency_thresholds or FREQUENCY_THRESHOLDS
    angle_thresholds = angle_thresholds or ANGLE_THRESHOLDS
    rows: list[dict] = []
    for csv_path in sorted(root.glob("*/simulink_dynamic_simulation_results.csv")):
        group = csv_path.parent.name
        table = pd.read_csv(csv_path)
        freq = pd.to_numeric(table.get("frequency_nadir_hz", 50.0), errors="coerce").fillna(50.0)
        angle_col = "max_rotor_angle_separation_coi_deg" if "max_rotor_angle_separation_coi_deg" in table.columns else "max_rotor_angle_separation_deg"
        angle = pd.to_numeric(table.get(angle_col, 0.0), errors="coerce").fillna(0.0)
        stress = _stress(table, freq, angle)
        for fthr in frequency_thresholds:
            for athr in angle_thresholds:
                unstable = (freq < fthr) | (angle > athr)
                rows.append(
                    {
                        "group": group,
                        "frequency_threshold_hz": float(fthr),
                        "rotor_angle_threshold_deg": float(athr),
                        "num_cases": int(len(table)),
                        "unstable_count": int(unstable.sum()),
                        "unstable_fraction": float(unstable.mean()) if len(table) else 0.0,
                        "mean_frequency_nadir_hz": float(freq.mean()) if len(table) else 0.0,
                        "mean_rotor_angle_separation_coi_deg": float(angle.mean()) if len(table) else 0.0,
                        "mean_dynamic_stress_score": float(stress.mean()) if len(table) else 0.0,
                    }
                )
    result = pd.DataFrame(rows)
    csv_out = out / "dynamic_threshold_sensitivity.csv"
    json_out = out / "dynamic_threshold_sensitivity_summary.json"
    result.to_csv(csv_out, index=False, encoding="utf-8-sig")
    summary = _summary(result)
    json_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_out), "json": str(json_out), **summary}


def _stress(table: pd.DataFrame, freq: pd.Series, angle: pd.Series) -> pd.Series:
    loading = pd.to_numeric(table.get("max_line_loading_ratio", 0.0), errors="coerce").fillna(0.0)
    shed = pd.to_numeric(table.get("dynamic_load_shed_mw", 0.0), errors="coerce").fillna(0.0)
    relay = pd.to_numeric(table.get("passive_relay_trip_count", 0.0), errors="coerce").fillna(0.0)
    return (49.5 - freq).clip(lower=0) + (angle / 180.0 - 1).clip(lower=0) + (loading - 1).clip(lower=0) + shed / max(float(shed.max()), 1.0) + relay


def _summary(table: pd.DataFrame) -> dict:
    if table.empty:
        return {
            "num_threshold_cases": 0,
            "all_groups_unstable_for_all_thresholds": False,
            "has_threshold_discrimination_signal": False,
            "interpretation": "threshold sensitivity only; not a formal dynamic conclusion",
        }
    grouped = table.groupby(["frequency_threshold_hz", "rotor_angle_threshold_deg"])
    all_unstable_all = bool((table["unstable_fraction"].astype(float) == 1.0).all())
    signal = False
    for _, sub in grouped:
        if "learned_top20" not in set(sub["group"]):
            continue
        learned = float(sub.loc[sub["group"] == "learned_top20", "unstable_fraction"].iloc[0])
        controls = sub.loc[sub["group"] != "learned_top20", "unstable_fraction"].astype(float)
        if len(controls) and learned > controls.max():
            signal = True
            break
    return {
        "num_threshold_cases": int(len(table)),
        "all_groups_unstable_for_all_thresholds": all_unstable_all,
        "has_threshold_discrimination_signal": signal,
        "interpretation": "threshold sensitivity only; not a formal dynamic conclusion",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan dynamic instability threshold sensitivity for negative-control groups.")
    parser.add_argument("--negative-control-results-root", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_threshold_sensitivity")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_dynamic_threshold_sensitivity(args.negative_control_results_root, args.output_dir)


if __name__ == "__main__":
    main()
