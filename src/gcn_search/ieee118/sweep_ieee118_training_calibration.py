from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from build_ieee118_paper_gcn_training_dataset import build_dataset


ROOT = Path(__file__).resolve().parents[3]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Small calibration smoke for IEEE118 paper-aligned training labels.")
    parser.add_argument("--seeds", type=int, nargs="+", default=[20260701, 20260702, 20260708])
    parser.add_argument("--load-scales", type=float, nargs="+", default=[1.0, 1.05, 1.1])
    parser.add_argument("--flow-limit-scales", type=float, nargs="+", default=[8.0, 10.0, 12.0])
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--target-state-samples", type=int, default=20)
    parser.add_argument("--samples-per-scenario", type=int, default=6)
    parser.add_argument("--sample-seed", type=int, default=20260708)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_training",
    )
    return parser.parse_args()


def recommendation(row: dict) -> str:
    ratio = float(row["positive_label_ratio"])
    first = int(row["num_first_step_critical_lines_estimate"])
    if first > 0.25 * int(row["num_candidate_labels"]):
        return "too_many_first_step_critical"
    if ratio < 0.01:
        return "too_sparse"
    if ratio > 0.35:
        return "too_dense"
    return "candidate"


def run_sweep(args: argparse.Namespace) -> pd.DataFrame:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for load_scale in args.load_scales:
        for flow_limit_scale in args.flow_limit_scales:
            subdir = args.output_dir / f"calibration_load{load_scale:g}_flow{flow_limit_scale:g}"
            dataset_args = argparse.Namespace(
                seeds=args.seeds,
                num_load_scenarios=None,
                samples_per_scenario=args.samples_per_scenario,
                target_state_samples=args.target_state_samples,
                load_scale=load_scale,
                load_random_low=0.9,
                load_random_high=1.1,
                limit_mode="flow_scaled",
                flow_limit_scale=flow_limit_scale,
                min_rate_a=args.min_rate_a,
                beta=1.2,
                security_limit=1.0,
                first_step_critical_policy="skip",
                feature_mode="paper",
                sample_seed=args.sample_seed,
                resume=False,
                checkpoint_every=0,
                train_seeds=None,
                validation_seeds=None,
                test_seeds=[20260708],
                output_dir=subdir,
            )
            try:
                meta = build_dataset(dataset_args)
                row = {
                    "load_scale": load_scale,
                    "flow_limit_scale": flow_limit_scale,
                    "min_rate_a": args.min_rate_a,
                    "positive_label_ratio": meta["positive_label_ratio"],
                    "num_candidate_labels": meta["num_candidate_labels"],
                    "s0_positive_ratio": meta["num_first_step_critical_labels"] / max(186 * meta["num_s0_samples"], 1),
                    "s1_positive_ratio": meta["num_valid_n2_positive_labels"] / max(meta["num_candidate_labels"] - 186 * meta["num_s0_samples"], 1),
                    "num_first_step_critical_lines_estimate": meta["num_first_step_critical_labels"],
                    "mean_candidate_labels_per_state": meta["num_candidate_labels"] / max(meta["num_state_samples"], 1),
                    "relay_cascade_positive_ratio": None,
                    "error_count": 0,
                    "recommended_setting": "",
                }
            except Exception as exc:
                row = {
                    "load_scale": load_scale,
                    "flow_limit_scale": flow_limit_scale,
                    "min_rate_a": args.min_rate_a,
                    "positive_label_ratio": 0.0,
                    "num_candidate_labels": 0,
                    "s0_positive_ratio": 0.0,
                    "s1_positive_ratio": 0.0,
                    "num_first_step_critical_lines_estimate": 0,
                    "mean_candidate_labels_per_state": 0.0,
                    "relay_cascade_positive_ratio": None,
                    "error_count": 1,
                    "error": str(exc),
                    "recommended_setting": "error",
                }
            if not row["recommended_setting"]:
                row["recommended_setting"] = recommendation(row)
            rows.append(row)
    table = pd.DataFrame(rows)
    table.to_csv(args.output_dir / "ieee118_training_calibration_sweep.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_training_calibration_sweep.json").write_text(
        json.dumps(table.to_dict("records"), indent=2),
        encoding="utf-8",
    )
    return table


def main() -> None:
    args = parse_args()
    print(run_sweep(args).to_string(index=False))


if __name__ == "__main__":
    main()
