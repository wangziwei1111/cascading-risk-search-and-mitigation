from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def merge_summaries(
    base_summary_csv: str | Path,
    multi_handwired_summary_csv: str | Path,
    output_csv: str | Path,
    output_summary_json: str | Path,
) -> dict:
    base = pd.read_csv(base_summary_csv)
    multi = pd.read_csv(multi_handwired_summary_csv) if Path(multi_handwired_summary_csv).exists() else pd.DataFrame(columns=base.columns)
    original_multi = multi.copy()
    multi = _drop_lines_already_handwired_in_base(base, multi)
    existing_skipped_line_ids = _line_ids(original_multi[~original_multi.index.isin(multi.index)] if not original_multi.empty else original_multi)
    multi_ready = _is_training_ready_handwired(multi)
    timeout_mask = _is_timeout_row(multi)
    failed_line_ids = _line_ids(multi[~multi_ready & ~timeout_mask])
    timeout_line_ids = _line_ids(multi[~multi_ready & timeout_mask])
    multi = multi[multi_ready].copy()
    for column in base.columns:
        if column not in multi.columns:
            multi[column] = pd.NA
    for column in multi.columns:
        if column not in base.columns:
            base[column] = pd.NA
    multi = multi[base.columns]

    combined = pd.concat([base, multi], ignore_index=True)
    combined["_priority"] = combined.apply(_priority, axis=1)
    combined = combined.sort_values("_priority", ascending=False)
    combined = combined.drop_duplicates(subset=["test_case"], keep="first").drop(columns=["_priority"])

    out_csv = Path(output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_csv, index=False, encoding="utf-8-sig")
    combined_ready = combined.get("training_ready_candidate", pd.Series("", index=combined.index)).astype(str).str.lower().isin({"1", "true", "yes"})
    combined_impl = combined.get("trip_implementation", pd.Series("", index=combined.index)).astype(str)
    handwired_impl = combined_impl.isin({"handwired_timed_breaker", "handwired_timed_controlled_switch"})

    summary = {
        "base_rows": int(len(base)),
        "multi_handwired_rows": int(len(multi)),
        "input_multi_handwired_rows": int(len(original_multi)),
        "merged_rows": int(len(combined)),
        "merged_line_ids": _line_ids(multi),
        "failed_line_ids": failed_line_ids,
        "timeout_line_ids": timeout_line_ids,
        "skipped_line_ids": existing_skipped_line_ids,
        "num_handwired_rows_added": int(combined["test_case"].astype(str).str.contains("handwired_line_trip_", na=False).sum()),
        "num_training_ready_handwired_rows": int(
            (handwired_impl & combined_ready).sum()
        ),
        "num_training_ready_handwired_rows_by_line": {
            line: int(((combined.get("tripped_line", pd.Series("", index=combined.index)).astype(str) == line) & handwired_impl & combined_ready).sum())
            for line in sorted(combined.loc[handwired_impl & combined_ready, "tripped_line"].astype(str).dropna().unique().tolist())
            if line and line.lower() != "nan"
        },
        "static_topology_disable_overwrote_handwired": False,
    }
    Path(output_summary_json).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _priority(row: pd.Series) -> int:
    impl = str(row.get("trip_implementation", ""))
    ready = str(row.get("training_ready_candidate", "")).lower() in {"1", "true", "yes"}
    if impl in {"handwired_timed_breaker", "handwired_timed_controlled_switch"} and ready:
        return 3
    if ready:
        return 2
    if impl == "static_topology_disable":
        return 0
    return 1


def _drop_lines_already_handwired_in_base(base: pd.DataFrame, multi: pd.DataFrame) -> pd.DataFrame:
    if multi.empty or "tripped_line" not in base.columns or "tripped_line" not in multi.columns:
        return multi
    base_impl = base.get("trip_implementation", pd.Series("", index=base.index)).astype(str)
    base_ready = base.get("training_ready_candidate", pd.Series("", index=base.index)).astype(str).str.lower().isin({"1", "true", "yes"})
    existing_lines = set(
        base.loc[
            base_impl.isin({"handwired_timed_breaker", "handwired_timed_controlled_switch"}) & base_ready,
            "tripped_line",
        ].astype(str)
    )
    if not existing_lines:
        return multi
    return multi[~multi["tripped_line"].astype(str).isin(existing_lines)].copy()


def _is_training_ready_handwired(table: pd.DataFrame) -> pd.Series:
    if table.empty:
        return pd.Series([], dtype=bool)
    ready = table.get("training_ready_candidate", pd.Series("", index=table.index)).astype(str).str.lower().isin({"1", "true", "yes"})
    impl = table.get("trip_implementation", pd.Series("", index=table.index)).astype(str)
    status = table.get("measurement_extraction_status", pd.Series("", index=table.index)).astype(str)
    return ready & impl.isin({"handwired_timed_breaker", "handwired_timed_controlled_switch"}) & status.eq("voltage_speed_angle")


def _is_timeout_row(table: pd.DataFrame) -> pd.Series:
    if table.empty:
        return pd.Series([], dtype=bool)
    status = table.get("measurement_extraction_status", pd.Series("", index=table.index)).astype(str).str.lower()
    note = table.get("note", pd.Series("", index=table.index)).astype(str).str.lower()
    message = table.get("timeout_or_error_message", pd.Series("", index=table.index)).astype(str).str.lower()
    return status.str.contains("timeout", na=False) | note.str.contains("timeout", na=False) | message.str.contains("timeout", na=False)


def _line_ids(table: pd.DataFrame) -> list[str]:
    if table.empty or "tripped_line" not in table.columns:
        return []
    values = table["tripped_line"].astype(str)
    return sorted(line for line in values.dropna().unique().tolist() if line and line.lower() != "nan")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge IEEE39 base and multi-handwired compact fault summaries.")
    parser.add_argument("--base-summary-csv", required=True)
    parser.add_argument("--multi-handwired-summary-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-summary-json", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = merge_summaries(
        args.base_summary_csv,
        args.multi_handwired_summary_csv,
        args.output_csv,
        args.output_summary_json,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
