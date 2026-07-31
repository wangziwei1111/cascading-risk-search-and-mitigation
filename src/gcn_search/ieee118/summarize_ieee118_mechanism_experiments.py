from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOCAL_ROOT = (
    ROOT / "results" / "gcn_search" / "ieee118_mechanism_aware_gcn"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact IEEE118 mechanism-aware GCN experiment audits."
    )
    parser.add_argument("--local-root", type=Path, default=DEFAULT_LOCAL_ROOT)
    parser.add_argument(
        "--output-dir", type=Path, default=DEFAULT_LOCAL_ROOT / "compact"
    )
    return parser.parse_args(argv)


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing local experiment summary: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def paired_prospective_rows(
    root: Path,
    *,
    baseline_method: str,
    candidate_method: str,
    seeds: range,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for seed in seeds:
        pair: dict[str, dict[str, Any]] = {}
        for method in (baseline_method, candidate_method):
            summary = _load_summary(
                root
                / f"{method}_seed{seed}"
                / "ieee118_prospective_oracle_summary.json"
            )
            fallback = next(
                (
                    row
                    for row in summary["search_stage_metrics"]
                    if "fallback" in str(row["search_stage"])
                ),
                {},
            )
            pair[method] = {
                "critical": int(summary["num_critical_discoveries"]),
                "relay": int(summary["num_relay_cascade_discoveries"]),
                "load_shed_mw": float(summary["captured_load_shed_mw"]),
                "fallback_queries": int(fallback.get("num_queries", 0)),
                "fallback_critical": int(fallback.get("num_critical", 0)),
                "fallback_relay": int(fallback.get("num_relay_cascade", 0)),
            }
        baseline = pair[baseline_method]
        candidate = pair[candidate_method]
        rows.append(
            {
                "seed": int(seed),
                "baseline_method": baseline_method,
                "candidate_method": candidate_method,
                "fallback_queries": baseline["fallback_queries"],
                "baseline_critical": baseline["critical"],
                "candidate_critical": candidate["critical"],
                "critical_delta": candidate["critical"] - baseline["critical"],
                "baseline_relay": baseline["relay"],
                "candidate_relay": candidate["relay"],
                "relay_delta": candidate["relay"] - baseline["relay"],
                "baseline_load_shed_mw": baseline["load_shed_mw"],
                "candidate_load_shed_mw": candidate["load_shed_mw"],
                "load_shed_delta_mw": candidate["load_shed_mw"]
                - baseline["load_shed_mw"],
                "fallback_critical_delta": candidate["fallback_critical"]
                - baseline["fallback_critical"],
                "fallback_relay_delta": candidate["fallback_relay"]
                - baseline["fallback_relay"],
            }
        )
    return pd.DataFrame(rows)


def aggregate_prospective(table: pd.DataFrame) -> dict[str, Any]:
    informative = table.loc[table["fallback_queries"] > 0]
    return {
        "num_seeds": int(len(table)),
        "num_informative_fallback_seeds": int(len(informative)),
        "critical_delta": int(table["critical_delta"].sum()),
        "relay_delta": int(table["relay_delta"].sum()),
        "load_shed_delta_mw": float(table["load_shed_delta_mw"].sum()),
        "informative_critical_wins": int(
            (informative["critical_delta"] > 0).sum()
        ),
        "informative_critical_ties": int(
            (informative["critical_delta"] == 0).sum()
        ),
        "informative_critical_losses": int(
            (informative["critical_delta"] < 0).sum()
        ),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    weighted_summary = _load_summary(
        args.local_root
        / "training_full_e5"
        / "ieee118_mechanism_aware_gcn_summary.json"
    )
    pcgrad_summary = _load_summary(
        args.local_root
        / "training_pcgrad_full_e5"
        / "ieee118_mechanism_aware_gcn_summary.json"
    )
    training_rows = []
    seen = set()
    for source, summary in (
        ("weighted_sum", weighted_summary),
        ("pcgrad_primary", pcgrad_summary),
    ):
        for row in summary["results"]:
            key = str(row["objective"])
            if key in seen:
                continue
            seen.add(key)
            training_rows.append(
                {
                    "source": source,
                    "objective": key,
                    "validation_ap": row["validation_average_precision"],
                    "validation_K95": row["validation_K95"],
                    "test_ap": row["test_average_precision"],
                    "test_K95": row["test_K95"],
                    "formal_path_K90": row["search_path_prob_K90"],
                    "formal_path_K95": row["search_path_prob_K95"],
                    "formal_path_K99": row["search_path_prob_K99"],
                    "residual_second_K95": row[
                        "search_residual_second_only_K95"
                    ],
                }
            )
    training = pd.DataFrame(training_rows)
    weighted = paired_prospective_rows(
        args.local_root / "prospective",
        baseline_method="tail",
        candidate_method="mechanism",
        seeds=range(20260711, 20260716),
    )
    pcgrad = paired_prospective_rows(
        args.local_root / "prospective_pcgrad",
        baseline_method="tail",
        candidate_method="pcgrad",
        seeds=range(20260716, 20260726),
    )
    ucb = paired_prospective_rows(
        args.local_root / "prospective_ucb",
        baseline_method="mean",
        candidate_method="ucb",
        seeds=range(20260726, 20260731),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    training.to_csv(
        args.output_dir / "mechanism_training_ablation.csv", index=False
    )
    weighted.to_csv(
        args.output_dir / "weighted_sum_prospective_comparison.csv", index=False
    )
    pcgrad.to_csv(
        args.output_dir / "pcgrad_prospective_comparison.csv", index=False
    )
    ucb.to_csv(args.output_dir / "gcn_ucb_prospective_comparison.csv", index=False)
    summary = {
        "status": "complete",
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "primary_checkpoint_retained": "tail_hard_pairwise_checkpoint",
        "weighted_sum": aggregate_prospective(weighted),
        "pcgrad_primary": aggregate_prospective(pcgrad),
        "gcn_ucb": aggregate_prospective(ucb),
        "conclusion": (
            "Mechanism-aware weighted sum, primary-protected PCGrad, and GCN "
            "UCB produced mixed seed-level gains and do not replace the tail "
            "hard-pairwise GCN."
        ),
    }
    (args.output_dir / "ieee118_mechanism_experiment_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    summary = run(parse_args(argv))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
