from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def analyze_swing_equilibrium_diagnostics(
    summary_json: str | Path | None = None,
    dynamic_result_csv: str | Path | None = None,
    trajectory_summary_csv: str | Path | None = None,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_equilibrium_diagnostics",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = _load_summary(summary_json)
    result = _load_first_row(dynamic_result_csv)
    trajectory = pd.read_csv(trajectory_summary_csv) if trajectory_summary_csv else pd.DataFrame()

    frequency_nadir = _first_number(summary, result, "no_trip_frequency_nadir_hz", "frequency_nadir_hz", 50.0)
    frequency_zenith = _first_number(summary, result, "no_trip_frequency_zenith_hz", "frequency_zenith_hz", 50.0)
    final_mean_frequency = _first_number(summary, result, "no_trip_final_mean_frequency_hz", "final_mean_frequency_hz", frequency_nadir)
    max_angle_coi = _first_number(
        summary,
        result,
        "no_trip_max_rotor_angle_separation_coi_deg",
        "max_rotor_angle_separation_coi_deg",
        _first_number(summary, result, "no_trip_max_rotor_angle_separation_deg", "max_rotor_angle_separation_deg", 0.0),
    )
    frequency_drift = _first_number(summary, result, "pre_event_frequency_drift_hz_per_s", "frequency_drift_hz_per_s", _frequency_drift(trajectory))
    angle_growth = _first_number(summary, result, "pre_event_angle_spread_growth_deg_per_s", "angle_spread_growth_deg_per_s", _angle_growth(trajectory))
    residual_norm = _first_number(summary, result, "initial_pm_pe_residual_norm", "initial_pm_pe_residual_norm", 0.0)
    residual_max = _first_number(summary, result, "initial_pm_pe_max_abs_residual", "initial_pm_pe_max_abs_residual", 0.0)

    no_trip_unstable = _first_bool(summary, result, "no_trip_dynamic_unstable", "dynamic_unstable", False)
    sanity_passed = bool(
        not no_trip_unstable
        and frequency_nadir >= 49.8
        and frequency_zenith <= 50.2
        and max_angle_coi <= 60.0
        and residual_max <= 1e-3
    )
    diagnostics = {
        "no_trip_dynamic_unstable": no_trip_unstable,
        "no_trip_frequency_nadir_hz": frequency_nadir,
        "no_trip_frequency_zenith_hz": frequency_zenith,
        "no_trip_final_mean_frequency_hz": final_mean_frequency,
        "no_trip_max_rotor_angle_separation_deg": _first_number(summary, result, "no_trip_max_rotor_angle_separation_deg", "max_rotor_angle_separation_deg", max_angle_coi),
        "no_trip_max_rotor_angle_separation_coi_deg": max_angle_coi,
        "pre_event_frequency_drift_hz_per_s": frequency_drift,
        "pre_event_angle_spread_growth_deg_per_s": angle_growth,
        "initial_pm_pe_residual_norm": residual_norm,
        "initial_pm_pe_max_abs_residual": residual_max,
        "mean_pm": _first_number(summary, result, "mean_pm", "mean_pm", 0.0),
        "mean_pe": _first_number(summary, result, "mean_pe", "mean_pe", 0.0),
        "total_load_mw": _first_number(summary, result, "total_load_mw", "total_load_mw", 0.0),
        "total_generation_mw": _first_number(summary, result, "total_generation_mw", "total_generation_mw", 0.0),
        "sanity_passed": sanity_passed,
        "dynamic_model_equilibrium_failed": not sanity_passed,
    }
    csv_path = out / "swing_equilibrium_diagnostics.csv"
    json_path = out / "swing_equilibrium_diagnostics.json"
    pd.DataFrame([diagnostics]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2), encoding="utf-8")
    return diagnostics


def _load_summary(path: str | Path | None) -> dict:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


def _load_first_row(path: str | Path | None) -> dict:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    table = pd.read_csv(file_path)
    if table.empty:
        return {}
    return table.iloc[0].to_dict()


def _first_number(summary: dict, row: dict, summary_key: str, row_key: str, default: float) -> float:
    value = summary.get(summary_key, row.get(row_key, default))
    try:
        if pd.isna(value):
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _first_bool(summary: dict, row: dict, summary_key: str, row_key: str, default: bool) -> bool:
    value = summary.get(summary_key, row.get(row_key, default))
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _frequency_drift(trajectory: pd.DataFrame) -> float:
    if trajectory.empty or not {"time_s", "frequency_hz"}.issubset(trajectory.columns):
        return 0.0
    grouped = trajectory.groupby("time_s")["frequency_hz"].mean().reset_index()
    if len(grouped) < 2:
        return 0.0
    dt = float(grouped["time_s"].iloc[-1] - grouped["time_s"].iloc[0])
    return float((grouped["frequency_hz"].iloc[-1] - grouped["frequency_hz"].iloc[0]) / max(dt, 1e-9))


def _angle_growth(trajectory: pd.DataFrame) -> float:
    if trajectory.empty or "time_s" not in trajectory.columns:
        return 0.0
    angle_col = "rotor_angle_separation_coi_deg" if "rotor_angle_separation_coi_deg" in trajectory.columns else None
    if angle_col is None:
        return 0.0
    grouped = trajectory.groupby("time_s")[angle_col].max().reset_index()
    if len(grouped) < 2:
        return 0.0
    dt = float(grouped["time_s"].iloc[-1] - grouped["time_s"].iloc[0])
    return float((grouped[angle_col].iloc[-1] - grouped[angle_col].iloc[0]) / max(dt, 1e-9))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze no-trip swing-equilibrium sanity diagnostics.")
    parser.add_argument("--summary-json")
    parser.add_argument("--dynamic-result-csv")
    parser.add_argument("--trajectory-summary-csv")
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_equilibrium_diagnostics")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_swing_equilibrium_diagnostics(args.summary_json, args.dynamic_result_csv, args.trajectory_summary_csv, args.output_dir)


if __name__ == "__main__":
    main()
