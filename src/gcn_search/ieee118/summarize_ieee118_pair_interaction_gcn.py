from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
LOCAL_ROOT = ROOT / "results" / "gcn_search" / "ieee118_pair_interaction_gcn"
DEFAULT_OUTPUT = LOCAL_ROOT / "compact"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize pair-interaction GCN evidence.")
    parser.add_argument("--local-root", type=Path, default=LOCAL_ROOT)
    parser.add_argument("--formal-run", type=Path, default=LOCAL_ROOT / "formal_e250")
    parser.add_argument("--seeds", type=int, nargs="+", default=list(range(20261206, 20261211)))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing local pair-interaction evidence: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run(args: argparse.Namespace) -> dict[str, Any]:
    formal = _read(args.formal_run / "ieee118_pair_interaction_summary.json")
    ablation = pd.DataFrame(formal["results"])
    prospective_rows: list[dict[str, Any]] = []
    for seed in args.seeds:
        pair: dict[str, dict[str, Any]] = {}
        for method in ("baseline", "relation"):
            summary = _read(
                args.local_root
                / f"prospective_{method}_seed_{seed}"
                / "ieee118_prospective_oracle_summary.json"
            )
            fallback = next(
                row for row in summary["search_stage_metrics"] if "gcn" in row["search_stage"]
            )
            pair[method] = {
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
                **{f"baseline_{key}": value for key, value in pair["baseline"].items()},
                **{f"relation_{key}": value for key, value in pair["relation"].items()},
                "delta_critical": pair["relation"]["critical"] - pair["baseline"]["critical"],
                "delta_relay": pair["relation"]["relay"] - pair["baseline"]["relay"],
                "delta_load_shed_mw": pair["relation"]["load_shed_mw"] - pair["baseline"]["load_shed_mw"],
            }
        )
    prospective = pd.DataFrame(prospective_rows)
    baseline_queries = int(prospective["baseline_fallback_queries"].sum())
    relation_queries = int(prospective["relation_fallback_queries"].sum())
    aggregate = {
        "num_prospective_seeds": int(len(prospective)),
        "prospective_seeds": [int(seed) for seed in args.seeds],
        "n2_budget_per_seed": 2100,
        "fallback_reserve_per_seed": 500,
        "baseline_fallback_queries": baseline_queries,
        "relation_fallback_queries": relation_queries,
        "baseline_fallback_critical": int(prospective["baseline_fallback_critical"].sum()),
        "relation_fallback_critical": int(prospective["relation_fallback_critical"].sum()),
        "baseline_critical_precision": float(
            prospective["baseline_fallback_critical"].sum() / baseline_queries
        ),
        "relation_critical_precision": float(
            prospective["relation_fallback_critical"].sum() / relation_queries
        ),
        "delta_critical": int(prospective["delta_critical"].sum()),
        "delta_relay": int(prospective["delta_relay"].sum()),
        "delta_load_shed_mw": float(prospective["delta_load_shed_mw"].sum()),
        "num_negative_critical_seeds": int((prospective["delta_critical"] < 0).sum()),
        "errors": int(prospective["baseline_errors"].sum() + prospective["relation_errors"].sum()),
    }
    summary = {
        "status": "complete",
        "gcn_core_class": "PaperStyleRts79Gcn",
        "gcn_core_modified": False,
        "selected_method": formal["selected_method"],
        "selection_rule": formal["selection_rule"],
        "formal_seed_used_for_selection": False,
        "simple_checkpoint_probability_ensemble": "rejected_by_validation",
        "aggregate_prospective": aggregate,
        "claim_boundary": "Aggregate improvement with one of five prospective seeds regressing.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    ablation.to_csv(args.output_dir / "ieee118_pair_interaction_ablation.csv", index=False)
    prospective.to_csv(args.output_dir / "ieee118_pair_interaction_prospective.csv", index=False)
    (args.output_dir / "ieee118_pair_interaction_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
