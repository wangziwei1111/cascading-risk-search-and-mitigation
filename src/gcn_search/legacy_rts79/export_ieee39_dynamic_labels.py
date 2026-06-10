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


def export_ieee39_dynamic_labels(
    fault_test_summary_csv: str | Path,
    event_log_csv: str | Path | None = None,
    path_table_csv: str | Path | None = None,
    output_dir: str | Path = "results/gcn_search/ieee39_dynamic_labels",
) -> dict[str, str]:
    summary = pd.read_csv(fault_test_summary_csv)
    events = pd.read_csv(event_log_csv) if event_log_csv and Path(event_log_csv).exists() else pd.DataFrame()
    path_table = pd.read_csv(path_table_csv) if path_table_csv and Path(path_table_csv).exists() else pd.DataFrame()

    labels = _build_label_preview(summary, events, path_table)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    preview_csv = out / "ieee39_dynamic_label_preview.csv"
    schema_json = out / "ieee39_dynamic_label_schema.json"
    labels.to_csv(preview_csv, index=False, encoding="utf-8-sig")
    schema_json.write_text(json.dumps(_schema_payload(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"preview_csv": str(preview_csv), "schema_json": str(schema_json), "num_rows": str(len(labels))}


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
                "min_frequency_hz": float(item.get("min_frequency_hz", 50.0)),
                "min_voltage_pu": float(item.get("min_voltage_pu", 1.0)),
                "max_rotor_angle_separation_deg": float(item.get("max_rotor_angle_separation_deg", 0.0)),
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
    min_frequency = float(row.get("min_frequency_hz", 50.0))
    min_voltage = float(row.get("min_voltage_pu", 1.0))
    angle = float(row.get("max_rotor_angle_separation_deg", 0.0))
    speed = abs(float(row.get("max_speed_deviation", 0.0)))
    return (
        max(0.0, 49.5 - min_frequency)
        + max(0.0, 0.9 - min_voltage)
        + max(0.0, angle / 180.0 - 1.0)
        + speed
        + relay_count
        + breaker_count
    )


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
    parser.add_argument("--fault-test-summary-csv", required=True)
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
