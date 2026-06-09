from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def analyze_opa_dynamic_disagreement(
    topk_paths_csv: str | Path,
    dynamic_results_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_disagreement",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = pd.read_csv(topk_paths_csv)
    dynamic = pd.read_csv(dynamic_results_csv)
    merged = paths.merge(dynamic, on="case_id", how="left")
    merged["opa_is_critical_bool"] = merged.get("opa_is_critical", False).map(_to_bool)
    merged["dynamic_unstable_bool"] = merged.get("dynamic_unstable", False).map(_to_bool)
    opa_critical_dynamic_stable = merged[merged["opa_is_critical_bool"] & ~merged["dynamic_unstable_bool"]].copy()
    opa_noncritical_dynamic_unstable = merged[~merged["opa_is_critical_bool"] & merged["dynamic_unstable_bool"]].copy()
    high_dynamic_risk_low_opa = opa_noncritical_dynamic_unstable.sort_values(
        ["frequency_nadir_hz", "max_rotor_angle_separation_deg", "max_line_loading_ratio"],
        ascending=[True, False, False],
    ).copy()
    reason_counts = (
        merged["unstable_reason"].fillna("missing").astype(str).str.split(";").explode().value_counts().reset_index()
    )
    reason_counts.columns = ["unstable_reason", "count"]
    summary = pd.DataFrame(
        [
            {"metric": "num_paths", "value": int(len(merged))},
            {"metric": "opa_critical_dynamic_stable_count", "value": int(len(opa_critical_dynamic_stable))},
            {"metric": "opa_noncritical_dynamic_unstable_count", "value": int(len(opa_noncritical_dynamic_unstable))},
            {"metric": "dynamic_unstable_count", "value": int(merged["dynamic_unstable_bool"].sum())},
            {"metric": "lowest_frequency_nadir_hz", "value": float(pd.to_numeric(merged["frequency_nadir_hz"], errors="coerce").min())},
            {"metric": "max_rotor_angle_separation_deg", "value": float(pd.to_numeric(merged["max_rotor_angle_separation_deg"], errors="coerce").max())},
            {"metric": "max_line_loading_ratio", "value": float(pd.to_numeric(merged["max_line_loading_ratio"], errors="coerce").max())},
        ]
    )
    summary.to_csv(out / "opa_dynamic_disagreement_summary.csv", index=False, encoding="utf-8-sig")
    opa_critical_dynamic_stable.to_csv(out / "opa_critical_dynamic_stable_cases.csv", index=False, encoding="utf-8-sig")
    opa_noncritical_dynamic_unstable.to_csv(out / "opa_noncritical_dynamic_unstable_cases.csv", index=False, encoding="utf-8-sig")
    high_dynamic_risk_low_opa.head(10).to_csv(out / "high_dynamic_risk_low_opa_shed_cases.csv", index=False, encoding="utf-8-sig")
    reason_counts.to_csv(out / "dynamic_unstable_reason_distribution.csv", index=False, encoding="utf-8-sig")
    merged.sort_values("frequency_nadir_hz", ascending=True).head(10).to_csv(out / "top10_lowest_frequency_nadir.csv", index=False, encoding="utf-8-sig")
    merged.sort_values("max_rotor_angle_separation_deg", ascending=False).head(10).to_csv(out / "top10_largest_rotor_angle.csv", index=False, encoding="utf-8-sig")
    merged.sort_values("max_line_loading_ratio", ascending=False).head(10).to_csv(out / "top10_largest_line_loading.csv", index=False, encoding="utf-8-sig")
    return {"output_dir": str(out), "summary_csv": str(out / "opa_dynamic_disagreement_summary.csv")}


def _to_bool(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze OPA/static and dynamic validation disagreement.")
    parser.add_argument("--topk-paths-csv", required=True)
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_disagreement")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_opa_dynamic_disagreement(args.topk_paths_csv, args.dynamic_results_csv, args.output_dir)


if __name__ == "__main__":
    main()
