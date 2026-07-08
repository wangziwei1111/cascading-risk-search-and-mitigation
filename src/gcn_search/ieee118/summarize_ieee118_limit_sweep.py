from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize IEEE118 flow-scaled thermal limit smoke sweeps.")
    parser.add_argument(
        "--scales",
        type=float,
        nargs="+",
        required=True,
        help="Flow-limit scales to summarize, for example 1.50 1.80 2.00.",
    )
    parser.add_argument(
        "--input-template",
        type=str,
        default="results/gcn_search/ieee118_flow_scaled_{tag}_smoke500",
        help="Input directory template. Uses {scale} and {tag}; tag removes the decimal point.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/gcn_search/ieee118_limit_calibration"),
        help="Directory for the compact sweep summary.",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="ieee118_flow_scaled_wide_scale_sweep",
        help="Output file prefix for CSV and JSON summaries.",
    )
    return parser.parse_args()


def scale_tag(scale: float) -> str:
    return f"{scale:.2f}".replace(".", "")


def load_scale_table(template: str, scale: float) -> tuple[Path, pd.DataFrame]:
    scale_text = f"{scale:.2f}"
    input_dir = Path(template.format(scale=scale_text, tag=scale_tag(scale)))
    summary_path = input_dir / "ieee118_fulltruth_summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing smoke summary for scale {scale_text}: {summary_path}")
    return input_dir, pd.read_csv(summary_path)


def bool_series(table: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in table:
        return pd.Series(default, index=table.index)
    values = table[column]
    if values.dtype == bool:
        return values.fillna(default)
    return values.fillna(str(default)).astype(str).str.lower().isin({"true", "1", "yes"})


def numeric_series(table: pd.DataFrame, column: str) -> pd.Series:
    if column not in table:
        return pd.Series(0.0, index=table.index)
    return pd.to_numeric(table[column], errors="coerce").fillna(0.0)


def summarize_scale(template: str, scale: float) -> dict:
    input_dir, table = load_scale_table(template, scale)
    converged = bool_series(table, "converged")
    critical = bool_series(table, "critical")
    errors = table["error"].fillna("").astype(str).str.len() > 0 if "error" in table else pd.Series(False, index=table.index)
    mechanism = table["critical_mechanism"].fillna("").astype(str) if "critical_mechanism" in table else pd.Series("", index=table.index)
    redispatch_shed = numeric_series(table, "redispatch_load_shed_mw")
    island_shed = numeric_series(table, "island_load_shed_mw")
    has_overload = bool_series(table, "has_overload_cascade")
    relay_trips = numeric_series(table, "num_relay_trips")
    total_shed = numeric_series(table, "total_load_shed_mw")
    max_event_loading = numeric_series(table, "max_event_loading_ratio")
    max_pre_redispatch_loading = numeric_series(table, "max_pre_redispatch_loading_ratio")

    return {
        "scale": f"{scale:.2f}",
        "input_dir": input_dir.as_posix(),
        "total_rows": int(len(table)),
        "converged_rows": int(converged.sum()),
        "error_rows": int(errors.sum()),
        "critical_rows": int(critical.sum()),
        "critical_ratio": float(critical.sum() / len(table)) if len(table) else 0.0,
        "relay_cascade_rows": int((mechanism == "relay_cascade").sum()),
        "relay_cascade_ratio": float((mechanism == "relay_cascade").sum() / len(table)) if len(table) else 0.0,
        "island_only_rows": int((mechanism == "island_only").sum()),
        "redispatch_shed_rows": int((redispatch_shed > 1e-7).sum()),
        "mixed_rows": int((has_overload & ((redispatch_shed > 1e-7) | (island_shed > 1e-7))).sum()),
        "max_event_loading_ratio": float(max_event_loading.max()) if len(table) else 0.0,
        "max_pre_redispatch_loading_ratio": float(max_pre_redispatch_loading.max()) if len(table) else 0.0,
        "total_relay_trips": int(relay_trips.sum()),
        "max_relay_trips_per_path": int(relay_trips.max()) if len(table) else 0,
        "mean_total_load_shed_mw": float(total_shed.mean()) if len(table) else 0.0,
        "p95_total_load_shed_mw": float(total_shed.quantile(0.95)) if len(table) else 0.0,
        "max_total_load_shed_mw": float(total_shed.max()) if len(table) else 0.0,
    }


def summarize(scales: list[float], input_template: str, output_dir: Path, output_prefix: str) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = [summarize_scale(input_template, scale) for scale in scales]
    table = pd.DataFrame(records)
    table.to_csv(output_dir / f"{output_prefix}.csv", index=False, encoding="utf-8-sig")
    (output_dir / f"{output_prefix}.json").write_text(
        json.dumps(records, indent=2),
        encoding="utf-8",
    )
    return table


def main() -> None:
    args = parse_args()
    table = summarize(args.scales, args.input_template, args.output_dir, args.output_prefix)
    print(f"IEEE118 limit sweep summary written to {args.output_dir}")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()
