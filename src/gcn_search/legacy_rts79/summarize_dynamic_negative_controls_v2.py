from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def summarize_dynamic_negative_controls_v2(
    negative_control_comparison_csv: str | Path,
    threshold_sensitivity_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_negative_control_summary",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    comparison = pd.read_csv(negative_control_comparison_csv)
    sensitivity = pd.read_csv(threshold_sensitivity_csv) if Path(threshold_sensitivity_csv).exists() else pd.DataFrame()
    relaxed = _relaxed_view(sensitivity)
    rows: list[dict] = []
    learned_stress = _group_value(comparison, "learned_top20", "mean_dynamic_stress_score")
    default_all_unstable = bool(not comparison.empty and (comparison["dynamic_precision_at_20"].astype(float) == 1.0).all())
    sensitivity_signal = _sensitivity_signal(sensitivity)
    for _, row in comparison.iterrows():
        group = str(row["group"])
        relaxed_fraction = _group_value(relaxed, group, "unstable_fraction", default=float(row.get("dynamic_precision_at_20", 0.0)))
        mean_stress = float(row.get("mean_dynamic_stress_score", 0.0))
        rows.append(
            {
                "group": group,
                "num_cases": int(row.get("num_cases", 0)),
                "unstable_at_default_threshold": float(row.get("dynamic_precision_at_20", 0.0)),
                "unstable_at_relaxed_angle_threshold": relaxed_fraction,
                "mean_frequency_nadir_hz": float(row.get("mean_frequency_nadir_hz", 0.0)),
                "mean_rotor_angle_separation_coi_deg": float(row.get("mean_rotor_angle_separation_deg", 0.0)),
                "mean_dynamic_stress_score": mean_stress,
                "median_dynamic_stress_score": mean_stress,
                "security_action_fraction": float(row.get("cases_with_security_redispatch_or_load_shed", 0.0)) / max(float(row.get("num_cases", 1)), 1.0),
                "passive_trip_fraction": float(row.get("cases_with_passive_relay_trip", 0.0)) / max(float(row.get("num_cases", 1)), 1.0),
                "learned_vs_control_stress_delta": 0.0 if group == "learned_top20" else learned_stress - mean_stress,
                "discrimination_signal_under_default": False,
                "discrimination_signal_under_sensitivity": sensitivity_signal,
                "global_degeneracy_warning": default_all_unstable,
            }
        )
    table = pd.DataFrame(rows)
    csv_path = out / "dynamic_negative_control_v2_summary.csv"
    json_path = out / "dynamic_negative_control_v2_summary.json"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    payload = {
        "global_degeneracy_warning": default_all_unstable,
        "dynamic_discrimination_signal": bool(sensitivity_signal and not default_all_unstable),
        "threshold_sensitivity_discrimination_signal": bool(sensitivity_signal),
        "num_groups": int(len(table)),
        "interpretation": "negative controls v2 summary; no dynamic recall is reported",
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), **payload}


def _relaxed_view(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return table
    relaxed = table[(table["frequency_threshold_hz"].astype(float) == 48.0) & (table["rotor_angle_threshold_deg"].astype(float) == 720.0)]
    if relaxed.empty:
        relaxed = table.sort_values(["frequency_threshold_hz", "rotor_angle_threshold_deg"]).groupby("group", as_index=False).tail(1)
    return relaxed


def _sensitivity_signal(table: pd.DataFrame) -> bool:
    if table.empty:
        return False
    for _, sub in table.groupby(["frequency_threshold_hz", "rotor_angle_threshold_deg"]):
        if "learned_top20" not in set(sub["group"]):
            continue
        learned = float(sub.loc[sub["group"] == "learned_top20", "unstable_fraction"].iloc[0])
        controls = sub.loc[sub["group"] != "learned_top20", "unstable_fraction"].astype(float)
        if len(controls) and learned > controls.max():
            return True
    return False


def _group_value(table: pd.DataFrame, group: str, col: str, default: float = 0.0) -> float:
    if table.empty or col not in table.columns or "group" not in table.columns:
        return default
    sub = table.loc[table["group"].astype(str) == group, col]
    if sub.empty:
        return default
    return float(sub.iloc[0])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize dynamic negative controls with stress and threshold sensitivity.")
    parser.add_argument("--negative-control-comparison-csv", required=True)
    parser.add_argument("--threshold-sensitivity-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_negative_control_summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summarize_dynamic_negative_controls_v2(args.negative_control_comparison_csv, args.threshold_sensitivity_csv, args.output_dir)


if __name__ == "__main__":
    main()
