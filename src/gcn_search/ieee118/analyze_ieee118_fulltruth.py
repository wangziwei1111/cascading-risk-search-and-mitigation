from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit IEEE 118 ordered N-2 full-truth outputs.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing ieee118_fulltruth_summary.csv.")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for audit outputs. Defaults to input-dir.")
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100], help="Top-K load-shed cutoffs.")
    parser.add_argument("--pattern-limit", type=int, default=20, help="Number of high-risk ordered patterns in JSON.")
    return parser.parse_args()


def describe_series(series: pd.Series) -> dict:
    desc = pd.to_numeric(series, errors="coerce").describe()
    return {str(key): float(value) for key, value in desc.items()}


def load_summary(input_dir: Path) -> pd.DataFrame:
    summary_path = input_dir / "ieee118_fulltruth_summary.csv"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing full-truth summary CSV: {summary_path}")
    table = pd.read_csv(summary_path)
    for column in ["converged", "critical"]:
        if column in table:
            table[column] = table[column].astype(bool)
    return table


def build_top_load_shed_table(table: pd.DataFrame, top_k_values: list[int]) -> pd.DataFrame:
    sorted_table = table.sort_values(
        ["total_load_shed_mw", "final_max_loading_ratio", "path"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    records: list[dict] = []
    max_k = min(max(top_k_values), len(sorted_table)) if top_k_values else 0
    for idx, row in sorted_table.head(max_k).iterrows():
        rank = int(idx) + 1
        buckets = [f"top_{k}" for k in sorted(top_k_values) if rank <= k]
        record = row.to_dict()
        record["top_rank"] = rank
        record["top_bucket"] = ",".join(buckets)
        records.append(record)
    columns = ["top_rank", "top_bucket"] + [column for column in table.columns if column not in {"top_rank", "top_bucket"}]
    return pd.DataFrame(records, columns=columns)


def build_line_frequency_table(table: pd.DataFrame) -> pd.DataFrame:
    labels = sorted(set(table["first_line"].astype(str)).union(set(table["second_line"].astype(str))))
    critical = table[table["critical"]].copy()
    first_counts = critical.groupby("first_line").size()
    second_counts = critical.groupby("second_line").size()
    total_first = table.groupby("first_line").size()
    total_second = table.groupby("second_line").size()
    records = []
    for label in labels:
        as_first_critical = int(first_counts.get(label, 0))
        as_second_critical = int(second_counts.get(label, 0))
        as_first_total = int(total_first.get(label, 0))
        as_second_total = int(total_second.get(label, 0))
        records.append(
            {
                "line_label": label,
                "as_first_critical_count": as_first_critical,
                "as_first_total_count": as_first_total,
                "as_first_critical_frequency": as_first_critical / as_first_total if as_first_total else 0.0,
                "as_second_critical_count": as_second_critical,
                "as_second_total_count": as_second_total,
                "as_second_critical_frequency": as_second_critical / as_second_total if as_second_total else 0.0,
                "total_critical_count": as_first_critical + as_second_critical,
            }
        )
    return pd.DataFrame(records).sort_values(
        ["total_critical_count", "as_first_critical_count", "as_second_critical_count", "line_label"],
        ascending=[False, False, False, True],
    )


def high_risk_patterns(table: pd.DataFrame, limit: int) -> list[dict]:
    critical = table[table["critical"]].copy()
    if critical.empty:
        return []
    grouped = (
        critical.groupby(["first_line", "second_line", "path"], as_index=False)
        .agg(
            critical_count=("critical", "size"),
            max_total_load_shed_mw=("total_load_shed_mw", "max"),
            mean_total_load_shed_mw=("total_load_shed_mw", "mean"),
            max_final_max_loading_ratio=("final_max_loading_ratio", "max"),
        )
        .sort_values(["critical_count", "max_total_load_shed_mw", "path"], ascending=[False, False, True])
        .head(limit)
    )
    return grouped.to_dict("records")


def build_summary(table: pd.DataFrame, top_table: pd.DataFrame, top_k_values: list[int], pattern_limit: int) -> dict:
    total_paths = int(len(table))
    converged_paths = int(table["converged"].sum()) if "converged" in table else 0
    error_mask = table["error"].fillna("").astype(str).str.len() > 0 if "error" in table else pd.Series(False, index=table.index)
    error_paths = int(error_mask.sum())
    critical_paths = int(table["critical"].sum()) if "critical" in table else 0
    max_row = (
        table.sort_values(["total_load_shed_mw", "final_max_loading_ratio", "path"], ascending=[False, False, True])
        .head(1)
        .to_dict("records")
    )
    return {
        "total_paths": total_paths,
        "converged_paths": converged_paths,
        "error_paths": error_paths,
        "critical_paths": critical_paths,
        "critical_ratio": critical_paths / total_paths if total_paths else 0.0,
        "max_load_shed_path": max_row[0] if max_row else {},
        "top_load_shed_counts": {f"top_{k}": int(min(k, len(top_table))) for k in sorted(top_k_values)},
        "total_load_shed_mw_describe": describe_series(table["total_load_shed_mw"]),
        "final_max_loading_ratio_describe": describe_series(table["final_max_loading_ratio"]),
        "high_risk_ordered_patterns": high_risk_patterns(table, pattern_limit),
    }


def write_readme(output_dir: Path, summary: dict) -> None:
    lines = [
        "# IEEE 118 Full-Truth Audit",
        "",
        "This audit summarizes IEEE 118 ordered N-2 cascade full-truth rows.",
        "",
        f"- Total paths: {summary['total_paths']}",
        f"- Converged paths: {summary['converged_paths']}",
        f"- Error paths: {summary['error_paths']}",
        f"- Critical paths: {summary['critical_paths']}",
        f"- Critical ratio: {summary['critical_ratio']:.6f}",
        "",
        "This is still full-truth data preparation. It is not IEEE 118 GCN search efficiency validation.",
    ]
    (output_dir / "ieee118_fulltruth_readme.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(input_dir: Path, output_dir: Path, top_k_values: list[int], pattern_limit: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    table = load_summary(input_dir)
    top_table = build_top_load_shed_table(table, top_k_values)
    frequency_table = build_line_frequency_table(table)
    error_mask = table["error"].fillna("").astype(str).str.len() > 0 if "error" in table else pd.Series(False, index=table.index)
    error_table = table[error_mask].copy()
    summary = build_summary(table, top_table, top_k_values, pattern_limit)

    (output_dir / "ieee118_fulltruth_audit_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    top_table.to_csv(output_dir / "ieee118_top_load_shed_paths.csv", index=False, encoding="utf-8-sig")
    frequency_table.to_csv(output_dir / "ieee118_line_critical_frequency.csv", index=False, encoding="utf-8-sig")
    error_table.to_csv(output_dir / "ieee118_error_paths.csv", index=False, encoding="utf-8-sig")
    write_readme(output_dir, summary)
    return summary


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir or args.input_dir
    summary = analyze(args.input_dir, output_dir, args.top_k, args.pattern_limit)
    print(f"IEEE 118 full-truth audit written to {output_dir}")
    print(f"total_paths={summary['total_paths']}")
    print(f"converged_paths={summary['converged_paths']}")
    print(f"critical_paths={summary['critical_paths']}")
    print(f"error_paths={summary['error_paths']}")


if __name__ == "__main__":
    main()
