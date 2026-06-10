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
            {"metric": "max_security_violation_loading_ratio", "value": _numeric_max(results, "max_security_violation_loading_ratio")},
            {"metric": "max_relay_violation_loading_ratio", "value": _numeric_max(results, "max_relay_violation_loading_ratio")},
        ]
    )
    summary.to_csv(out / "relay_vs_security_summary.csv", index=False, encoding="utf-8-sig")
    security_events.to_csv(out / "security_redispatch_cases.csv", index=False, encoding="utf-8-sig")
    relay_events.to_csv(out / "passive_relay_trip_cases.csv", index=False, encoding="utf-8-sig")
    security_events[_numeric_series(security_events, "load_shed_mw") > 0].to_csv(
        out / "load_shed_due_to_security_constraint.csv", index=False, encoding="utf-8-sig"
    )
    relay_events.to_csv(out / "relay_threshold_violation_cases.csv", index=False, encoding="utf-8-sig")
    if "load_shed_mw" in security_events.columns:
        top_security = security_events.sort_values("load_shed_mw", ascending=False).head(10)
    else:
        top_security = security_events.head(10)
    top_security.to_csv(out / "top10_security_load_shedding_cases.csv", index=False, encoding="utf-8-sig")
    if "loading_ratio" in relay_events.columns:
        top_relay = relay_events.sort_values("loading_ratio", ascending=False).head(10)
    else:
        top_relay = relay_events.head(10)
    top_relay.to_csv(out / "top10_relay_trip_cases.csv", index=False, encoding="utf-8-sig")
    sequence_check = _event_order_check(events)
    topology_check = _passive_trip_topology_update_check(events)
    sequence_check.to_csv(out / "relay_security_event_sequence_check.csv", index=False, encoding="utf-8-sig")
    topology_check.to_csv(out / "passive_trip_topology_update_check.csv", index=False, encoding="utf-8-sig")
    return {"output_dir": str(out), "summary_csv": str(out / "relay_vs_security_summary.csv")}


def _filter_event(events: pd.DataFrame, event_type: str) -> pd.DataFrame:
    if events.empty or "event_type" not in events.columns:
        return pd.DataFrame()
    return events[events["event_type"].astype(str) == event_type].copy()


def _numeric_max(table: pd.DataFrame, col: str) -> float:
    if col not in table.columns:
        return 0.0
    values = pd.to_numeric(table[col], errors="coerce").fillna(0.0)
    if values.empty:
        return 0.0
    return float(values.max())


def _numeric_series(table: pd.DataFrame, col: str) -> pd.Series:
    if col not in table.columns:
        return pd.Series([0.0] * len(table), index=table.index)
    return pd.to_numeric(table[col], errors="coerce").fillna(0.0)


def _event_order_check(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if events.empty:
        return pd.DataFrame(columns=["case_id", "first_active_time_s", "first_protection_or_security_time_s", "passed", "reason"])
    work = events.copy()
    work["time_s"] = pd.to_numeric(work["time_s"], errors="coerce")
    for case_id, group in work.groupby("case_id"):
        active = group[group["event_type"].astype(str).str.startswith("active_trip")]
        follow = group[group["event_type"].astype(str).isin(["security_redispatch_or_load_shed", "passive_relay_trip"])]
        first_active = active["time_s"].min() if not active.empty else float("nan")
        first_follow = follow["time_s"].min() if not follow.empty else float("nan")
        passed = follow.empty or (not active.empty and first_follow >= first_active)
        rows.append(
            {
                "case_id": case_id,
                "first_active_time_s": first_active,
                "first_protection_or_security_time_s": first_follow,
                "passed": bool(passed),
                "reason": "ok" if passed else "protection_or_security_before_active_trip",
            }
        )
    return pd.DataFrame(rows)


def _passive_trip_topology_update_check(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    if events.empty:
        return pd.DataFrame(columns=["case_id", "line_label", "time_s", "passed", "reason"])
    work = events.copy()
    work["time_s"] = pd.to_numeric(work["time_s"], errors="coerce")
    relays = work[work["event_type"].astype(str) == "passive_relay_trip"]
    for _, relay in relays.iterrows():
        case_id = relay["case_id"]
        line = str(relay["line_label"])
        group = work[(work["case_id"] == case_id) & (work["time_s"] >= relay["time_s"])]
        if "offlineLines" in group.columns:
            offline_text = ";".join(group["offlineLines"].fillna("").astype(str).tolist())
        else:
            offline_text = ""
        passed = line in offline_text
        rows.append(
            {
                "case_id": case_id,
                "line_label": line,
                "time_s": relay["time_s"],
                "passed": bool(passed),
                "reason": "ok" if passed else "passive_trip_line_missing_from_offlineLines",
            }
        )
    return pd.DataFrame(rows)


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
