from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def compare_default_vs_calibrated_dynamic_smoke(
    default_summary_csv: str | Path,
    calibrated_summary_csv: str | Path,
    default_degeneracy_json: str | Path,
    calibrated_degeneracy_json: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_real_pipeline_summary",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    default_row = pd.read_csv(default_summary_csv).iloc[0].to_dict()
    calibrated_row = pd.read_csv(calibrated_summary_csv).iloc[0].to_dict()
    default_deg = json.loads(Path(default_degeneracy_json).read_text(encoding="utf-8"))
    calibrated_deg = json.loads(Path(calibrated_degeneracy_json).read_text(encoding="utf-8"))
    rows = [
        _comparison_row("default", default_row, default_deg),
        _comparison_row("calibrated", calibrated_row, calibrated_deg),
    ]
    comparison = pd.DataFrame(rows)
    csv_path = out / "default_vs_calibrated_dynamic_smoke_comparison.csv"
    md_path = out / "default_vs_calibrated_dynamic_smoke_comparison.md"
    comparison.to_csv(csv_path, index=False, encoding="utf-8-sig")
    md_path.write_text(_to_markdown(comparison), encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _comparison_row(label: str, row: dict, degeneracy: dict) -> dict:
    return {
        "variant": label,
        "result_scope": row.get("result_scope", ""),
        "top_k": int(row.get("top_k", 20)),
        "dynamic_precision_at_k": float(row.get("dynamic_precision_at_k", 0.0)),
        "passive_relay_trip_cases": int(row.get("cases_with_passive_relay_trip", 0)),
        "security_redispatch_cases": int(row.get("cases_with_security_redispatch_or_load_shed", 0)),
        "opa_critical_and_dynamic_unstable_count": int(row.get("opa_critical_and_dynamic_unstable_count", 0)),
        "opa_critical_but_dynamic_stable_count": int(row.get("opa_critical_but_dynamic_stable_count", 0)),
        "opa_noncritical_but_dynamic_unstable_count": int(row.get("opa_noncritical_but_dynamic_unstable_count", 0)),
        "total_dynamic_load_shed_mw": float(row.get("total_dynamic_load_shed_mw", 0.0)),
        "degeneracy_warning": bool(degeneracy.get("degeneracy_warning", False)),
        "note": "smoke-level only; no dynamic recall without full dynamic truth",
    }


def _to_markdown(comparison: pd.DataFrame) -> str:
    columns = list(comparison.columns)
    table_lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in comparison.iterrows():
        table_lines.append("| " + " | ".join(str(row[col]) for col in columns) + " |")
    lines = [
        "# Default vs Calibrated Dynamic Smoke Comparison",
        "",
        "Default result demonstrates pipeline execution. Calibrated result is intended to reduce all-passive-trip degeneracy. Both remain smoke-level only.",
        "",
        *table_lines,
        "",
    ]
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare default and calibrated Top20 dynamic smoke summaries.")
    parser.add_argument("--default-summary-csv", required=True)
    parser.add_argument("--calibrated-summary-csv", required=True)
    parser.add_argument("--default-degeneracy-json", required=True)
    parser.add_argument("--calibrated-degeneracy-json", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_real_pipeline_summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    compare_default_vs_calibrated_dynamic_smoke(
        args.default_summary_csv,
        args.calibrated_summary_csv,
        args.default_degeneracy_json,
        args.calibrated_degeneracy_json,
        args.output_dir,
    )


if __name__ == "__main__":
    main()
