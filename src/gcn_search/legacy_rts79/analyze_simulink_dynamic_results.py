from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def analyze_simulink_dynamic_results(dynamic_results_csv: str | Path, topk_paths_csv: str | Path, output_dir: str | Path, full_dynamic_truth: bool = False) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dynamic = pd.read_csv(dynamic_results_csv)
    topk = pd.read_csv(topk_paths_csv)
    merged = topk.merge(dynamic, on="case_id", how="left")
    merged["dynamic_unstable"] = merged["dynamic_unstable"].fillna(False).astype(bool)
    precision_rows = []
    for k in [20, 50, 100, 200]:
        subset = merged.sort_values("path_rank").head(k)
        if subset.empty:
            precision = 0.0
        else:
            precision = float(subset["dynamic_unstable"].sum() / len(subset))
        row = {"top_k": k, "num_simulated": int(len(subset)), "dynamic_unstable_count": int(subset["dynamic_unstable"].sum()), "dynamic_precision_at_k": precision}
        if full_dynamic_truth:
            row["dynamic_recall_at_k"] = precision
        precision_rows.append(row)
    precision = pd.DataFrame(precision_rows)
    overlap = _overlap(merged)
    failures = merged[merged["dynamic_unstable"]].copy()
    summary = {
        "num_cases": int(len(merged)),
        "full_dynamic_truth": bool(full_dynamic_truth),
        "dynamic_unstable_count": int(merged["dynamic_unstable"].sum()),
        "opa_critical_and_dynamic_unstable_count": int(overlap.loc[overlap["metric"] == "opa_critical_and_dynamic_unstable_count", "value"].iloc[0]),
        "mean_frequency_nadir_hz": float(pd.to_numeric(merged["frequency_nadir_hz"], errors="coerce").mean()),
        "min_frequency_nadir_hz": float(pd.to_numeric(merged["frequency_nadir_hz"], errors="coerce").min()),
        "max_rotor_angle_separation_deg": float(pd.to_numeric(merged["max_rotor_angle_separation_deg"], errors="coerce").max()),
        "note": "dynamic_recall@K is reported only when full_dynamic_truth=true; otherwise only dynamic_precision@K is valid.",
    }
    precision.to_csv(out / "simulink_dynamic_precision_at_k.csv", index=False, encoding="utf-8-sig")
    overlap.to_csv(out / "simulink_opa_dynamic_overlap.csv", index=False, encoding="utf-8-sig")
    failures.to_csv(out / "simulink_dynamic_failure_cases.csv", index=False, encoding="utf-8-sig")
    (out / "simulink_dynamic_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output_dir": str(out), "summary": str(out / "simulink_dynamic_summary.json")}


def _overlap(merged: pd.DataFrame) -> pd.DataFrame:
    opa = merged["opa_is_critical"].map(_to_bool) if "opa_is_critical" in merged else pd.Series([False] * len(merged))
    dyn = merged["dynamic_unstable"].astype(bool)
    rows = [
        {"metric": "opa_critical_and_dynamic_unstable_count", "value": int((opa & dyn).sum())},
        {"metric": "opa_critical_but_dynamic_stable_count", "value": int((opa & ~dyn).sum())},
        {"metric": "opa_noncritical_but_dynamic_unstable_count", "value": int((~opa & dyn).sum())},
        {"metric": "opa_noncritical_and_dynamic_stable_count", "value": int((~opa & ~dyn).sum())},
    ]
    return pd.DataFrame(rows)


def _to_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze simplified Simulink dynamic validation results.")
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--topk-paths-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_analysis")
    parser.add_argument("--full-dynamic-truth", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_simulink_dynamic_results(args.dynamic_results_csv, args.topk_paths_csv, args.output_dir, full_dynamic_truth=args.full_dynamic_truth)


if __name__ == "__main__":
    main()
