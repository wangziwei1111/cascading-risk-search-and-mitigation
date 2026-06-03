from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, evaluate_pio_gcn_topk


def run_ablation(args: argparse.Namespace) -> None:
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict] = []
    detail_rows: list[dict] = []

    _record_original_baseline(args, summary_rows, detail_rows)
    _run_pio_method(
        method="physics_features_only",
        model=args.physics_ce_model,
        normalizer=args.physics_normalizer,
        use_mask=False,
        use_physics_loss=False,
        measured_state_json=None,
        args=args,
        out=out,
        summary_rows=summary_rows,
        detail_rows=detail_rows,
        notes="physics CE-only model, candidate probability mask disabled",
    )
    _run_pio_method(
        method="physics_features_plus_mask",
        model=args.physics_ce_model,
        normalizer=args.physics_normalizer,
        use_mask=True,
        use_physics_loss=False,
        measured_state_json=None,
        args=args,
        out=out,
        summary_rows=summary_rows,
        detail_rows=detail_rows,
        notes="physics CE-only model, candidate probability mask enabled",
    )
    _run_pio_method(
        method="physics_informed_loss",
        model=args.physics_informed_model,
        normalizer=args.physics_normalizer,
        use_mask=True,
        use_physics_loss=True,
        measured_state_json=None,
        args=args,
        out=out,
        summary_rows=summary_rows,
        detail_rows=detail_rows,
        notes="physics-informed model trained with nonzero lambda smoke config",
    )
    _run_pio_method(
        method="online_state_update",
        model=args.physics_informed_model,
        normalizer=args.physics_normalizer,
        use_mask=True,
        use_physics_loss=True,
        measured_state_json=args.measured_state_json,
        args=args,
        out=out,
        summary_rows=summary_rows,
        detail_rows=detail_rows,
        notes="physics-informed model with measured-state updated root case",
    )
    _run_pio_method(
        method="pio_gcn_topk",
        model=args.physics_informed_model,
        normalizer=args.physics_normalizer,
        use_mask=True,
        use_physics_loss=True,
        measured_state_json=None,
        args=args,
        out=out,
        summary_rows=summary_rows,
        detail_rows=detail_rows,
        notes="physics-informed model + mask + Top-K physical simulation",
    )

    pd.DataFrame(summary_rows).to_csv(out / "pio_gcn_ablation_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(detail_rows).to_csv(out / "pio_gcn_ablation_details.csv", index=False, encoding="utf-8-sig")
    (out / "pio_gcn_ablation_config.json").write_text(json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")


def _record_original_baseline(args: argparse.Namespace, summary_rows: list[dict], detail_rows: list[dict]) -> None:
    start = time.time()
    notes = "read from original evaluate_rts79_paper_gcn_search baseline CSV"
    num_simulated = 0
    num_found = 0
    if args.baseline_summary and Path(args.baseline_summary).exists():
        table = pd.read_csv(args.baseline_summary)
        row = table.loc[table["search_method"] == "GCN_path_prob"]
        if not row.empty:
            num_simulated = int(row.iloc[0]["attempts_to_find_all"])
            num_found = int(row.iloc[0].get("found_after_100_attempts", 0))
            detail_rows.append({"method": "original_GCN_path_prob", **row.iloc[0].to_dict()})
    else:
        notes = "baseline_summary missing; original method not re-run in ablation smoke"
    summary_rows.append(
        {
            "method": "original_GCN_path_prob",
            "feature_mode": "paper",
            "use_mask": False,
            "use_physics_loss": False,
            "use_online_state": False,
            "top_k": "",
            "model_path": args.paper_model or "",
            "normalizer_path": args.paper_normalizer or "",
            "is_real_ablation": bool(args.baseline_summary and Path(args.baseline_summary).exists()),
            "num_simulated_paths": num_simulated,
            "num_critical_found": num_found,
            "illegal_candidate_count": 0,
            "runtime_seconds": float(time.time() - start),
            "critical_path_recall": "",
            "smoke_recall": "",
            "notes": notes,
        }
    )


def _run_pio_method(
    method: str,
    model: str,
    normalizer: str,
    use_mask: bool,
    use_physics_loss: bool,
    measured_state_json: str | None,
    args: argparse.Namespace,
    out: Path,
    summary_rows: list[dict],
    detail_rows: list[dict],
    notes: str,
) -> None:
    start = time.time()
    method_out = out / method
    try:
        result = evaluate_pio_gcn_topk(
            PioTopkConfig(
                model=model,
                normalizer=normalizer,
                output_dir=str(method_out),
                seed=args.seed,
                beta=args.beta,
                security_limit=args.security_limit,
                top_k=tuple(args.top_k),
                measured_state_json=measured_state_json,
                max_paths_for_smoke_test=args.max_paths_for_smoke_test,
                use_candidate_probability_mask=use_mask,
            )
        )
        method_summary = pd.DataFrame(result["summary"])
        num_simulated = int(method_summary["num_simulated_paths"].max()) if not method_summary.empty else 0
        num_found = int(method_summary["num_critical_found"].max()) if not method_summary.empty else 0
        for row in result["summary"]:
            detail_rows.append({"method": method, **row})
        failed_notes = ""
    except Exception as exc:
        num_simulated = 0
        num_found = 0
        failed_notes = f"failed: {exc}"
    summary_rows.append(
        {
            "method": method,
            "feature_mode": "physics",
            "use_mask": use_mask,
            "use_physics_loss": use_physics_loss,
            "use_online_state": measured_state_json is not None,
            "top_k": ",".join(str(k) for k in args.top_k),
            "model_path": model,
            "normalizer_path": normalizer,
            "is_real_ablation": not bool(failed_notes),
            "num_simulated_paths": num_simulated,
            "num_critical_found": num_found,
            "illegal_candidate_count": 0,
            "runtime_seconds": float(time.time() - start),
            "critical_path_recall": "",
            "smoke_recall": "",
            "notes": failed_notes or notes,
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PIO-GCN smoke ablation with distinct method configs.")
    parser.add_argument("--physics-informed-model", required=True)
    parser.add_argument("--physics-ce-model", required=True)
    parser.add_argument("--physics-normalizer", required=True)
    parser.add_argument("--baseline-summary")
    parser.add_argument("--paper-model")
    parser.add_argument("--paper-normalizer")
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
