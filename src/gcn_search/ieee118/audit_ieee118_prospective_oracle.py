from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]


def _bool_series(values: pd.Series) -> pd.Series:
    if values.dtype == bool:
        return values.fillna(False)
    return values.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_prospective_queries(
    query_table: pd.DataFrame,
    truth_table: pd.DataFrame,
) -> tuple[dict[str, Any], pd.DataFrame, pd.DataFrame]:
    required_query = {"query_rank", "path"}
    required_truth = {
        "path",
        "critical",
        "critical_mechanism",
        "total_load_shed_mw",
    }
    missing_query = sorted(required_query - set(query_table))
    missing_truth = sorted(required_truth - set(truth_table))
    if missing_query or missing_truth:
        raise ValueError(
            "Prospective audit is missing fields: "
            f"query={missing_query}, truth={missing_truth}"
        )
    queries = query_table.copy()
    truth = truth_table.copy()
    queries["path"] = queries["path"].astype(str)
    truth["path"] = truth["path"].astype(str)
    if queries["path"].duplicated().any():
        raise ValueError("Prospective query log contains duplicate paths.")
    if truth["path"].duplicated().any():
        raise ValueError("Prospective full-truth audit contains duplicate paths.")
    queries["query_rank"] = pd.to_numeric(
        queries["query_rank"], errors="raise"
    ).astype(int)
    queries = queries.sort_values("query_rank", kind="stable").reset_index(drop=True)
    expected_rank = np.arange(1, len(queries) + 1)
    if not np.array_equal(queries["query_rank"].to_numpy(), expected_rank):
        raise ValueError("Prospective query ranks must be contiguous from one.")
    unknown = sorted(set(queries["path"]) - set(truth["path"]))
    if unknown:
        raise ValueError(
            f"Prospective queries are absent from post-hoc truth: {unknown[:10]}"
        )

    truth["truth_critical"] = _bool_series(truth["critical"])
    truth["truth_relay_cascade"] = truth["critical_mechanism"].fillna("").astype(str).eq(
        "relay_cascade"
    )
    truth["truth_total_load_shed_mw"] = pd.to_numeric(
        truth["total_load_shed_mw"], errors="coerce"
    ).fillna(0.0)
    joined = queries.merge(
        truth[
            [
                "path",
                "truth_critical",
                "truth_relay_cascade",
                "truth_total_load_shed_mw",
            ]
        ],
        on="path",
        how="left",
        validate="one_to_one",
    )
    if "critical" in queries:
        observed = _bool_series(joined["critical"])
        if not np.array_equal(observed.to_numpy(), joined["truth_critical"].to_numpy()):
            mismatch = joined.loc[
                observed.ne(joined["truth_critical"]), "path"
            ].tolist()
            raise ValueError(
                "Prospective query outcomes disagree with post-hoc truth: "
                f"{mismatch[:10]}"
            )

    total_critical = int(truth["truth_critical"].sum())
    total_relay = int(truth["truth_relay_cascade"].sum())
    total_shed = float(truth["truth_total_load_shed_mw"].sum())
    queried_critical = joined["truth_critical"].astype(bool)
    queried_relay = joined["truth_relay_cascade"].astype(bool)
    queried_shed = joined["truth_total_load_shed_mw"].astype(float)
    critical_cumulative = queried_critical.cumsum()
    relay_cumulative = queried_relay.cumsum()
    shed_cumulative = queried_shed.cumsum()
    curve = pd.DataFrame(
        {
            "candidate_evaluations": expected_rank,
            "critical_paths_found": critical_cumulative,
            "relay_cascade_paths_found": relay_cumulative,
            "captured_load_shed_mw": shed_cumulative,
            "critical_recall": critical_cumulative / max(total_critical, 1),
            "relay_cascade_recall": relay_cumulative / max(total_relay, 1),
            "query_precision": critical_cumulative / expected_rank,
        }
    )
    queried_paths = set(queries["path"])
    missed = truth.loc[
        truth["truth_critical"] & ~truth["path"].isin(queried_paths)
    ].copy()
    missed = missed.sort_values(
        ["truth_total_load_shed_mw", "path"],
        ascending=[False, True],
        kind="stable",
    )
    summary = {
        "status": "complete",
        "audit_mode": "posthoc_read_only",
        "policy_query_order_modified": False,
        "num_truth_paths": int(len(truth)),
        "num_truth_critical": total_critical,
        "num_truth_relay_cascade": total_relay,
        "num_queries": int(len(queries)),
        "search_budget_ratio": float(len(queries) / max(len(truth), 1)),
        "num_queried_critical": int(queried_critical.sum()),
        "num_queried_relay_cascade": int(queried_relay.sum()),
        "critical_recall": float(queried_critical.sum() / max(total_critical, 1)),
        "relay_cascade_recall": float(queried_relay.sum() / max(total_relay, 1)),
        "query_precision": float(queried_critical.mean() if len(queries) else 0.0),
        "captured_load_shed_mw": float(queried_shed.sum()),
        "total_truth_load_shed_mw": total_shed,
        "captured_load_shed_ratio": float(queried_shed.sum() / max(total_shed, 1e-12)),
        "num_missed_critical": int(len(missed)),
    }
    return summary, curve, missed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Audit a frozen prospective IEEE118 query log against independently "
            "generated full-truth after search completion."
        )
    )
    parser.add_argument("--query-log", type=Path, required=True)
    parser.add_argument("--fulltruth-csv", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--policy-summary-json", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-missed-paths", type=int, default=100)
    return parser.parse_args(argv)


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.query_log, "prospective query log"),
        (args.fulltruth_csv, "independent full-truth CSV"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing local {label}: {path}")
    if args.max_missed_paths < 0:
        raise ValueError("--max-missed-paths must be non-negative.")
    query = pd.read_csv(args.query_log)
    truth = pd.read_csv(args.fulltruth_csv)
    if "seed" in truth:
        truth = truth.loc[
            pd.to_numeric(truth["seed"], errors="coerce").eq(int(args.seed))
        ].copy()
    if truth.empty:
        raise ValueError(f"No full-truth rows found for seed {args.seed}.")
    policy_summary = {}
    if args.policy_summary_json is not None:
        if not args.policy_summary_json.exists():
            raise FileNotFoundError(
                f"Missing prospective policy summary: {args.policy_summary_json}"
            )
        policy_summary = json.loads(
            args.policy_summary_json.read_text(encoding="utf-8")
        )
        if policy_summary.get("fulltruth_read_during_search") is not False:
            raise ValueError(
                "Policy summary does not certify fulltruth_read_during_search=false."
            )
    summary, curve, missed = audit_prospective_queries(query, truth)
    summary.update(
        {
            "seed": int(args.seed),
            "query_log_sha256": _file_sha256(args.query_log),
            "fulltruth_sha256": _file_sha256(args.fulltruth_csv),
            "policy_configuration_fingerprint": policy_summary.get(
                "configuration_fingerprint"
            ),
            "fulltruth_read_during_search": False,
            "audit_performed_after_search": True,
        }
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "ieee118_prospective_posthoc_audit_summary.json"
    curve_path = args.output_dir / "ieee118_prospective_posthoc_curve.csv"
    missed_path = args.output_dir / "ieee118_prospective_missed_critical_top.csv"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    curve.to_csv(curve_path, index=False, encoding="utf-8-sig")
    missed.head(int(args.max_missed_paths)).to_csv(
        missed_path,
        index=False,
        encoding="utf-8-sig",
    )
    (args.output_dir / "ieee118_prospective_posthoc_readme.md").write_text(
        "# IEEE118 prospective post-hoc audit\n\n"
        "This audit read independent full-truth only after the frozen query log "
        "was complete. It did not alter search order, promotion, or stopping.\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    print(json.dumps(run_audit(parse_args(argv)), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
