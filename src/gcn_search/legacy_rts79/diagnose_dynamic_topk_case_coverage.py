from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


METHODS = ["learned_mlp", "pio_gcn", "lodf"]


def diagnose_dynamic_topk_case_coverage(
    ranking_csv: str | Path,
    input_root: str | Path,
    cases_root: str | Path,
    results_root: str | Path,
    output_dir: str | Path,
    top_k: tuple[int, ...] = (50, 100),
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ranking = pd.read_csv(ranking_csv)
    rows: list[dict] = []
    for method in METHODS:
        for k in top_k:
            group = f"{method}_top{k}"
            input_csv = Path(input_root) / f"{method}_top{k}_input_paths.csv"
            case_manifest = Path(cases_root) / group / "simulink_dynamic_case_manifest.csv"
            matlab_batch = Path(cases_root) / group / "matlab_batch_input.csv"
            simulation_csv = Path(results_root) / group / "simulink_dynamic_simulation_results.csv"
            input_paths = _read_csv(input_csv)
            manifest = _read_csv(case_manifest)
            batch = _read_csv(matlab_batch)
            simulation = _read_csv(simulation_csv)
            invalid_stats = _invalid_stats(input_paths)
            exported = int(len(manifest)) if not manifest.empty else 0
            simulated = int(len(simulation)) if not simulation.empty else 0
            dropped = int(max(0, k - simulated))
            reason = _reason(k, input_paths, manifest, simulation, invalid_stats)
            rows.append(
                {
                    "method": method,
                    "requested_top_k": int(k),
                    "ranking_rows_available": int(len(ranking)),
                    "unique_paths_available": int(ranking["path"].nunique()) if "path" in ranking.columns else int(len(ranking)),
                    "input_paths_rows": int(len(input_paths)),
                    "unique_input_paths": int(input_paths["path"].nunique()) if "path" in input_paths.columns else int(len(input_paths)),
                    "exported_case_count": exported,
                    "matlab_batch_case_count": int(batch["case_id"].nunique()) if "case_id" in batch.columns else 0,
                    "simulated_case_count": simulated,
                    "duplicate_path_count": int(max(0, len(input_paths) - input_paths["path"].nunique())) if "path" in input_paths.columns else 0,
                    "invalid_path_count": invalid_stats["invalid_path_count"],
                    "same_line_path_count": invalid_stats["same_line_path_count"],
                    "missing_line_label_count": invalid_stats["missing_line_label_count"],
                    "dropped_case_count": dropped,
                    "dropped_reason_summary": reason,
                    "coverage_ratio": float(simulated / max(k, 1)),
                }
            )
    table = pd.DataFrame(rows)
    csv_path = out / "dynamic_topk_case_coverage_diagnostics.csv"
    json_path = out / "dynamic_topk_case_coverage_diagnostics.json"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    payload = {
        "ranking_csv": str(ranking_csv),
        "input_root": str(input_root),
        "cases_root": str(cases_root),
        "results_root": str(results_root),
        "num_rows": int(len(table)),
        "min_coverage_ratio": float(table["coverage_ratio"].min()) if not table.empty else 0.0,
        "coverage_passed": bool(not table.empty and (table["coverage_ratio"] >= 0.95).all()),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), **payload}


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _invalid_stats(table: pd.DataFrame) -> dict[str, int]:
    invalid = 0
    same_line = 0
    missing = 0
    if table.empty:
        return {"invalid_path_count": 0, "same_line_path_count": 0, "missing_line_label_count": 0}
    for _, row in table.iterrows():
        first, second = _extract_lines(row)
        if not first or not second:
            invalid += 1
            missing += 1
        elif first == second:
            invalid += 1
            same_line += 1
    return {"invalid_path_count": invalid, "same_line_path_count": same_line, "missing_line_label_count": missing}


def _extract_lines(row: pd.Series) -> tuple[str, str]:
    if "path" in row and pd.notna(row["path"]):
        parts = re.split(r"\s*->\s*", str(row["path"]).strip().upper())
        if len(parts) == 2:
            return _normalize_line(parts[0]), _normalize_line(parts[1])
    return _normalize_line(row.get("first_line", "")), _normalize_line(row.get("second_line", ""))


def _normalize_line(value: object) -> str:
    match = re.search(r"L?(\d+)", str(value).upper())
    if not match:
        return ""
    idx = int(match.group(1))
    if idx < 1 or idx > 38:
        return ""
    return f"L{idx:02d}"


def _reason(k: int, input_paths: pd.DataFrame, manifest: pd.DataFrame, simulation: pd.DataFrame, invalid_stats: dict[str, int]) -> str:
    if len(simulation) >= k:
        return "none"
    reasons = []
    if input_paths.empty:
        reasons.append("missing_input_paths")
    if "path" in input_paths.columns and len(input_paths) > input_paths["path"].nunique():
        reasons.append("duplicate_input_paths")
    if invalid_stats["invalid_path_count"]:
        reasons.append("invalid_or_missing_line_label")
    if len(manifest) < k:
        reasons.append("case_export_shortfall")
    if not simulation.empty and len(simulation) < len(manifest):
        reasons.append("matlab_simulation_shortfall")
    if not reasons:
        reasons.append("unknown_shortfall")
    return ";".join(reasons)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose Top-K case coverage for dynamic method comparison.")
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--cases-root", required=True)
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--top-k", nargs="+", type=int, default=[50, 100])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    diagnose_dynamic_topk_case_coverage(args.ranking_csv, args.input_root, args.cases_root, args.results_root, args.output_dir, tuple(args.top_k))


if __name__ == "__main__":
    main()
