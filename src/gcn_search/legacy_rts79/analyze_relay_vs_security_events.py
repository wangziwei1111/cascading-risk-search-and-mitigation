from __future__ import annotations

import argparse
import glob
from pathlib import Path

import pandas as pd


def classify_loading_action(loading_ratio: float, beta: float = 1.2, security_limit: float = 1.0) -> str:
    if loading_ratio > beta:
        return "passive_relay_trip"
    if loading_ratio > security_limit:
        return "security_redispatch_or_load_shed"
    return "no_action"


def analyze_relay_vs_security_events(
    dynamic_results_csv: str | Path,
    event_log_glob: str,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_relay_security_analysis",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    results = pd.read_csv(dynamic_results_csv)
    logs = []
    for path_text in sorted(glob.glob(str(event_log_glob))):
        path = Path(path_text)
        try:
            table = pd.read_csv(path)
        except Exception:
            continue
        if not table.empty:
            table["event_log_path"] = str(path)
            logs.append(table)
    events = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame()
    security_events = _filter_event(events, "security_redispatch_or_load_shed")
    relay_events = _filter_event(events, "passive_relay_trip")
    security_cases = set(security_events.get("case_id", []))
    relay_cases = set(relay_events.get("case_id", []))
    summary = pd.DataFrame(
        [
            {"metric": "num_cases", "value": int(len(results))},
            {"metric": "cases_with_security_limit_violation_not_relay", "value": int(len(security_cases))},
            {"metric": "cases_with_security_redispatch_or_load_shed", "value": int(len(security_cases))},
            {"metric": "cases_with_passive_relay_trip", "value": int(len(relay_cases))},
            {"metric": "cases_with_both_security_and_relay", "value": int(len(security_cases & relay_cases))},
            {"metric": "total_dynamic_load_shed_mw", "value": float(pd.to_numeric(results.get("dynamic_load_shed_mw", 0.0), errors="coerce").fillna(0.0).sum())},
            {"metric": "max_security_violation_loading_ratio", "value": float(pd.to_numeric(results.get("max_security_violation_loading_ratio", 0.0), errors="coerce").fillna(0.0).max())},
            {"metric": "max_relay_violation_loading_ratio", "value": float(pd.to_numeric(results.get("max_relay_violation_loading_ratio", 0.0), errors="coerce").fillna(0.0).max())},
        ]
    )
    summary.to_csv(out / "relay_vs_security_summary.csv", index=False, encoding="utf-8-sig")
    security_events.to_csv(out / "security_redispatch_cases.csv", index=False, encoding="utf-8-sig")
    relay_events.to_csv(out / "passive_relay_trip_cases.csv", index=False, encoding="utf-8-sig")
    security_events[pd.to_numeric(security_events.get("load_shed_mw", 0.0), errors="coerce").fillna(0.0) > 0].to_csv(
        out / "load_shed_due_to_security_constraint.csv", index=False, encoding="utf-8-sig"
    )
    relay_events.to_csv(out / "relay_threshold_violation_cases.csv", index=False, encoding="utf-8-sig")
    security_events.sort_values("load_shed_mw", ascending=False).head(10).to_csv(out / "top10_security_load_shedding_cases.csv", index=False, encoding="utf-8-sig")
    relay_events.sort_values("loading_ratio", ascending=False).head(10).to_csv(out / "top10_relay_trip_cases.csv", index=False, encoding="utf-8-sig")
    return {"output_dir": str(out), "summary_csv": str(out / "relay_vs_security_summary.csv")}


def _filter_event(events: pd.DataFrame, event_type: str) -> pd.DataFrame:
    if events.empty or "event_type" not in events.columns:
        return pd.DataFrame()
    return events[events["event_type"].astype(str) == event_type].copy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze relay-threshold and security-constraint event logs.")
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--event-log-glob", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_relay_security_analysis")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_relay_vs_security_events(args.dynamic_results_csv, args.event_log_glob, args.output_dir)


if __name__ == "__main__":
    main()
