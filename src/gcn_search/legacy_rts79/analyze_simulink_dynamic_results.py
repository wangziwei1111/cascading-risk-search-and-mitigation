from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def analyze_simulink_dynamic_results(
    dynamic_results_csv: str | Path,
    topk_paths_csv: str | Path,
    output_dir: str | Path,
    full_dynamic_truth: bool = False,
    dynamic_truth_csv: str | Path | None = None,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dynamic = pd.read_csv(dynamic_results_csv)
    topk = pd.read_csv(topk_paths_csv)
    merged = topk.merge(dynamic, on="case_id", how="left")
    merged["dynamic_unstable"] = merged["dynamic_unstable"].fillna(False).astype(bool)
    truth = _load_dynamic_truth(dynamic, dynamic_truth_csv, full_dynamic_truth)
    dynamic_recall_available = truth is not None
    dynamic_unstable_total = int(truth["dynamic_unstable"].astype(bool).sum()) if dynamic_recall_available else None
    precision_rows = []
    for k in [20, 50, 100, 200]:
        subset = merged.sort_values("path_rank").head(k)
        if subset.empty:
            precision = 0.0
        else:
            precision = float(subset["dynamic_unstable"].sum() / len(subset))
        found_unstable = int(subset["dynamic_unstable"].sum())
        row = {"top_k": k, "num_simulated": int(len(subset)), "dynamic_unstable_count": found_unstable, "dynamic_precision_at_k": precision}
        if dynamic_recall_available:
            row["dynamic_recall_at_k"] = float(found_unstable / dynamic_unstable_total) if dynamic_unstable_total else 0.0
        precision_rows.append(row)
    precision = pd.DataFrame(precision_rows)
    overlap = _overlap(merged)
    failures = merged[merged["dynamic_unstable"]].copy()
    summary = {
        "num_cases": int(len(merged)),
        "full_dynamic_truth": bool(dynamic_recall_available),
        "dynamic_recall_available": bool(dynamic_recall_available),
        "dynamic_truth_csv": str(dynamic_truth_csv) if dynamic_truth_csv else None,
        "dynamic_unstable_total": dynamic_unstable_total,
        "dynamic_unstable_count": int(merged["dynamic_unstable"].sum()),
        "opa_critical_and_dynamic_unstable_count": int(overlap.loc[overlap["metric"] == "opa_critical_and_dynamic_unstable_count", "value"].iloc[0]),
        "mean_frequency_nadir_hz": float(pd.to_numeric(merged["frequency_nadir_hz"], errors="coerce").mean()),
        "min_frequency_nadir_hz": float(pd.to_numeric(merged["frequency_nadir_hz"], errors="coerce").min()),
        "max_rotor_angle_separation_deg": float(pd.to_numeric(merged["max_rotor_angle_separation_deg"], errors="coerce").max()),
        "note": "dynamic_recall@K is reported only when --dynamic-truth-csv is provided or the result CSV is explicitly marked as full_dynamic_truth=true.",
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


def _load_dynamic_truth(dynamic: pd.DataFrame, dynamic_truth_csv: str | Path | None, full_dynamic_truth: bool) -> pd.DataFrame | None:
    if dynamic_truth_csv:
        truth = pd.read_csv(dynamic_truth_csv)
    elif full_dynamic_truth and "full_dynamic_truth" in dynamic.columns and dynamic["full_dynamic_truth"].map(_to_bool).all():
        truth = dynamic.copy()
    else:
        return None
    if "dynamic_unstable" not in truth.columns:
        raise RuntimeError("Dynamic truth CSV must contain dynamic_unstable column.")
    truth = truth.copy()
    truth["dynamic_unstable"] = truth["dynamic_unstable"].map(_to_bool)
    return truth


def _to_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze simplified Simulink dynamic validation results.")
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--topk-paths-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_analysis")
    parser.add_argument("--full-dynamic-truth", action="store_true")
    parser.add_argument("--dynamic-truth-csv", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_simulink_dynamic_results(
        args.dynamic_results_csv,
        args.topk_paths_csv,
        args.output_dir,
        full_dynamic_truth=args.full_dynamic_truth,
        dynamic_truth_csv=args.dynamic_truth_csv,
    )


if __name__ == "__main__":
    main()
