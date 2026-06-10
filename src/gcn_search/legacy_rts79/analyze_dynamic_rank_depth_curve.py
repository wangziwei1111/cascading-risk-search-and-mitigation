from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from compute_dynamic_stress_score import compute_dynamic_stress_score


GROUPS = ["learned_mlp_top100", "pio_gcn_top100", "lodf_top100"]


def analyze_dynamic_rank_depth_curve(
    cases_root: str | Path,
    results_root: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_method_comparison_summary",
    ks: tuple[int, ...] = (10, 20, 50, 100),
    output_prefix: str = "dynamic_rank_depth_curve",
) -> dict:
    cases_root = Path(cases_root)
    results_root = Path(results_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for group in GROUPS:
        dynamic_csv = results_root / group / "simulink_dynamic_simulation_results.csv"
        topk_csv = cases_root / group / "simulink_topk_paths.csv"
        if not dynamic_csv.exists() or not topk_csv.exists():
            continue
        dynamic = pd.read_csv(dynamic_csv)
        topk = pd.read_csv(topk_csv)
        stress = compute_dynamic_stress_score(dynamic_csv, results_root / group / "dynamic_stress_score_for_rank_curve.csv")
        merged = topk.merge(dynamic, on="case_id", how="left").merge(stress[["case_id", "dynamic_stress_score"]], on="case_id", how="left")
        merged["dynamic_unstable"] = merged["dynamic_unstable"].fillna(False).astype(bool)
        merged = merged.sort_values("path_rank")
        method = group.removesuffix("_top100")
        for k in ks:
            sub = merged.head(k)
            if sub.empty:
                continue
            rows.append(
                {
                    "method": method,
                    "k": int(k),
                    "dynamic_precision_at_k": float(sub["dynamic_unstable"].mean()),
                    "mean_dynamic_stress_score_at_k": float(pd.to_numeric(sub["dynamic_stress_score"], errors="coerce").mean()),
                    "cumulative_security_actions": int(pd.to_numeric(sub.get("security_redispatch_count", 0), errors="coerce").fillna(0).sum()),
                    "cumulative_passive_relay_trips": int(pd.to_numeric(sub.get("passive_relay_trip_count", 0), errors="coerce").fillna(0).sum()),
                    "cumulative_dynamic_load_shed_mw": float(pd.to_numeric(sub.get("dynamic_load_shed_mw", 0), errors="coerce").fillna(0).sum()),
                    "mean_frequency_nadir_hz_at_k": float(pd.to_numeric(sub.get("frequency_nadir_hz", 50.0), errors="coerce").mean()),
                    "mean_rotor_angle_coi_deg_at_k": float(pd.to_numeric(sub.get("max_rotor_angle_separation_coi_deg", sub.get("max_rotor_angle_separation_deg", 0.0)), errors="coerce").mean()),
                }
            )
    table = pd.DataFrame(rows)
    csv_path = out / f"{output_prefix}.csv"
    brief_path = out / f"{output_prefix}_brief.md"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    _brief(table, brief_path)
    return {"csv": str(csv_path), "brief": str(brief_path), "num_rows": int(len(table))}


def _brief(table: pd.DataFrame, path: Path) -> None:
    lines = [
        "# Dynamic Rank-Depth Curve Brief",
        "",
        "This curve checks whether dynamic stress appears earlier in the ranking. It is preliminary diagnostic evidence only.",
        "",
        "| method | k | precision | mean stress |",
        "| --- | ---: | ---: | ---: |",
    ]
    for _, row in table.iterrows():
        lines.append(f"| {row['method']} | {int(row['k'])} | {float(row['dynamic_precision_at_k']):.4f} | {float(row['mean_dynamic_stress_score_at_k']):.4f} |")
    lines.append("")
    lines.append("No dynamic recall is reported because no full dynamic truth is available.")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze rank-depth dynamic stress curves.")
    parser.add_argument("--cases-root", required=True)
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_method_comparison_summary")
    parser.add_argument("--ks", type=int, nargs="+", default=[10, 20, 50, 100])
    parser.add_argument("--output-prefix", default="dynamic_rank_depth_curve")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_dynamic_rank_depth_curve(args.cases_root, args.results_root, args.output_dir, tuple(args.ks), args.output_prefix)


if __name__ == "__main__":
    main()
