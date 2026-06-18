from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> Any:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_rows_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "pair_id",
        "execution_status",
        "pilot_label_value",
        "pilot_label_status",
        "dynamic_stress_score_if_available",
        "unstable_flag_if_available",
        "timeout_or_failure_reason",
        "evidence_source",
        "raw_trajectory_committed",
        "full_timeseries_committed",
        "mat_file_committed",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _coerce_row(row: dict[str, Any]) -> dict[str, Any]:
    status = str(row.get("execution_status", "unknown")).lower()
    label_status = str(row.get("pilot_label_status", status)).lower()
    label_value = row.get("pilot_label_value")
    if status in {"unknown", "timeout", "blocked", "failed"} or label_status in {"unknown", "timeout", "blocked", "failed"}:
        label_value = None
    if label_value not in {0, 1, None}:
        label_value = None
    return {
        "pair_id": row.get("pair_id"),
        "execution_status": status,
        "pilot_label_value": label_value,
        "pilot_label_status": label_status,
        "dynamic_stress_score_if_available": row.get("dynamic_stress_score_if_available"),
        "unstable_flag_if_available": row.get("unstable_flag_if_available"),
        "timeout_or_failure_reason": row.get("timeout_or_failure_reason"),
        "evidence_source": row.get("evidence_source", "compact_evidence_summary"),
        "raw_trajectory_committed": False,
        "full_timeseries_committed": False,
        "mat_file_committed": False,
    }


def parse_compact_evidence(input_json: Path) -> list[dict[str, Any]]:
    payload = _read_json(input_json)
    if isinstance(payload, list):
        raw_rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        raw_rows = payload["rows"]
    elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
        raw_rows = payload["results"]
    else:
        raw_rows = []
    return [_coerce_row(dict(row)) for row in raw_rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse IEEE39 selected-pair compact evidence only.")
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    input_json = Path(args.input_json)
    output_dir = Path(args.output_dir)
    if args.strict and not input_json.exists():
        raise SystemExit(f"Missing compact evidence JSON: {input_json}")
    rows = parse_compact_evidence(input_json)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(output_dir / "parsed_selected_pair_compact_evidence.json", rows)
    _write_rows_csv(output_dir / "parsed_selected_pair_compact_evidence.csv", rows)
    print(json.dumps({"num_rows": len(rows), "formal_labels_exported": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
