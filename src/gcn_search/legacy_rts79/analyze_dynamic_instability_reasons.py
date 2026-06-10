from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import pandas as pd


REASON_KEYS = {
    "frequency": "frequency_nadir_below_threshold",
    "rotor": "rotor_angle_above_threshold",
    "relay": "relay_violation_not_eliminated",
    "sim": "sim_failed",
}


def analyze_dynamic_instability_reasons(
    dynamic_results_csv: str | Path,
    event_log_glob: str,
    topk_paths_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_real_pipeline_summary",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dynamic = pd.read_csv(dynamic_results_csv)
    topk = pd.read_csv(topk_paths_csv)
    merged = topk.merge(dynamic, on="case_id", how="right")
    events = _load_events(event_log_glob)
    reason_counts = _reason_counts(merged)
    security_cases = set(events.loc[events.get("event_type", pd.Series(dtype=str)).astype(str) == "security_redispatch_or_load_shed", "case_id"]) if not events.empty else set()
    relay_cases = set(events.loc[events.get("event_type", pd.Series(dtype=str)).astype(str) == "passive_relay_trip", "case_id"]) if not events.empty else set()
    freq_or_angle = merged["unstable_reason"].fillna("").astype(str).str.contains("frequency|rotor", case=False, regex=True)
    security_no_freq_angle = merged["case_id"].isin(security_cases) & ~freq_or_angle
    freq_angle_no_relay_security = freq_or_angle & ~merged["case_id"].isin(security_cases | relay_cases)
    summary = {
        "num_cases": int(len(merged)),
        "dynamic_unstable_count": int(_to_bool_series(merged["dynamic_unstable"]).sum()),
        **reason_counts,
        "frequency_nadir_hz_min": _num_stat(merged, "frequency_nadir_hz", "min"),
        "frequency_nadir_hz_mean": _num_stat(merged, "frequency_nadir_hz", "mean"),
        "frequency_nadir_hz_max": _num_stat(merged, "frequency_nadir_hz", "max"),
        "frequency_zenith_hz_min": _num_stat(merged, "frequency_zenith_hz", "min"),
        "frequency_zenith_hz_mean": _num_stat(merged, "frequency_zenith_hz", "mean"),
        "frequency_zenith_hz_max": _num_stat(merged, "frequency_zenith_hz", "max"),
        "max_rotor_angle_separation_deg_min": _num_stat(merged, "max_rotor_angle_separation_deg", "min"),
        "max_rotor_angle_separation_deg_mean": _num_stat(merged, "max_rotor_angle_separation_deg", "mean"),
        "max_rotor_angle_separation_deg_max": _num_stat(merged, "max_rotor_angle_separation_deg", "max"),
        "max_line_loading_ratio_min": _num_stat(merged, "max_line_loading_ratio", "min"),
        "max_line_loading_ratio_mean": _num_stat(merged, "max_line_loading_ratio", "mean"),
        "max_line_loading_ratio_max": _num_stat(merged, "max_line_loading_ratio", "max"),
        "total_dynamic_load_shed_mw": float(pd.to_numeric(merged.get("dynamic_load_shed_mw", 0.0), errors="coerce").fillna(0.0).sum()),
        "passive_relay_trip_count": int(pd.to_numeric(merged.get("passive_relay_trip_count", 0), errors="coerce").fillna(0).sum()),
        "security_redispatch_count": int(pd.to_numeric(merged.get("security_redispatch_count", 0), errors="coerce").fillna(0).sum()),
        "cases_with_security_action_but_no_frequency_or_angle_instability": int(security_no_freq_angle.sum()),
        "cases_with_frequency_or_angle_instability_but_no_relay_or_security_action": int(freq_angle_no_relay_security.sum()),
    }
    summary_csv = out / "dynamic_instability_reason_summary.csv"
    summary_json = out / "dynamic_instability_reason_summary.json"
    top_cases_csv = out / "top_dynamic_stress_cases.csv"
    pd.DataFrame([summary]).to_csv(summary_csv, index=False, encoding="utf-8-sig")
    summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    stress_cols = [col for col in ["case_id", "path", "frequency_nadir_hz", "max_rotor_angle_separation_deg", "max_line_loading_ratio", "dynamic_load_shed_mw", "passive_relay_trip_count", "unstable_reason"] if col in merged.columns]
    merged.assign(_stress=_rough_stress(merged)).sort_values("_stress", ascending=False)[stress_cols].head(20).to_csv(top_cases_csv, index=False, encoding="utf-8-sig")
    return {"summary_csv": str(summary_csv), "summary_json": str(summary_json), "top_cases_csv": str(top_cases_csv), **summary}


def _load_events(pattern: str) -> pd.DataFrame:
    tables = []
    for path in glob.glob(pattern):
        try:
            tables.append(pd.read_csv(path))
        except Exception:
            continue
    return pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()


def _reason_counts(table: pd.DataFrame) -> dict[str, int]:
    reasons = table.get("unstable_reason", pd.Series(dtype=str)).fillna("").astype(str)
    counts = {value: 0 for value in REASON_KEYS.values()}
    counts["security_load_shed_only"] = 0
    counts["mixed_reasons"] = 0
    for reason in reasons:
        hit = []
        lower = reason.lower()
        if "frequency" in lower:
            counts["frequency_nadir_below_threshold"] += 1
            hit.append("frequency")
        if "rotor" in lower:
            counts["rotor_angle_above_threshold"] += 1
            hit.append("rotor")
        if "relay_violation" in lower:
            counts["relay_violation_not_eliminated"] += 1
            hit.append("relay")
        if "sim_failed" in lower or "failed" in lower:
            counts["sim_failed"] += 1
            hit.append("sim")
        if len(hit) > 1:
            counts["mixed_reasons"] += 1
    return counts


def _num_stat(table: pd.DataFrame, col: str, fn: str) -> float:
    values = pd.to_numeric(table.get(col, pd.Series(dtype=float)), errors="coerce")
    if values.dropna().empty:
        return 0.0
    return float(getattr(values, fn)())


def _rough_stress(table: pd.DataFrame) -> pd.Series:
    freq = pd.to_numeric(table.get("frequency_nadir_hz", 50.0), errors="coerce").fillna(50.0)
    angle = pd.to_numeric(table.get("max_rotor_angle_separation_deg", 0.0), errors="coerce").fillna(0.0)
    loading = pd.to_numeric(table.get("max_line_loading_ratio", 0.0), errors="coerce").fillna(0.0)
    shed = pd.to_numeric(table.get("dynamic_load_shed_mw", 0.0), errors="coerce").fillna(0.0)
    relay = pd.to_numeric(table.get("passive_relay_trip_count", 0.0), errors="coerce").fillna(0.0)
    return (49.5 - freq).clip(lower=0) + (angle / 180.0 - 1).clip(lower=0) + (loading - 1).clip(lower=0) + shed / max(float(shed.max()), 1.0) + relay


def _to_bool_series(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize dynamic instability reasons and stress cases.")
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--event-log-glob", required=True)
    parser.add_argument("--topk-paths-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_real_pipeline_summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_dynamic_instability_reasons(args.dynamic_results_csv, args.event_log_glob, args.topk_paths_csv, args.output_dir)


if __name__ == "__main__":
    main()
