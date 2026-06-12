from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


LABEL_COLUMNS = [
    "path",
    "first_line",
    "second_line",
    "dynamic_unstable",
    "dynamic_stress_score",
    "min_frequency_hz",
    "min_voltage_pu",
    "max_rotor_angle_separation_deg",
    "relay_trip_count",
    "breaker_trip_count",
]

TIMED_LINE_TRIP_IMPLEMENTATIONS = {
    "timed_controlled_switch",
    "existing_breaker_control",
    "handwired_timed_breaker",
    "handwired_timed_controlled_switch",
}


def export_ieee39_dynamic_labels(
    fault_test_summary_csv: str | Path,
    event_log_csv: str | Path | None = None,
    path_table_csv: str | Path | None = None,
    output_dir: str | Path = "results/gcn_search/ieee39_dynamic_labels",
) -> dict[str, str]:
    summary = pd.read_csv(fault_test_summary_csv)
    events = pd.read_csv(event_log_csv) if event_log_csv and Path(event_log_csv).exists() else pd.DataFrame()
    path_table = pd.read_csv(path_table_csv) if path_table_csv and Path(path_table_csv).exists() else pd.DataFrame()

    training_ready = _training_ready_rows(summary)
    labels = _build_label_preview(training_ready, events, path_table)
    quality = _quality_summary(summary, training_ready)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    preview_csv = out / "ieee39_dynamic_label_preview.csv"
    schema_json = out / "ieee39_dynamic_label_schema.json"
    quality_json = out / "ieee39_dynamic_label_quality_summary.json"
    labels.to_csv(preview_csv, index=False, encoding="utf-8-sig")
    schema_json.write_text(json.dumps(_schema_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    quality_json.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"preview_csv": str(preview_csv), "schema_json": str(schema_json), "quality_json": str(quality_json), "num_rows": str(len(labels))}


def _training_ready_rows(summary: pd.DataFrame) -> pd.DataFrame:
    if "training_ready_candidate" in summary.columns:
        ready = summary["training_ready_candidate"].astype(str).str.lower().isin({"1", "true", "yes"})
        schema = summary.get("schema_only", pd.Series(False, index=summary.index)).astype(str).str.lower().isin({"1", "true", "yes"})
        no_fault = summary.get("test_case", pd.Series("", index=summary.index)).astype(str).str.lower().eq("no_fault_sanity")
        trip_impl = summary.get("trip_implementation", pd.Series("", index=summary.index)).astype(str)
        fault_type = summary.get("fault_type", pd.Series("", index=summary.index)).astype(str)
        test_case = summary.get("test_case", pd.Series("", index=summary.index)).astype(str)
        is_line_trip = test_case.str.contains("single_line_trip|handwired_line_trip_", case=False, na=False) | fault_type.str.contains("pilot_line_trip|single_line_trip", case=False, na=False)
        line_trip_allowed = ~is_line_trip | trip_impl.isin(TIMED_LINE_TRIP_IMPLEMENTATIONS)
        if "measurement_extraction_status" in summary.columns:
            measurement_status = summary["measurement_extraction_status"].astype(str)
            measurement_ok = ~is_line_trip | measurement_status.str.contains("voltage_speed_angle", case=False, na=False)
        else:
            measurement_ok = pd.Series(True, index=summary.index)
        static_disabled = trip_impl.eq("static_topology_disable")
        return summary[ready & ~schema & ~no_fault & line_trip_allowed & measurement_ok & ~static_disabled].copy()
    if "simulation_success" not in summary.columns or "physical_fault_or_breaker_action_executed" not in summary.columns:
        return summary.iloc[0:0].copy()
    success = summary["simulation_success"].astype(str).str.lower().isin({"1", "true", "yes"})
    physical = summary["physical_fault_or_breaker_action_executed"].astype(str).str.lower().isin({"1", "true", "yes"})
    return summary[success & physical].copy()


def _quality_summary(summary: pd.DataFrame, training_ready: pd.DataFrame) -> dict:
    has_physical = "physical_fault_or_breaker_action_executed" in summary.columns
    physical_count = int(summary["physical_fault_or_breaker_action_executed"].astype(str).str.lower().isin({"1", "true", "yes"}).sum()) if has_physical else 0
    ready_count = int(len(training_ready))
    if "schema_only" in summary.columns:
        schema_only = int(summary["schema_only"].astype(str).str.lower().isin({"1", "true", "yes"}).sum())
    else:
        schema_only = int(len(summary) - ready_count)
    if ready_count == 0 and physical_count == 0:
        status = "schema_only"
    elif ready_count < 10:
        status = "partial_physical_execution"
    elif ready_count < 50:
        status = "training_ready_minimal"
    else:
        status = "training_ready_batch"
    voltage_count = _measurement_count(summary, "min_voltage_pu")
    frequency_count = _measurement_count(summary, "min_frequency_hz")
    speed_count = _measurement_count(summary, "max_speed_deviation")
    angle_count = _measurement_count(summary, "max_rotor_angle_separation_deg")
    measurement_quality_status = _measurement_quality_status(
        voltage_count=voltage_count,
        frequency_count=frequency_count,
        speed_count=speed_count,
        angle_count=angle_count,
        ready_count=ready_count,
    )
    trip_impl = summary.get("trip_implementation", pd.Series("", index=summary.index)).astype(str)
    test_case = summary.get("test_case", pd.Series("", index=summary.index)).astype(str)
    fault_type = summary.get("fault_type", pd.Series("", index=summary.index)).astype(str)
    ready_cases = training_ready.get("test_case", pd.Series("", index=training_ready.index)).astype(str)
    ready_trip_impl = training_ready.get("trip_implementation", pd.Series("", index=training_ready.index)).astype(str)
    ready_lines = training_ready.get("tripped_line", pd.Series("", index=training_ready.index)).astype(str)
    handwired_ready = training_ready[ready_trip_impl.isin({"handwired_timed_breaker", "handwired_timed_controlled_switch"})]
    handwired_ready_lines = handwired_ready.get("tripped_line", pd.Series("", index=handwired_ready.index)).astype(str)
    handwired_lines = sorted(line for line in handwired_ready_lines.unique().tolist() if line and line.lower() != "nan")
    handwired_validation = _handwired_validation_summary()
    multi_handwired_validation = _multi_handwired_validation_summary()
    return {
        "num_fault_rows": int(len(summary)),
        "num_physical_executed_rows": physical_count,
        "num_training_ready_labels": ready_count,
        "num_schema_only_rows": schema_only,
        "num_labels_with_voltage_measurement": voltage_count,
        "num_labels_with_frequency_measurement": frequency_count,
        "num_labels_with_speed_measurement": speed_count,
        "num_labels_with_rotor_angle_measurement": angle_count,
        "num_training_ready_three_phase_fault_labels": int(ready_cases.str.contains("three_phase_fault", case=False, na=False).sum()),
        "num_training_ready_relay_proxy_labels": int(ready_cases.str.contains("relay", case=False, na=False).sum()),
        "num_training_ready_timed_line_trip_labels": int(ready_trip_impl.isin(TIMED_LINE_TRIP_IMPLEMENTATIONS).sum()),
        "num_training_ready_handwired_line_trip_labels": int(ready_trip_impl.isin({"handwired_timed_breaker", "handwired_timed_controlled_switch"}).sum()),
        "num_training_ready_handwired_line_trip_labels_by_line": {
            line: int((handwired_ready_lines == line).sum()) for line in handwired_lines
        },
        "num_unique_handwired_line_ids": int(len(handwired_lines)),
        "num_unique_training_ready_fault_types": int(training_ready.get("fault_type", pd.Series("", index=training_ready.index)).astype(str).nunique()),
        "num_handwired_validation_passed": int(multi_handwired_validation.get("num_validation_passed", int(bool(handwired_validation.get("validation_passed", False))))),
        "handwired_model_used": bool(multi_handwired_validation.get("handwired_model_used", bool(handwired_validation.get("handwired_model_found", False)))),
        "handwired_model_committed": False,
        "num_static_topology_disable_rows": int(trip_impl.eq("static_topology_disable").sum()),
        "num_manual_required_trip_rows": int(
            (
                test_case.str.contains("line_trip", case=False, na=False)
                | fault_type.str.contains("line_trip", case=False, na=False)
            ).sum()
            - trip_impl.isin(TIMED_LINE_TRIP_IMPLEMENTATIONS).sum()
        ),
        "measurement_quality_status": measurement_quality_status,
        "label_quality_status": status,
        "allowed_for_dynamic_aware_training": bool(ready_count >= 10),
    }


def _handwired_validation_summary() -> dict:
    path = Path("results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_handwired_breaker_validation_summary.json")
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _multi_handwired_validation_summary() -> dict:
    path = Path("results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv")
    if not path.exists():
        return {}
    try:
        table = pd.read_csv(path)
    except Exception:
        return {}
    passed = table.get("validation_passed", pd.Series(False, index=table.index)).astype(str).str.lower().isin({"1", "true", "yes"})
    found = table.get("handwired_model_found", pd.Series(False, index=table.index)).astype(str).str.lower().isin({"1", "true", "yes"})
    return {
        "num_validation_passed": int(passed.sum()),
        "handwired_model_used": bool(found.any()),
    }


def _measurement_count(summary: pd.DataFrame, column: str) -> int:
    if column not in summary.columns:
        return 0
    return int(pd.to_numeric(summary[column], errors="coerce").notna().sum())


def _measurement_quality_status(
    *,
    voltage_count: int,
    frequency_count: int,
    speed_count: int,
    angle_count: int,
    ready_count: int,
) -> str:
    dynamic_count = max(frequency_count, speed_count, angle_count)
    if voltage_count == 0 and dynamic_count == 0:
        return "no_measurements"
    if voltage_count > 0 and dynamic_count == 0:
        return "voltage_only"
    if ready_count >= 50 and voltage_count >= 50 and dynamic_count >= 50:
        return "sufficient_for_training_batch"
    if ready_count >= 10 and voltage_count >= 10 and dynamic_count >= 10:
        return "sufficient_for_training_preview"
    return "partial_dynamic_measurements"


def _build_label_preview(summary: pd.DataFrame, events: pd.DataFrame, path_table: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for _, item in summary.iterrows():
        test_case = str(item.get("test_case", "unknown_case"))
        tripped_line = str(item.get("tripped_line", "") or "")
        path = _path_for_case(test_case, tripped_line, path_table)
        relay_count = _event_count(events, test_case, "relay")
        breaker_count = _event_count(events, test_case, "breaker")
        first_line, second_line = _split_path(path)
        stress = _dynamic_stress_score(item, relay_count, breaker_count)
        rows.append(
            {
                "path": path,
                "first_line": first_line,
                "second_line": second_line,
                "dynamic_unstable": bool(item.get("unstable_flag", False)),
                "dynamic_stress_score": stress,
                "min_frequency_hz": _finite_or_nan(item.get("min_frequency_hz")),
                "min_voltage_pu": _finite_or_nan(item.get("min_voltage_pu")),
                "max_rotor_angle_separation_deg": _finite_or_nan(item.get("max_rotor_angle_separation_deg")),
                "relay_trip_count": int(relay_count),
                "breaker_trip_count": int(breaker_count),
            }
        )
    return pd.DataFrame(rows, columns=LABEL_COLUMNS)


def _path_for_case(test_case: str, tripped_line: str, path_table: pd.DataFrame) -> str:
    if not path_table.empty and "test_case" in path_table.columns and "path" in path_table.columns:
        match = path_table[path_table["test_case"].astype(str) == test_case]
        if not match.empty:
            return str(match.iloc[0]["path"])
    if tripped_line and tripped_line.lower() != "nan":
        return tripped_line
    return test_case


def _split_path(path: str) -> tuple[str, str]:
    for sep in ("->", ",", ";", "|"):
        if sep in path:
            parts = [part.strip() for part in path.split(sep) if part.strip()]
            return (parts[0] if parts else "", parts[1] if len(parts) > 1 else "")
    return path, ""


def _event_count(events: pd.DataFrame, test_case: str, token: str) -> int:
    if events.empty or "test_case" not in events.columns:
        return 0
    subset = events[events["test_case"].astype(str) == test_case]
    text = subset.astype(str).agg(" ".join, axis=1).str.lower() if not subset.empty else pd.Series(dtype=str)
    return int(text.str.contains(token).sum())


def _dynamic_stress_score(row: pd.Series, relay_count: int, breaker_count: int) -> float:
    min_frequency = _finite_or_default(row.get("min_frequency_hz"), 50.0)
    min_voltage = _finite_or_default(row.get("min_voltage_pu"), 1.0)
    angle = _finite_or_default(row.get("max_rotor_angle_separation_deg"), 0.0)
    speed = abs(_finite_or_default(row.get("max_speed_deviation"), 0.0))
    return (
        max(0.0, 49.5 - min_frequency)
        + max(0.0, 0.9 - min_voltage)
        + max(0.0, angle / 180.0 - 1.0)
        + speed
        + relay_count
        + breaker_count
    )


def _finite_or_default(value, default: float) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return default if pd.isna(parsed) else float(parsed)


def _finite_or_nan(value) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float("nan") if pd.isna(parsed) else float(parsed)


def _schema_payload() -> dict:
    return {
        "label_scope": "IEEE39 graphical dynamic model preliminary labels",
        "not_training_output": True,
        "columns": {
            "path": "ordered line outage path, e.g. L10->L05",
            "first_line": "first active line trip",
            "second_line": "second active line trip, empty for N-1",
            "dynamic_unstable": "boolean dynamic instability flag from IEEE39 graphical simulation summary",
            "dynamic_stress_score": "continuous diagnostic score derived from frequency, voltage, rotor angle, relay and breaker counts",
            "min_frequency_hz": "minimum observed frequency in Hz",
            "min_voltage_pu": "minimum observed bus voltage in per unit",
            "max_rotor_angle_separation_deg": "maximum rotor-angle separation in degrees",
            "relay_trip_count": "number of relay events in event log",
            "breaker_trip_count": "number of breaker events in event log",
        },
        "limitations": [
            "Schema only; this round does not train a dynamic-aware reranker.",
            "Labels are only as credible as the selected IEEE39 graphical model and protection wrapper.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export IEEE39 dynamic label preview and schema.")
    parser.add_argument("--fault-test-summary-csv", "--fault-summary-csv", dest="fault_test_summary_csv", required=True)
    parser.add_argument("--event-log-csv", default=None)
    parser.add_argument("--path-table-csv", default=None)
    parser.add_argument("--output-dir", default="results/gcn_search/ieee39_dynamic_labels")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = export_ieee39_dynamic_labels(
        args.fault_test_summary_csv,
        args.event_log_csv,
        args.path_table_csv,
        args.output_dir,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
