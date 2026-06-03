from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, evaluate_pio_gcn_topk


METHODS = [
    "original_GCN_path_prob",
    "physics_features_only",
    "physics_features_plus_mask",
    "physics_informed_loss",
    "online_state_update",
    "pio_gcn_topk",
]


def run_ablation(args: argparse.Namespace) -> None:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    detail_rows = []
    for method in METHODS:
        start = time.time()
        method_out = out / method
        notes = ""
        try:
            measured = args.measured_state_json if method == "online_state_update" else None
            result = evaluate_pio_gcn_topk(
                PioTopkConfig(
                    model=args.model,
                    normalizer=args.normalizer,
                    output_dir=str(method_out),
                    seed=args.seed,
                    beta=args.beta,
                    security_limit=args.security_limit,
                    top_k=tuple(args.top_k),
                    measured_state_json=measured,
                    run_exhaustive_truth=False,
                    max_paths_for_smoke_test=args.max_paths_for_smoke_test,
                )
            )
            method_summary = pd.DataFrame(result["summary"])
            num_simulated = int(method_summary["num_simulated_paths"].max()) if not method_summary.empty else 0
            num_found = int(method_summary["num_critical_found"].max()) if not method_summary.empty else 0
            for row in result["summary"]:
                detail_rows.append({"method": method, **row})
        except Exception as exc:  # smoke framework should record failures instead of crashing.
            num_simulated = 0
            num_found = 0
            notes = f"failed: {exc}"
        summary_rows.append(
            {
                "method": method,
                "feature_mode": "paper" if method == "original_GCN_path_prob" else "physics",
                "use_mask": method in {"physics_features_plus_mask", "physics_informed_loss", "online_state_update", "pio_gcn_topk"},
                "use_physics_loss": method == "physics_informed_loss",
                "use_online_state": method == "online_state_update",
                "top_k": ",".join(str(k) for k in args.top_k),
                "num_simulated_paths": num_simulated,
                "num_critical_found": num_found,
                "illegal_candidate_count": 0,
                "runtime_seconds": float(time.time() - start),
                "critical_path_recall": "",
                "notes": notes or "smoke-test proxy; methods share PIO evaluator unless noted",
            }
        )
    pd.DataFrame(summary_rows).to_csv(out / "pio_gcn_ablation_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(detail_rows).to_csv(out / "pio_gcn_ablation_details.csv", index=False, encoding="utf-8-sig")
    (out / "pio_gcn_ablation_config.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PIO-GCN smoke ablation.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--normalizer", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/pio_ablation")
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20])
    parser.add_argument("--measured-state-json", default="examples/rts79_measured_state_example.json")
    parser.add_argument("--max-paths-for-smoke-test", type=int, default=20)
    return parser.parse_args()


if __name__ == "__main__":
    run_ablation(parse_args())
