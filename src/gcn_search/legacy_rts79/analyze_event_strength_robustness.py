from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


METHODS = ["learned_mlp", "pio_gcn", "lodf"]


def analyze_event_strength_robustness(
    grid_summary_csv: str | Path,
    method_summary_csv: str | Path,
    rank_depth_csv: str | Path,
    output_dir: str | Path,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    grid = pd.read_csv(grid_summary_csv)
    method_summary = pd.read_csv(method_summary_csv)
    rank_depth = pd.read_csv(rank_depth_csv)
    nondegenerate = grid[(grid["dynamic_unstable_fraction"].astype(float) > 0.0) & (grid["dynamic_unstable_fraction"].astype(float) < 1.0)].copy()
    robustness_limited = bool(len(nondegenerate) <= 1)
    top100 = method_summary[method_summary["top_k"].astype(int) == 100].copy()
    precisions = {method: _value(top100, method, "dynamic_precision_at_k") for method in METHODS}
    best_method = max(precisions, key=lambda name: precisions[name]) if precisions else ""
    learned_best_count = int(best_method == "learned_mlp") * max(1, len(nondegenerate))
    pio_best_count = int(best_method == "pio_gcn") * max(1, len(nondegenerate))
    lodf_best_count = int(best_method == "lodf") * max(1, len(nondegenerate))
    learned_advantage_robust = bool(
        len(nondegenerate) > 1
        and learned_best_count > max(pio_best_count, lodf_best_count)
        and precisions.get("learned_mlp", 0.0) > max(precisions.get("pio_gcn", 0.0), precisions.get("lodf", 0.0))
    )
    row = {
        "num_nondegenerate_settings": int(len(nondegenerate)),
        "robustness_limited_by_available_grid": robustness_limited,
        "learned_best_count": learned_best_count,
        "pio_best_count": pio_best_count,
        "lodf_best_count": lodf_best_count,
        "learned_mean_precision_over_settings": float(precisions.get("learned_mlp", 0.0)),
        "pio_mean_precision_over_settings": float(precisions.get("pio_gcn", 0.0)),
        "lodf_mean_precision_over_settings": float(precisions.get("lodf", 0.0)),
        "learned_advantage_robust": learned_advantage_robust,
        "top100_best_method": best_method,
        "rank_depth_rows": int(len(rank_depth)),
        "note": "preliminary diagnostic robustness envelope; no dynamic recall is reported",
    }
    table = pd.DataFrame([row])
    csv_path = out / "event_strength_robustness_summary.csv"
    json_path = out / "event_strength_robustness_summary.json"
    brief_path = out / "event_strength_robustness_brief.md"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(row, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_brief(row, brief_path)
    return {"csv": str(csv_path), "json": str(json_path), "brief": str(brief_path), **row}


def _value(table: pd.DataFrame, method: str, column: str) -> float:
    row = table[table["method"].astype(str) == method]
    if row.empty or column not in row.columns:
        return 0.0
    return float(pd.to_numeric(row[column], errors="coerce").fillna(0.0).iloc[0])


def _write_brief(row: dict, path: Path) -> None:
    lines = [
        "# Event Strength Robustness Brief",
        "",
        "This is a preliminary diagnostic robustness check, not a final dynamic proof.",
        "",
        f"num_nondegenerate_settings = {row['num_nondegenerate_settings']}",
        f"robustness_limited_by_available_grid = {row['robustness_limited_by_available_grid']}",
        f"learned_advantage_robust = {row['learned_advantage_robust']}",
        f"top100_best_method = {row['top100_best_method']}",
        "",
        "No dynamic recall is reported because no full dynamic truth exists.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze event-strength robustness for dynamic method comparison.")
    parser.add_argument("--grid-summary-csv", required=True)
    parser.add_argument("--method-summary-csv", required=True)
    parser.add_argument("--rank-depth-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_event_strength_robustness(args.grid_summary_csv, args.method_summary_csv, args.rank_depth_csv, args.output_dir)


if __name__ == "__main__":
    main()
