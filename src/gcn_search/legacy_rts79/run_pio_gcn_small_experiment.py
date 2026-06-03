from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, evaluate_pio_gcn_topk


@dataclass(frozen=True)
class SmallExperimentConfig:
    model: str
    normalizer: str
    output_dir: str
    baseline_summary_dir: str | None = None
    seed_start: int = 20260722
    num_seeds: int = 10
    top_k: tuple[int, ...] = (20, 50, 100)
    beta: float = 1.2
    security_limit: float = 1.0
    run_full_truth: bool = False
    max_paths_for_smoke_test: int | None = None
    measured_state_json: str | None = None


def run_small_experiment(config: SmallExperimentConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")

    per_seed_rows: list[dict] = []
    for offset in range(config.num_seeds):
        seed = config.seed_start + offset
        seed_output = out / f"seed_{seed}"
        seed_start_time = time.time()
        result = evaluate_pio_gcn_topk(
            PioTopkConfig(
                model=config.model,
                normalizer=config.normalizer,
                output_dir=str(seed_output),
                seed=seed,
                beta=config.beta,
                security_limit=config.security_limit,
                top_k=config.top_k,
                measured_state_json=config.measured_state_json,
                run_full_truth=config.run_full_truth,
                max_paths_for_smoke_test=config.max_paths_for_smoke_test,
            )
        )
        seed_runtime = time.time() - seed_start_time
        for row in result["summary"]:
            per_seed_rows.append(
                {
                    "seed": seed,
                    "top_k": int(row["top_k"]),
                    "num_simulated_paths": int(row["num_simulated_paths"]),
                    "num_critical_found": int(row["num_critical_found"]),
                    "critical_path_recall": row.get("critical_path_recall", ""),
                    "smoke_recall": row.get("smoke_recall", ""),
                    "runtime_seconds": float(seed_runtime),
                    "used_measured_state": bool(row.get("used_measured_state", False)),
                    "simulation_initial_source": row.get("simulation_initial_source", ""),
                    "output_dir": str(seed_output),
                    "notes": row.get("notes", ""),
                }
            )

    per_seed = pd.DataFrame(per_seed_rows)
    per_seed.to_csv(out / "per_seed_summary.csv", index=False, encoding="utf-8-sig")
    aggregate = _make_aggregate_summary(per_seed, config)
    aggregate.to_csv(out / "aggregate_summary.csv", index=False, encoding="utf-8-sig")
    comparison = _make_method_comparison(aggregate, config)
    comparison.to_csv(out / "method_comparison_summary.csv", index=False, encoding="utf-8-sig")
    return {
        "output_dir": str(out),
        "per_seed_summary": str(out / "per_seed_summary.csv"),
        "aggregate_summary": str(out / "aggregate_summary.csv"),
        "method_comparison_summary": str(out / "method_comparison_summary.csv"),
    }


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _make_aggregate_summary(per_seed: pd.DataFrame, config: SmallExperimentConfig) -> pd.DataFrame:
    rows = []
    has_full_recall = config.run_full_truth and per_seed["critical_path_recall"].astype(str).str.len().gt(0).any()
    for top_k, group in per_seed.groupby("top_k", sort=True):
        row = {
            "top_k": int(top_k),
            "num_seeds": int(group["seed"].nunique()),
            "mean_num_critical_found": float(group["num_critical_found"].mean()),
            "std_num_critical_found": float(group["num_critical_found"].std(ddof=0)),
            "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
            "mean_num_simulated_paths": float(group["num_simulated_paths"].mean()),
            "notes": "full truth recall" if has_full_recall else "smoke truth only; do not report as formal recall",
        }
        if has_full_recall:
            recall = _to_numeric(group["critical_path_recall"]).dropna()
            row["mean_critical_path_recall"] = float(recall.mean()) if not recall.empty else ""
            row["std_critical_path_recall"] = float(recall.std(ddof=0)) if not recall.empty else ""
        else:
            smoke = _to_numeric(group["smoke_recall"]).dropna()
            row["mean_smoke_recall"] = float(smoke.mean()) if not smoke.empty else ""
            row["std_smoke_recall"] = float(smoke.std(ddof=0)) if not smoke.empty else ""
        rows.append(row)
    return pd.DataFrame(rows)


def _make_method_comparison(aggregate: pd.DataFrame, config: SmallExperimentConfig) -> pd.DataFrame:
    rows = []
    if config.baseline_summary_dir:
        baseline_path = Path(config.baseline_summary_dir) / "rts79_search_efficiency_summary.csv"
        if baseline_path.exists():
            baseline = pd.read_csv(baseline_path)
            preferred = baseline[baseline["search_method"].astype(str).str.contains("GCN", case=False, na=False)]
            baseline_row = preferred.iloc[0] if not preferred.empty else baseline.iloc[0]
            rows.append(
                {
                    "method": "original_GCN_path_prob_smoke_baseline",
                    "top_k_or_attempts_to_find_all": baseline_row.get("attempts_to_find_all", ""),
                    "num_seeds": 1,
                    "mean_critical_found": baseline_row.get("found_after_100_attempts", ""),
                    "mean_recall_or_found_after_100": baseline_row.get("found_after_100_attempts", ""),
                    "mean_runtime_seconds": "",
                    "notes": f"read from {baseline_path}; baseline truth and PIO smoke truth may differ, so do not force direct comparison",
                }
            )
        else:
            rows.append(
                {
                    "method": "original_GCN_path_prob_smoke_baseline",
                    "top_k_or_attempts_to_find_all": "",
                    "num_seeds": 0,
                    "mean_critical_found": "",
                    "mean_recall_or_found_after_100": "",
                    "mean_runtime_seconds": "",
                    "notes": f"baseline CSV not found at {baseline_path}",
                }
            )
    else:
        rows.append(
            {
                "method": "original_GCN_path_prob_smoke_baseline",
                "top_k_or_attempts_to_find_all": "",
                "num_seeds": 0,
                "mean_critical_found": "",
                "mean_recall_or_found_after_100": "",
                "mean_runtime_seconds": "",
                "notes": "no baseline_summary_dir provided",
            }
        )

    for _, row in aggregate.iterrows():
        recall_value = row.get("mean_critical_path_recall", row.get("mean_smoke_recall", ""))
        rows.append(
            {
                "method": f"PIO_GCN_Top{int(row['top_k'])}",
                "top_k_or_attempts_to_find_all": int(row["top_k"]),
                "num_seeds": int(row["num_seeds"]),
                "mean_critical_found": float(row["mean_num_critical_found"]),
                "mean_recall_or_found_after_100": recall_value,
                "mean_runtime_seconds": float(row["mean_runtime_seconds"]),
                "notes": row["notes"],
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small multi-seed PIO-GCN Top-K RTS-79 experiment.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--normalizer", required=True)
    parser.add_argument("--baseline-summary-dir")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed-start", type=int, default=20260722)
    parser.add_argument("--num-seeds", type=int, default=10)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100])
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--run-full-truth", action="store_true")
    parser.add_argument("--max-paths-for-smoke-test", type=int)
    parser.add_argument("--measured-state-json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_small_experiment(
        SmallExperimentConfig(
            model=args.model,
            normalizer=args.normalizer,
            baseline_summary_dir=args.baseline_summary_dir,
            output_dir=args.output_dir,
            seed_start=args.seed_start,
            num_seeds=args.num_seeds,
            top_k=tuple(args.top_k),
            beta=args.beta,
            security_limit=args.security_limit,
            run_full_truth=args.run_full_truth,
            max_paths_for_smoke_test=args.max_paths_for_smoke_test,
            measured_state_json=args.measured_state_json,
        )
    )


if __name__ == "__main__":
    main()
