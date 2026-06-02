from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def analyze_seed(eval_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    truth = pd.read_csv(eval_dir / "rts79_search_eval_exhaustive_truth.csv")
    order = pd.read_csv(eval_dir / "rts79_search_order.csv")
    critical_truth = truth.loc[truth["critical"].astype(bool)].copy()
    active_critical_paths = set(critical_truth["path"].astype(str))
    full_critical_paths = set(critical_truth["full_cascade_path"].dropna().astype(str))
    full_critical_paths.discard("")

    summaries = []
    curves = []
    for method, group in order.groupby("search_method", sort=False):
        group = group.sort_values("search_attempt").copy()
        active_found: set[str] = set()
        full_found: set[str] = set()
        records = []
        for _, row in group.iterrows():
            path = str(row["path"])
            full_path = "" if pd.isna(row.get("full_cascade_path", "")) else str(row.get("full_cascade_path", ""))
            if path in active_critical_paths:
                active_found.add(path)
            if full_path in full_critical_paths:
                full_found.add(full_path)
            records.append(
                {
                    "search_method": method,
                    "search_attempt": int(row["search_attempt"]),
                    "path": path,
                    "full_cascade_path": full_path,
                    "active_found_count": len(active_found),
                    "full_found_count": len(full_found),
                }
            )
        curve = pd.DataFrame(records)
        curves.append(curve)
        summaries.append(
            {
                "search_method": method,
                "active_critical_count": len(active_critical_paths),
                "full_critical_count": len(full_critical_paths),
                "attempts_to_find_all_active": _first_attempt(curve, "active_found_count", len(active_critical_paths)),
                "attempts_to_find_all_full": _first_attempt(curve, "full_found_count", len(full_critical_paths)),
                "active_found_after_50": _found_at(curve, "active_found_count", 50),
                "active_found_after_100": _found_at(curve, "active_found_count", 100),
                "active_found_after_200": _found_at(curve, "active_found_count", 200),
                "full_found_after_50": _found_at(curve, "full_found_count", 50),
                "full_found_after_100": _found_at(curve, "full_found_count", 100),
                "full_found_after_200": _found_at(curve, "full_found_count", 200),
            }
        )
    return pd.DataFrame(summaries), pd.concat(curves, ignore_index=True)


def _first_attempt(curve: pd.DataFrame, column: str, target: int) -> float:
    matched = curve.loc[curve[column] >= target, "search_attempt"]
    return float(matched.iloc[0]) if not matched.empty else np.nan


def _found_at(curve: pd.DataFrame, column: str, attempt: int) -> int:
    prefix = curve.loc[curve["search_attempt"] <= attempt, column]
    return int(prefix.max()) if not prefix.empty else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare RTS-79 active-path and full-path search counting conventions.")
    parser.add_argument("--eval-root", default="outputs", help="Directory containing per-seed evaluation folders.")
    parser.add_argument("--prefix", default="paper_gcn_search_eval_800_reachable_seed_", help="Per-seed folder prefix.")
    parser.add_argument("--seeds", nargs="+", type=int, default=[20260722, 20260723, 20260724, 20260725, 20260726])
    parser.add_argument("--output-dir", default="outputs/rts79_search_counting_convention_analysis")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    all_summary = []
    for seed in args.seeds:
        eval_dir = Path(args.eval_root) / f"{args.prefix}{seed}"
        summary, curve = analyze_seed(eval_dir)
        summary.insert(0, "seed", seed)
        curve.insert(0, "seed", seed)
        summary.to_csv(out / f"seed_{seed}_counting_summary.csv", index=False, encoding="utf-8-sig")
        curve.to_csv(out / f"seed_{seed}_counting_curve.csv", index=False, encoding="utf-8-sig")
        all_summary.append(summary)
    combined = pd.concat(all_summary, ignore_index=True)
    combined.to_csv(out / "per_seed_counting_summary.csv", index=False, encoding="utf-8-sig")
    mean = (
        combined.groupby("search_method", as_index=False)
        .agg(
            mean_active_critical_count=("active_critical_count", "mean"),
            mean_full_critical_count=("full_critical_count", "mean"),
            mean_attempts_to_find_all_active=("attempts_to_find_all_active", "mean"),
            mean_attempts_to_find_all_full=("attempts_to_find_all_full", "mean"),
            mean_active_found_after_50=("active_found_after_50", "mean"),
            mean_active_found_after_100=("active_found_after_100", "mean"),
            mean_active_found_after_200=("active_found_after_200", "mean"),
            mean_full_found_after_50=("full_found_after_50", "mean"),
            mean_full_found_after_100=("full_found_after_100", "mean"),
            mean_full_found_after_200=("full_found_after_200", "mean"),
        )
        .sort_values("mean_attempts_to_find_all_active")
    )
    mean.to_csv(out / "mean_counting_summary.csv", index=False, encoding="utf-8-sig")
    print(mean.to_string(index=False))


if __name__ == "__main__":
    main()
