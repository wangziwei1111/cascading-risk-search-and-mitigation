from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ROOT = ROOT / "results" / "gcn_search" / "ieee118_uncertainty_global_fusion"
DEFAULT_OUTPUT = DEFAULT_ROOT / "compact"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize uncertainty-aware global-RRF ablations."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    return series.fillna("").astype(str).str.lower().isin({"1", "true", "yes"})


def _run(path: Path) -> dict[str, float | int]:
    query = path / "ieee118_prospective_oracle_queries.csv"
    if not query.exists():
        raise FileNotFoundError(f"Missing local uncertainty-fusion query log: {query}")
    table = pd.read_csv(query)
    fallback = table[table["search_stage"].astype(str).str.contains("fallback")]
    errors = table["error"].fillna("").astype(str).str.len().gt(0)
    return {
        "critical": int(_bool(table["critical"]).sum()),
        "relay": int(_bool(table["relay_cascade"]).sum()),
        "load_shed_mw": float(table["total_load_shed_mw"].sum()),
        "fallback_critical": int(_bool(fallback["critical"]).sum()),
        "fallback_relay": int(_bool(fallback["relay_cascade"]).sum()),
        "fallback_load_shed_mw": float(fallback["total_load_shed_mw"].sum()),
        "fallback_queries": int(len(fallback)),
        "errors": int(errors.sum()),
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    development: list[dict[str, object]] = []
    for seed in range(20261216, 20261221):
        methods = {
            "global_rrf_070": f"baseline_global070_seed_{seed}",
            "uncertainty_010": f"candidate_uncertainty_seed_{seed}",
            "uncertainty_005": f"candidate_u005_seed_{seed}",
            "uncertainty_002": f"candidate_u002_seed_{seed}",
        }
        for method, name in methods.items():
            development.append(
                {"phase": "development", "seed": seed, "method": method, **_run(args.root / name)}
            )
    development_table = pd.DataFrame(development)
    prospective: list[dict[str, object]] = []
    for seed in range(20261221, 20261226):
        for method, name in {
            "global_rrf_070": f"baseline_global070_seed_{seed}",
            "uncertainty_010": f"candidate_uncertainty_seed_{seed}",
        }.items():
            prospective.append(
                {"phase": "prospective", "seed": seed, "method": method, **_run(args.root / name)}
            )
    prospective_table = pd.DataFrame(prospective)
    development_aggregate = development_table.groupby("method", sort=True)[
        ["critical", "relay", "load_shed_mw", "fallback_critical", "fallback_relay", "fallback_load_shed_mw", "errors"]
    ].sum().reset_index()
    prospective_aggregate = prospective_table.groupby("method", sort=True)[
        ["critical", "relay", "load_shed_mw", "fallback_critical", "fallback_relay", "fallback_load_shed_mw", "errors"]
    ].sum().reset_index()
    summary = {
        "status": "complete",
        "gcn_core_class": "PaperStyleRts79Gcn",
        "gcn_core_modified": False,
        "main_method_unchanged": "global_rrf_070",
        "uncertainty_method": "global_rrf_uncertainty",
        "development_seeds": list(range(20261216, 20261221)),
        "prospective_seeds": list(range(20261221, 20261226)),
        "uncertainty_weight": 0.10,
        "development_aggregate": development_aggregate.to_dict(orient="records"),
        "prospective_aggregate": prospective_aggregate.to_dict(orient="records"),
        "prospective_delta_uncertainty_vs_main": {
            "critical": int(
                prospective_aggregate.loc[prospective_aggregate.method.eq("uncertainty_010"), "critical"].iloc[0]
                - prospective_aggregate.loc[prospective_aggregate.method.eq("global_rrf_070"), "critical"].iloc[0]
            ),
            "relay": int(
                prospective_aggregate.loc[prospective_aggregate.method.eq("uncertainty_010"), "relay"].iloc[0]
                - prospective_aggregate.loc[prospective_aggregate.method.eq("global_rrf_070"), "relay"].iloc[0]
            ),
            "load_shed_mw": float(
                prospective_aggregate.loc[prospective_aggregate.method.eq("uncertainty_010"), "load_shed_mw"].iloc[0]
                - prospective_aggregate.loc[prospective_aggregate.method.eq("global_rrf_070"), "load_shed_mw"].iloc[0]
            ),
        },
        "decision": "retain_global_rrf_070_as_main; uncertainty_is_ablation_only",
        "reason": "Aggregate gain but seed-level regressions and no stable dominance.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    development_table.to_csv(args.output_dir / "ieee118_uncertainty_development.csv", index=False)
    development_aggregate.to_csv(args.output_dir / "ieee118_uncertainty_development_aggregate.csv", index=False)
    prospective_table.to_csv(args.output_dir / "ieee118_uncertainty_prospective.csv", index=False)
    (args.output_dir / "ieee118_uncertainty_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
