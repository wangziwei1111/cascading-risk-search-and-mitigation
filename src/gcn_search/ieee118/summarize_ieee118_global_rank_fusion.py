from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
PAIR_ROOT = ROOT / "results" / "gcn_search" / "ieee118_pair_interaction_gcn"
GROUPWISE_ROOT = ROOT / "results" / "gcn_search" / "ieee118_groupwise_listwise_gcn"
DEFAULT_OUTPUT = (
    ROOT / "results" / "gcn_search" / "ieee118_global_rank_fusion" / "compact"
)


def _bool_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.fillna("").astype(str).str.strip().str.lower().isin(
        {"1", "true", "yes"}
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize development and prospective global-RRF evidence."
    )
    parser.add_argument("--pair-root", type=Path, default=PAIR_ROOT)
    parser.add_argument("--groupwise-root", type=Path, default=GROUPWISE_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def summarize_query_table(table: pd.DataFrame) -> dict[str, Any]:
    required = {
        "search_stage",
        "critical",
        "relay_cascade",
        "total_load_shed_mw",
        "error",
    }
    missing = sorted(required - set(table))
    if missing:
        raise ValueError(f"Prospective query log is missing columns: {missing}")
    fallback = table[table["search_stage"].astype(str).str.contains("fallback")]
    errors = table["error"].fillna("").astype(str).str.len().gt(0)
    return {
        "num_queries": int(len(table)),
        "critical": int(_bool_series(table["critical"]).sum()),
        "relay": int(_bool_series(table["relay_cascade"]).sum()),
        "load_shed_mw": float(table["total_load_shed_mw"].sum()),
        "fallback_queries": int(len(fallback)),
        "fallback_critical": int(_bool_series(fallback["critical"]).sum()),
        "fallback_relay": int(_bool_series(fallback["relay_cascade"]).sum()),
        "fallback_load_shed_mw": float(fallback["total_load_shed_mw"].sum()),
        "errors": int(errors.sum()),
    }


def _read_run(path: Path) -> dict[str, Any]:
    query_path = path / "ieee118_prospective_oracle_queries.csv"
    first_path = path / "ieee118_prospective_oracle_first_steps.csv"
    if not query_path.exists() or not first_path.exists():
        raise FileNotFoundError(f"Missing local global-rank-fusion run: {path}")
    metrics = summarize_query_table(pd.read_csv(query_path))
    metrics["n1_state_constructions"] = int(len(pd.read_csv(first_path)))
    return metrics


def _row(seed: int, method: str, path: Path, phase: str) -> dict[str, Any]:
    return {"phase": phase, "seed": int(seed), "method": method, **_read_run(path)}


def run(args: argparse.Namespace) -> dict[str, Any]:
    development: list[dict[str, Any]] = []
    for seed in range(20261201, 20261206):
        development.append(
            _row(
                seed,
                "frozen_gcn",
                args.groupwise_root / f"reserve500_dense_seed_{seed}",
                "development",
            )
        )
        development.append(
            _row(
                seed,
                "pair_relation",
                args.pair_root / f"dev_relation_seed_{seed}",
                "development",
            )
        )
        for tag in ("070", "085"):
            development.append(
                _row(
                    seed,
                    f"local_rrf_{tag}",
                    args.pair_root / f"dev_rrf_w{tag}_seed_{seed}",
                    "development",
                )
            )
        for tag in ("050", "070", "085"):
            development.append(
                _row(
                    seed,
                    f"global_rrf_{tag}",
                    args.pair_root / f"dev_global_rrf_w{tag}_seed_{seed}",
                    "development",
                )
            )
    development_table = pd.DataFrame(development)
    baseline = development_table.loc[
        development_table["method"].eq("frozen_gcn"),
        ["seed", "fallback_critical"],
    ].set_index("seed")["fallback_critical"]
    aggregate_rows: list[dict[str, Any]] = []
    for method, group in development_table.groupby("method", sort=True):
        deltas = group.set_index("seed")["fallback_critical"] - baseline
        aggregate_rows.append(
            {
                "method": method,
                "fallback_critical": int(group["fallback_critical"].sum()),
                "fallback_relay": int(group["fallback_relay"].sum()),
                "fallback_load_shed_mw": float(group["fallback_load_shed_mw"].sum()),
                "num_seeds_below_baseline": int((deltas < 0).sum()),
                "minimum_critical_delta": int(deltas.min()),
            }
        )
    aggregate = pd.DataFrame(aggregate_rows)
    eligible = aggregate.loc[aggregate["num_seeds_below_baseline"].eq(0)]
    selected = str(
        eligible.sort_values(
            ["fallback_critical", "fallback_relay", "fallback_load_shed_mw"],
            ascending=False,
        ).iloc[0]["method"]
    )
    if selected != "global_rrf_070":
        raise ValueError(f"Frozen development rule selected unexpected method: {selected}")

    prospective: list[dict[str, Any]] = []
    for seed in range(20261211, 20261216):
        for method, name in (
            ("frozen_gcn", f"prospective_baseline_seed_{seed}"),
            ("pair_relation", f"prospective_relation_seed_{seed}"),
            ("global_rrf_070", f"prospective_global_rrf_w070_seed_{seed}"),
        ):
            prospective.append(
                _row(seed, method, args.pair_root / name, "prospective")
            )
    prospective_table = pd.DataFrame(prospective)
    prospective_aggregate = prospective_table.groupby("method", sort=True)[
        [
            "critical",
            "relay",
            "load_shed_mw",
            "fallback_critical",
            "fallback_relay",
            "fallback_load_shed_mw",
            "errors",
            "n1_state_constructions",
        ]
    ].sum()
    base = prospective_aggregate.loc["frozen_gcn"]
    chosen = prospective_aggregate.loc[selected]
    per_seed = prospective_table.pivot(
        index="seed", columns="method", values="fallback_critical"
    )
    summary = {
        "status": "complete",
        "gcn_core_class": "PaperStyleRts79Gcn",
        "gcn_core_modified": False,
        "additional_n2_training_labels": 0,
        "selection_phase": "development seeds 20261201-20261205",
        "selection_rule": (
            "Maximize aggregate fallback critical hits subject to no development "
            "seed falling below frozen GCN; tie-break by relay hits and shed."
        ),
        "selected_method": selected,
        "selected_pair_weight": 0.70,
        "prospective_seeds": list(range(20261211, 20261216)),
        "prospective_used_for_selection": False,
        "prospective_delta_vs_frozen_gcn": {
            "critical": int(chosen["critical"] - base["critical"]),
            "relay": int(chosen["relay"] - base["relay"]),
            "load_shed_mw": float(chosen["load_shed_mw"] - base["load_shed_mw"]),
            "fallback_critical": int(
                chosen["fallback_critical"] - base["fallback_critical"]
            ),
            "fallback_relay": int(chosen["fallback_relay"] - base["fallback_relay"]),
            "num_seeds_below_baseline": int(
                (per_seed[selected] < per_seed["frozen_gcn"]).sum()
            ),
        },
        "prospective_errors": int(prospective_aggregate["errors"].sum()),
        "claim_boundary": (
            "Validated on five untouched synthetic load scenarios; this is not "
            "utility-grid deployment evidence or a worst-case guarantee."
        ),
        "rejected_methods": {
            "local_rrf": "Destroyed cross-S1 score comparability and regressed all development seeds.",
            "equal_weight_global_rrf": "Valid but lower aggregate development critical hits than weight 0.70.",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    development_table.to_csv(
        args.output_dir / "ieee118_global_rank_fusion_development.csv", index=False
    )
    aggregate.to_csv(
        args.output_dir / "ieee118_global_rank_fusion_development_aggregate.csv",
        index=False,
    )
    prospective_table.to_csv(
        args.output_dir / "ieee118_global_rank_fusion_prospective.csv", index=False
    )
    (args.output_dir / "ieee118_global_rank_fusion_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
