from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TRUTH_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
)
DEFAULT_SCORE_TABLE = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_paper_aligned_training_scaleup"
    / "s0_bottleneck_diagnostics"
    / "s0_bottleneck_full_score_table_local_only.csv"
)

FIXED_BUDGETS = (100, 200, 500, 1000, 1500, 2000, 2116, 2500, 3000, 3256, 4000, 5000, 10000)
RECALL_TARGETS = (0.90, 0.95, 0.99, 1.00)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit the IEEE118 N-1 gate and residual ordered N-2 universe.")
    parser.add_argument(
        "--fulltruth-csv",
        type=Path,
        default=DEFAULT_TRUTH_DIR / "ieee118_fulltruth_summary.csv",
    )
    parser.add_argument(
        "--first-step-summary-csv",
        type=Path,
        default=None,
        help="Defaults to ieee118_first_step_summary.csv beside --fulltruth-csv.",
    )
    parser.add_argument(
        "--score-table-csv",
        type=Path,
        default=DEFAULT_SCORE_TABLE,
        help="Optional existing score table used for diagnostic N-1-gated rankings.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_n1_residual_audit",
    )
    return parser.parse_args(argv)


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. This audit does not regenerate full-truth data.")


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def scenario_key_columns(frame: pd.DataFrame) -> list[str]:
    columns = [name for name in ("scenario_id", "seed") if name in frame.columns]
    if not columns:
        raise ValueError("Input must contain scenario_id and/or seed so N-1 results can be matched safely.")
    return columns


def load_valid_truth(path: Path) -> pd.DataFrame:
    require_file(path, "IEEE118 full-truth CSV")
    truth = pd.read_csv(path)
    required = {"path", "first_line", "second_line", "critical", "critical_mechanism"}
    missing = sorted(required - set(truth.columns))
    if missing:
        raise ValueError(f"Full-truth CSV missing required columns: {missing}")
    scenario_key_columns(truth)
    if "valid_ordered_n2" in truth.columns:
        truth = truth.loc[coerce_bool(truth["valid_ordered_n2"])].copy()
    if "first_step_critical" in truth.columns:
        truth = truth.loc[~coerce_bool(truth["first_step_critical"])].copy()
    if truth.empty:
        raise ValueError("Full-truth CSV contains no valid ordered N-2 rows after early-stop filtering.")
    truth["critical"] = coerce_bool(truth["critical"])
    mechanism = truth["critical_mechanism"].fillna("").astype(str)
    truth["relay_cascade"] = mechanism.eq("relay_cascade")
    truth["island_only"] = mechanism.eq("island_only")
    truth["total_load_shed_mw"] = pd.to_numeric(
        truth.get("total_load_shed_mw", pd.Series(0.0, index=truth.index)),
        errors="coerce",
    ).fillna(0.0)
    return truth.reset_index(drop=True)


def load_first_step_summary(path: Path) -> pd.DataFrame:
    require_file(path, "IEEE118 first-step summary CSV")
    first = pd.read_csv(path)
    required = {"first_line", "first_step_critical"}
    missing = sorted(required - set(first.columns))
    if missing:
        raise ValueError(f"First-step summary CSV missing required columns: {missing}")
    scenario_key_columns(first)
    first["first_step_critical"] = coerce_bool(first["first_step_critical"])
    first["first_step_total_load_shed_mw"] = pd.to_numeric(
        first.get("first_step_total_load_shed_mw", pd.Series(0.0, index=first.index)),
        errors="coerce",
    ).fillna(0.0)
    return first


def annotate_n1_residual(truth: pd.DataFrame, first: pd.DataFrame) -> pd.DataFrame:
    truth_keys = scenario_key_columns(truth)
    first_keys = scenario_key_columns(first)
    keys = [name for name in truth_keys if name in first_keys]
    if not keys:
        raise ValueError("Full-truth and first-step summary have no common scenario key.")
    n1 = first.loc[first["first_step_critical"], keys + ["first_line"]].drop_duplicates()
    n1 = n1.rename(columns={"first_line": "second_line"}).assign(n1_second=True)
    annotated = truth.merge(n1, on=keys + ["second_line"], how="left")
    annotated["n1_second"] = annotated["n1_second"].notna()
    annotated["residual_ordered_n2"] = ~annotated["n1_second"]
    return annotated


def build_n1_line_table(first: pd.DataFrame, annotated: pd.DataFrame) -> pd.DataFrame:
    keys = [name for name in scenario_key_columns(first) if name in annotated.columns]
    n1 = first.loc[first["first_step_critical"]].copy()
    grouped = (
        annotated.loc[annotated["n1_second"]]
        .groupby(keys + ["second_line"], as_index=False)
        .agg(
            tier_a_paths=("path", "size"),
            tier_a_critical=("critical", "sum"),
            tier_a_relay_cascade=("relay_cascade", "sum"),
            tier_a_island_only=("island_only", "sum"),
        )
        .rename(columns={"second_line": "first_line"})
    )
    out = n1.merge(grouped, on=keys + ["first_line"], how="left")
    for name in ("tier_a_paths", "tier_a_critical", "tier_a_relay_cascade", "tier_a_island_only"):
        out[name] = pd.to_numeric(out[name], errors="coerce").fillna(0).astype(int)
    out["tier_a_precision"] = out["tier_a_critical"] / out["tier_a_paths"].clip(lower=1)
    keep = keys + [
        "first_line",
        "first_step_total_load_shed_mw",
        "tier_a_paths",
        "tier_a_critical",
        "tier_a_precision",
        "tier_a_relay_cascade",
        "tier_a_island_only",
    ]
    return out[keep].sort_values(keys + ["first_line"]).reset_index(drop=True)


def build_residual_first_line_table(annotated: pd.DataFrame) -> pd.DataFrame:
    keys = scenario_key_columns(annotated)
    residual = annotated.loc[annotated["residual_ordered_n2"]]
    out = (
        residual.groupby(keys + ["first_line"], as_index=False)
        .agg(
            residual_paths=("path", "size"),
            residual_critical=("critical", "sum"),
            residual_relay_cascade=("relay_cascade", "sum"),
            residual_island_only=("island_only", "sum"),
            residual_load_shed_mw=("total_load_shed_mw", "sum"),
        )
        .sort_values(keys + ["first_line"])
        .reset_index(drop=True)
    )
    out["residual_reachable"] = out["residual_critical"] > 0
    return out


def budget_values(total_paths: int) -> list[int]:
    values = {min(int(value), total_paths) for value in FIXED_BUDGETS if value > 0}
    values.update(
        {
            max(1, int(round(total_paths * ratio)))
            for ratio in (0.005, 0.01, 0.02, 0.05, 0.065, 0.10, 0.15, 0.20)
        }
    )
    values.add(total_paths)
    return sorted(value for value in values if value <= total_paths)


def rank_with_n1_gate(score: pd.DataFrame, n1_second: pd.Series, score_column: str) -> pd.DataFrame:
    if score_column not in score:
        raise ValueError(f"Score table missing ranking column: {score_column}")
    ranked = score.copy()
    ranked["n1_second"] = n1_second.to_numpy(dtype=bool)
    ranked[score_column] = pd.to_numeric(ranked[score_column], errors="coerce").fillna(-np.inf)
    return ranked.sort_values(
        ["n1_second", score_column, "path"],
        ascending=[False, False, True],
    ).reset_index(drop=True)


def evaluate_ranking(method: str, ranked: pd.DataFrame, *, universe: str = "full") -> tuple[pd.DataFrame, dict[str, Any]]:
    total_critical = int(ranked["critical"].sum())
    total_relay = int(ranked["relay_cascade"].sum())
    total_island = int(ranked["island_only"].sum())
    rows: list[dict[str, Any]] = []
    for k in budget_values(len(ranked)):
        top = ranked.head(k)
        critical_hits = int(top["critical"].sum())
        relay_hits = int(top["relay_cascade"].sum())
        island_hits = int(top["island_only"].sum())
        rows.append(
            {
                "method": method,
                "universe": universe,
                "K": k,
                "search_budget_ratio": k / max(len(ranked), 1),
                "critical_hit_count": critical_hits,
                "recall_critical": critical_hits / max(total_critical, 1),
                "precision_at_k": critical_hits / max(k, 1),
                "relay_cascade_hit_count": relay_hits,
                "recall_relay_cascade": relay_hits / max(total_relay, 1),
                "island_only_hit_count": island_hits,
                "recall_island_only": island_hits / max(total_island, 1),
                "captured_load_shed_mw": float(top["total_load_shed_mw"].sum()),
            }
        )
    critical_positions = np.flatnonzero(ranked["critical"].to_numpy(dtype=bool)) + 1
    thresholds: dict[str, Any] = {
        "method": method,
        "universe": universe,
        "total_paths": int(len(ranked)),
        "total_critical": total_critical,
    }
    for target in RECALL_TARGETS:
        needed = int(math.ceil(total_critical * target))
        label = f"K{int(round(target * 100))}"
        thresholds[label] = int(critical_positions[needed - 1]) if needed and len(critical_positions) >= needed else None
    return pd.DataFrame(rows), thresholds


def load_score_table(path: Path, annotated: pd.DataFrame) -> pd.DataFrame:
    require_file(path, "diagnostic score table CSV")
    score = pd.read_csv(path)
    if "path" not in score:
        raise ValueError("Score table CSV must contain path.")
    truth_columns = [
        "path",
        "critical",
        "relay_cascade",
        "island_only",
        "total_load_shed_mw",
        "n1_second",
        "residual_ordered_n2",
    ]
    score = score.drop(columns=[name for name in truth_columns[1:] if name in score], errors="ignore")
    score = score.merge(annotated[truth_columns], on="path", how="inner", validate="one_to_one")
    if len(score) != len(annotated):
        raise ValueError(f"Score table covers {len(score)} paths but valid full-truth contains {len(annotated)} paths.")
    return score


def evaluate_diagnostic_scores(score: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    summaries: list[pd.DataFrame] = []
    thresholds: list[dict[str, Any]] = []
    for score_column, suffix in (
        ("p_shed_second", "second_only"),
        ("path_product_score", "path_prob"),
    ):
        if score_column not in score:
            continue
        plain = score.sort_values([score_column, "path"], ascending=[False, True]).reset_index(drop=True)
        rows, threshold = evaluate_ranking(suffix, plain)
        summaries.append(rows)
        thresholds.append(threshold)
        gated = rank_with_n1_gate(score, score["n1_second"], score_column)
        rows, threshold = evaluate_ranking(f"n1_gate_plus_{suffix}", gated)
        summaries.append(rows)
        thresholds.append(threshold)
        residual = plain.loc[plain["residual_ordered_n2"]].reset_index(drop=True)
        rows, threshold = evaluate_ranking(f"residual_{suffix}", residual, universe="residual")
        summaries.append(rows)
        thresholds.append(threshold)
    return (pd.concat(summaries, ignore_index=True) if summaries else pd.DataFrame()), thresholds


def compact_count(frame: pd.DataFrame, column: str) -> int:
    return int(frame[column].sum()) if column in frame else 0


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    first_path = args.first_step_summary_csv or args.fulltruth_csv.with_name("ieee118_first_step_summary.csv")
    truth = load_valid_truth(args.fulltruth_csv)
    first = load_first_step_summary(first_path)
    annotated = annotate_n1_residual(truth, first)
    n1_lines = build_n1_line_table(first, annotated)
    residual_first = build_residual_first_line_table(annotated)
    tier_a = annotated.loc[annotated["n1_second"]]
    residual = annotated.loc[annotated["residual_ordered_n2"]]

    summary: dict[str, Any] = {
        "status": "complete",
        "fulltruth_csv": str(args.fulltruth_csv),
        "first_step_summary_csv": str(first_path),
        "num_scenarios": int(annotated[scenario_key_columns(annotated)].drop_duplicates().shape[0]),
        "num_valid_ordered_n2_paths": int(len(annotated)),
        "num_critical_paths": compact_count(annotated, "critical"),
        "num_relay_cascade_paths": compact_count(annotated, "relay_cascade"),
        "num_island_only_paths": compact_count(annotated, "island_only"),
        "num_n1_critical_lines": int(len(n1_lines)),
        "n1_prescreen_evaluations_per_scenario": int(first.groupby(scenario_key_columns(first)).size().median()),
        "tier_a_paths": int(len(tier_a)),
        "tier_a_critical_paths": compact_count(tier_a, "critical"),
        "tier_a_precision": float(tier_a["critical"].mean()) if len(tier_a) else 0.0,
        "residual_paths": int(len(residual)),
        "residual_critical_paths": compact_count(residual, "critical"),
        "residual_critical_ratio": float(residual["critical"].mean()) if len(residual) else 0.0,
        "residual_relay_cascade_paths": compact_count(residual, "relay_cascade"),
        "residual_island_only_paths": compact_count(residual, "island_only"),
        "num_residual_reachable_first_lines": int(residual_first["residual_reachable"].sum()),
        "num_residual_nonreachable_first_lines": int((~residual_first["residual_reachable"]).sum()),
        "definition": {
            "tier_a": "valid ordered N-2 paths whose second_line is N-1 critical in the same S0 scenario",
            "residual": "valid ordered N-2 paths whose second_line is not N-1 critical in the same S0 scenario",
            "critical_unchanged": True,
        },
    }

    search_summary = pd.DataFrame()
    thresholds: list[dict[str, Any]] = []
    if args.score_table_csv is not None and args.score_table_csv.exists():
        score = load_score_table(args.score_table_csv, annotated)
        search_summary, thresholds = evaluate_diagnostic_scores(score)
        summary["score_table_csv"] = str(args.score_table_csv)
        summary["diagnostic_ranking_thresholds"] = thresholds
    else:
        summary["score_table_csv"] = None
        summary["score_table_note"] = "No score table was supplied; structural N-1/residual audit completed without rankings."

    n1_lines.to_csv(args.output_dir / "ieee118_n1_critical_lines.csv", index=False, encoding="utf-8-sig")
    residual_first.to_csv(args.output_dir / "ieee118_residual_first_line_summary.csv", index=False, encoding="utf-8-sig")
    if not search_summary.empty:
        search_summary.to_csv(args.output_dir / "ieee118_n1_residual_search_summary.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_n1_residual_audit_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    readme = [
        "# IEEE118 N-1 Gate and Residual N-2 Audit",
        "",
        "This audit does not change the original full-truth labels. It separates N-1-known second-line risk from residual N-2 interaction risk.",
        "",
        f"- Valid ordered N-2 paths: {summary['num_valid_ordered_n2_paths']}",
        f"- Critical paths: {summary['num_critical_paths']}",
        f"- N-1 critical lines: {summary['num_n1_critical_lines']}",
        f"- Tier-A critical paths: {summary['tier_a_critical_paths']} / {summary['tier_a_paths']}",
        f"- Residual critical paths: {summary['residual_critical_paths']} / {summary['residual_paths']}",
        f"- Residual reachable first lines: {summary['num_residual_reachable_first_lines']}",
        "",
        "N-1 prescreen evaluations and ordered N-2 candidate evaluations must be reported separately.",
    ]
    (args.output_dir / "ieee118_n1_residual_readme.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    args = parse_args()
    print(json.dumps(analyze(args), indent=2))


if __name__ == "__main__":
    main()
