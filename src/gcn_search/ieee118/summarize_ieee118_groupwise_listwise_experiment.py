from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
LOCAL_ROOT = ROOT / "results" / "gcn_search" / "ieee118_groupwise_listwise_gcn"
DEFAULT_OUTPUT = LOCAL_ROOT / "compact"
DEFAULT_TAIL = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_tail_critical_gcn"
    / "tail_active_005_k95select"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize groupwise GCN experiments.")
    parser.add_argument("--local-root", type=Path, default=LOCAL_ROOT)
    parser.add_argument("--tail-baseline-dir", type=Path, default=DEFAULT_TAIL)
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(20261201, 20261206)))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _read_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing local experiment summary: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_row(method: str, row: dict[str, Any]) -> dict[str, Any]:
    keep = {
        key: value
        for key, value in row.items()
        if key.startswith("validation_")
        or key.startswith("test_")
        or key.startswith("search_")
    }
    return {"method": method, **keep}


def run(args: argparse.Namespace) -> dict[str, Any]:
    tail = _read_summary(args.tail_baseline_dir / "ieee118_tail_aware_gcn_summary.json")
    dense = _read_summary(
        args.local_root / "dense005_ablation_e5" / "ieee118_tail_aware_gcn_summary.json"
    )
    phase3 = next(row for row in dense["results"] if row["objective"] == "phase3_checkpoint")
    scattered = next(row for row in tail["results"] if row["objective"] == "hard_pairwise")
    dense_pair = next(row for row in dense["results"] if row["objective"] == "hard_pairwise")
    smooth = next(row for row in dense["results"] if row["objective"] == "groupwise_smooth_ap")
    ablation = pd.DataFrame(
        [
            _metric_row("phase3_checkpoint", phase3),
            _metric_row("scattered_hard_pairwise", scattered),
            _metric_row("dense_state_hard_pairwise_selected", dense_pair),
            _metric_row("dense_state_smooth_ap_rejected", smooth),
        ]
    )

    prospective_rows: list[dict[str, Any]] = []
    for seed in args.seeds:
        pair: dict[str, dict[str, Any]] = {}
        for model in ("old", "dense"):
            summary = _read_summary(
                args.local_root
                / f"reserve500_{model}_seed_{seed}"
                / "ieee118_prospective_oracle_summary.json"
            )
            fallback = next(
                row for row in summary["search_stage_metrics"] if "gcn" in row["search_stage"]
            )
            pair[model] = {
                "critical": int(summary["num_critical_discoveries"]),
                "relay": int(summary["num_relay_cascade_discoveries"]),
                "load_shed_mw": float(summary["captured_load_shed_mw"]),
                "fallback_queries": int(fallback["num_queries"]),
                "fallback_critical": int(fallback["num_critical"]),
                "fallback_relay": int(fallback["num_relay_cascade"]),
                "fallback_load_shed_mw": float(fallback["captured_load_shed_mw"]),
                "errors": int(summary["num_error_queries"]),
            }
        prospective_rows.append(
            {
                "seed": int(seed),
                **{f"old_{key}": value for key, value in pair["old"].items()},
                **{f"dense_{key}": value for key, value in pair["dense"].items()},
                "delta_critical": pair["dense"]["critical"] - pair["old"]["critical"],
                "delta_relay": pair["dense"]["relay"] - pair["old"]["relay"],
                "delta_load_shed_mw": pair["dense"]["load_shed_mw"] - pair["old"]["load_shed_mw"],
            }
        )
    prospective = pd.DataFrame(prospective_rows)
    old_queries = int(prospective["old_fallback_queries"].sum())
    dense_queries = int(prospective["dense_fallback_queries"].sum())
    aggregate = {
        "num_prospective_seeds": int(len(prospective)),
        "n2_budget_per_seed": 2100,
        "gcn_fallback_reserve_per_seed": 500,
        "old_fallback_queries": old_queries,
        "dense_fallback_queries": dense_queries,
        "old_fallback_critical": int(prospective["old_fallback_critical"].sum()),
        "dense_fallback_critical": int(prospective["dense_fallback_critical"].sum()),
        "old_fallback_critical_precision": float(
            prospective["old_fallback_critical"].sum() / old_queries
        ),
        "dense_fallback_critical_precision": float(
            prospective["dense_fallback_critical"].sum() / dense_queries
        ),
        "delta_critical": int(prospective["delta_critical"].sum()),
        "delta_relay": int(prospective["delta_relay"].sum()),
        "delta_load_shed_mw": float(prospective["delta_load_shed_mw"].sum()),
        "num_seeds_with_negative_critical_delta": int(
            (prospective["delta_critical"] < 0).sum()
        ),
        "errors": int(
            prospective["old_errors"].sum() + prospective["dense_errors"].sum()
        ),
    }
    summary = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "selection_rule": "Minimum validation K95; formal and prospective truth not used for selection.",
        "selected_method": "dense_state_hard_pairwise",
        "rejected_method": "dense_state_smooth_ap",
        "aggregate_prospective": aggregate,
        "claim_boundary": (
            "Prospective improvement is aggregate, not uniform: one of five seeds regressed."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ablation.to_csv(args.output_dir / "ieee118_groupwise_listwise_ablation.csv", index=False)
    prospective.to_csv(
        args.output_dir / "ieee118_groupwise_prospective_comparison.csv", index=False
    )
    (args.output_dir / "ieee118_groupwise_listwise_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
