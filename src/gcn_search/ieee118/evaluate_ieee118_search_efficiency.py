from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS, BR_X, F_BUS, PF, RATE_A, T_BUS
from pypower.idx_bus import BUS_I

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_adapter import build_case_adapter, run_sequential_outages_for_case
from generate_ieee118_ordered_n2_fulltruth import apply_ieee118_load_scenario, apply_thermal_limit_mode


FIXED_BUDGETS = [50, 100, 200, 500, 1000, 2000, 5000]
PERCENT_BUDGETS = [0.005, 0.01, 0.02, 0.05, 0.10]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate IEEE118 ordered N-2 search-efficiency rankings.")
    parser.add_argument(
        "--fulltruth-csv",
        type=Path,
        default=ROOT
        / "results"
        / "gcn_search"
        / "ieee118_flow_scaled_800_fulltruth_seed20260708"
        / "ieee118_fulltruth_summary.csv",
    )
    parser.add_argument("--gcn-predictions-csv", type=Path, default=None)
    parser.add_argument("--include-lodf", action="store_true", help="Compute the IEEE118 LODF_yP baseline.")
    parser.add_argument("--random-seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument("--limit-mode", choices=["original_rate_a", "flow_scaled"], default="flow_scaled")
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--load-scale", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--max-paths", type=int, default=None, help="Optional smoke cap on truth rows and rankings.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_gcn_smoke",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. This script reads local large artifacts and will not regenerate them automatically."
        )


def load_fulltruth(path: Path, max_paths: int | None = None) -> pd.DataFrame:
    require_file(path, "IEEE118 full-truth CSV")
    table = pd.read_csv(path)
    if max_paths is not None:
        table = table.head(max_paths).copy()
    required = {"path", "critical", "critical_mechanism", "total_load_shed_mw"}
    missing = sorted(required - set(table.columns))
    if missing:
        raise ValueError(f"Full-truth CSV missing required columns: {missing}")
    table["critical"] = coerce_bool(table["critical"])
    table["relay_cascade"] = table["critical_mechanism"].fillna("").astype(str).eq("relay_cascade")
    table["total_load_shed_mw"] = pd.to_numeric(table["total_load_shed_mw"], errors="coerce").fillna(0.0)
    return table.reset_index(drop=True)


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def budget_table(total_paths: int) -> pd.DataFrame:
    records = []
    for k in FIXED_BUDGETS:
        records.append({"budget_type": "fixed", "budget_label": str(k), "K": min(int(k), total_paths)})
    for pct in PERCENT_BUDGETS:
        k = max(1, int(round(total_paths * pct)))
        records.append({"budget_type": "percent", "budget_label": f"{pct * 100:g}%", "K": min(k, total_paths)})
    return pd.DataFrame(records).drop_duplicates(["budget_type", "budget_label", "K"]).sort_values("K")


def line_order_paths(truth: pd.DataFrame) -> list[str]:
    return truth["path"].astype(str).tolist()


def random_order_paths(paths: list[str], seed: int) -> list[str]:
    ordered = list(paths)
    rng = random.Random(seed)
    rng.shuffle(ordered)
    return ordered


def order_from_predictions(predictions_csv: Path, truth_paths: Iterable[str]) -> list[str]:
    require_file(predictions_csv, "GCN predictions CSV")
    predictions = pd.read_csv(predictions_csv)
    if not {"path", "gcn_score"}.issubset(predictions.columns):
        raise ValueError("GCN predictions CSV must contain path and gcn_score columns")
    allowed = set(truth_paths)
    predictions = predictions.loc[predictions["path"].astype(str).isin(allowed)].copy()
    predictions["gcn_score"] = pd.to_numeric(predictions["gcn_score"], errors="coerce").fillna(-np.inf)
    ranked = predictions.sort_values(["gcn_score", "path"], ascending=[False, True])["path"].astype(str).tolist()
    missing = [path for path in truth_paths if path not in set(ranked)]
    return ranked + missing


def evaluate_order(method: str, ordered_paths: list[str], truth: pd.DataFrame, budgets: pd.DataFrame) -> pd.DataFrame:
    truth_by_path = truth.set_index("path")
    total_paths = len(truth)
    total_critical = int(truth["critical"].sum())
    total_relay = int(truth["relay_cascade"].sum())
    total_load_shed = float(truth["total_load_shed_mw"].sum())
    relay_load_shed = float(truth.loc[truth["relay_cascade"], "total_load_shed_mw"].sum())
    ranked = truth_by_path.reindex(ordered_paths).dropna(subset=["critical"]).reset_index()
    records = []
    for _, budget in budgets.iterrows():
        k = int(budget["K"])
        top = ranked.head(k)
        critical_hits = int(top["critical"].sum())
        relay_hits = int(top["relay_cascade"].sum())
        captured_shed = float(top["total_load_shed_mw"].sum())
        captured_relay_shed = float(top.loc[top["relay_cascade"], "total_load_shed_mw"].sum())
        records.append(
            {
                "method": method,
                "budget_type": budget["budget_type"],
                "budget_label": budget["budget_label"],
                "K": k,
                "search_budget_ratio": k / total_paths if total_paths else 0.0,
                "critical_hit_count": critical_hits,
                "relay_cascade_hit_count": relay_hits,
                "recall_critical": critical_hits / total_critical if total_critical else 0.0,
                "recall_relay_cascade": relay_hits / total_relay if total_relay else 0.0,
                "precision_at_k": critical_hits / k if k else 0.0,
                "captured_total_load_shed_mw": captured_shed,
                "captured_total_load_shed_ratio": captured_shed / total_load_shed if total_load_shed else 0.0,
                "captured_relay_cascade_load_shed_mw": captured_relay_shed,
                "captured_relay_cascade_load_shed_ratio": captured_relay_shed / relay_load_shed if relay_load_shed else 0.0,
            }
        )
    return pd.DataFrame(records)


def summarize_random(random_rows: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "critical_hit_count",
        "relay_cascade_hit_count",
        "recall_critical",
        "recall_relay_cascade",
        "precision_at_k",
        "captured_total_load_shed_mw",
        "captured_total_load_shed_ratio",
        "captured_relay_cascade_load_shed_mw",
        "captured_relay_cascade_load_shed_ratio",
    ]
    rows = []
    group_cols = ["method", "budget_type", "budget_label", "K", "search_budget_ratio"]
    for key, group in random_rows.groupby(group_cols, sort=False):
        record = dict(zip(group_cols, key))
        for metric in metric_cols:
            values = pd.to_numeric(group[metric], errors="coerce")
            record[metric] = float(values.mean())
            record[f"{metric}_std"] = float(values.std(ddof=1)) if len(values) > 1 else 0.0
        rows.append(record)
    ordered = group_cols + metric_cols + [f"{metric}_std" for metric in metric_cols]
    return pd.DataFrame(rows, columns=ordered)


def calculate_lodf_y_p(case: dict, line_labels: tuple[str, ...], beta: float = 1.2) -> pd.DataFrame:
    branch = case["branch"]
    bus = case["bus"]
    bus_numbers = bus[:, BUS_I].astype(int).tolist()
    bus_to_position = {bus_number: pos for pos, bus_number in enumerate(bus_numbers)}
    x_matrix = build_nodal_reactance_matrix(case, bus_to_position)
    incidence = build_branch_incidence_matrix(branch, bus_to_position)
    branch_x = branch[:, BR_X].astype(float)
    flow = np.where(branch[:, BR_STATUS].astype(int) == 1, branch[:, PF].astype(float), 0.0)
    rate_a = branch[:, RATE_A].astype(float)
    status = branch[:, BR_STATUS].astype(int)
    x_pair = incidence.T @ x_matrix @ incidence
    records = []
    for k_idx, label in enumerate(line_labels):
        if status[k_idx] != 1:
            records.append({"candidate_line": label, "y_P": np.nan, "is_singular_or_islanding": False})
            continue
        denominator = 1.0 - x_pair[k_idx, k_idx] / branch_x[k_idx]
        if abs(denominator) < 1e-8:
            records.append({"candidate_line": label, "y_P": float(beta), "is_singular_or_islanding": True})
            continue
        alpha_hat = np.full(branch.shape[0], np.nan)
        for m_idx in range(branch.shape[0]):
            if status[m_idx] != 1 or m_idx == k_idx or rate_a[m_idx] <= 0:
                continue
            d_mk = (x_pair[m_idx, k_idx] / branch_x[m_idx]) / denominator
            alpha_hat[m_idx] = abs(flow[m_idx] + d_mk * flow[k_idx]) / rate_a[m_idx]
        y_p = 0.0 if np.all(np.isnan(alpha_hat)) else float(np.nanmax(alpha_hat))
        records.append({"candidate_line": label, "y_P": y_p, "is_singular_or_islanding": False})
    return pd.DataFrame(records).sort_values(["y_P", "candidate_line"], ascending=[False, True], na_position="last")


def build_branch_incidence_matrix(branch: np.ndarray, bus_to_position: dict[int, int]) -> np.ndarray:
    incidence = np.zeros((len(bus_to_position), branch.shape[0]))
    for idx, row in enumerate(branch):
        incidence[bus_to_position[int(row[F_BUS])], idx] = 1.0
        incidence[bus_to_position[int(row[T_BUS])], idx] = -1.0
    return incidence


def build_nodal_reactance_matrix(case: dict, bus_to_position: dict[int, int]) -> np.ndarray:
    branch = case["branch"]
    bus_count = len(bus_to_position)
    b_bus = np.zeros((bus_count, bus_count))
    for row in branch:
        if int(row[BR_STATUS]) != 1:
            continue
        i = bus_to_position[int(row[F_BUS])]
        j = bus_to_position[int(row[T_BUS])]
        b = 1.0 / float(row[BR_X])
        b_bus[i, i] += b
        b_bus[j, j] += b
        b_bus[i, j] -= b
        b_bus[j, i] -= b
    x_matrix = np.zeros_like(b_bus)
    active = [idx for idx in range(bus_count) if np.any(np.abs(b_bus[idx]) > 1e-12)]
    if len(active) <= 1:
        return x_matrix
    reference = active[0]
    reduced = [idx for idx in active if idx != reference]
    x_matrix[np.ix_(reduced, reduced)] = np.linalg.pinv(b_bus[np.ix_(reduced, reduced)])
    return x_matrix


def make_ieee118_lodf_order(args: argparse.Namespace, truth: pd.DataFrame) -> list[str]:
    adapter = build_case_adapter("ieee118")
    scenario_case = apply_ieee118_load_scenario(adapter.case, seed=args.seed, load_scale=args.load_scale)
    scenario_case = apply_thermal_limit_mode(
        scenario_case,
        limit_mode=args.limit_mode,
        flow_limit_scale=args.flow_limit_scale,
        min_rate_a=args.min_rate_a,
    )
    first_table = calculate_lodf_y_p(scenario_case, adapter.line_labels, beta=args.beta).dropna(subset=["y_P"])
    first_scores = {str(row["candidate_line"]): float(row["y_P"]) for _, row in first_table.iterrows()}
    first_order = first_table["candidate_line"].astype(str).tolist()
    scored_paths = []
    for first_line in first_order:
        state = run_sequential_outages_for_case(
            scenario_case,
            adapter,
            [first_line],
            beta=args.beta,
            security_limit=args.security_limit,
        )
        second_table = calculate_lodf_y_p(state["case"], adapter.line_labels, beta=args.beta).dropna(subset=["y_P"])
        for _, row in second_table.iterrows():
            second_line = str(row["candidate_line"])
            if second_line == first_line:
                continue
            path = f"{first_line}->{second_line}"
            score = float(first_scores.get(first_line, 0.0) * float(row["y_P"]))
            scored_paths.append((-score, -float(row["y_P"]), path))
    scored_paths.sort()
    truth_paths = set(truth["path"].astype(str))
    return [path for _, _, path in scored_paths if path in truth_paths]


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def evaluate(args: argparse.Namespace) -> pd.DataFrame:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    truth = load_fulltruth(args.fulltruth_csv, args.max_paths)
    budgets = budget_table(len(truth))
    paths = line_order_paths(truth)
    rows = [evaluate_order("line_order", paths, truth, budgets)]
    line_summary = rows[-1]
    line_summary.to_csv(args.output_dir / "line_order_baseline_summary.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "line_order_baseline_summary.json", line_summary.to_dict("records"))

    random_parts = []
    for seed in args.random_seeds:
        random_parts.append(evaluate_order(f"random_seed_{seed}", random_order_paths(paths, seed), truth, budgets))
    random_raw = pd.concat(random_parts, ignore_index=True)
    random_summary = summarize_random(random_raw.assign(method="random"))
    random_summary.to_csv(args.output_dir / "random_baseline_summary.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "random_baseline_summary.json", random_summary.to_dict("records"))
    rows.append(random_summary.assign(method="random"))

    lodf_status = {"status": "not_run", "reason": "Pass --include-lodf to compute IEEE118 LODF_yP."}
    if args.include_lodf:
        lodf_order = make_ieee118_lodf_order(args, truth)
        lodf_summary = evaluate_order("LODF_yP", lodf_order, truth, budgets)
        lodf_summary.to_csv(args.output_dir / "lodf_yp_baseline_summary.csv", index=False, encoding="utf-8-sig")
        write_json(args.output_dir / "lodf_yp_baseline_summary.json", lodf_summary.to_dict("records"))
        rows.append(lodf_summary)
        lodf_status = {"status": "complete", "num_ranked_paths": len(lodf_order)}
    else:
        write_json(args.output_dir / "lodf_yp_baseline_summary.json", lodf_status)

    if args.gcn_predictions_csv is not None:
        gcn_order = order_from_predictions(args.gcn_predictions_csv, paths)
        gcn_summary = evaluate_order("GCN_smoke", gcn_order, truth, budgets)
        gcn_summary.to_csv(args.output_dir / "gcn_smoke_search_summary.csv", index=False, encoding="utf-8-sig")
        write_json(args.output_dir / "gcn_smoke_search_summary.json", gcn_summary.to_dict("records"))
        rows.append(gcn_summary)

    combined = pd.concat(rows, ignore_index=True, sort=False)
    combined.to_csv(args.output_dir / "search_efficiency_summary.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / "search_efficiency_summary.json", combined.to_dict("records"))
    write_json(
        args.output_dir / "search_efficiency_config.json",
        {
            "fulltruth_csv": str(args.fulltruth_csv),
            "gcn_predictions_csv": str(args.gcn_predictions_csv) if args.gcn_predictions_csv else None,
            "total_paths": int(len(truth)),
            "critical_paths": int(truth["critical"].sum()),
            "relay_cascade_paths": int(truth["relay_cascade"].sum()),
            "budgets": budgets.to_dict("records"),
            "random_seeds": args.random_seeds,
            "lodf_yp": lodf_status,
            "notes": "Smoke-stage evaluation. Results are not final tuned IEEE118 GCN claims.",
        },
    )
    return combined


def main() -> None:
    args = parse_args()
    summary = evaluate(args)
    print(f"IEEE118 search-efficiency summary written to {args.output_dir / 'search_efficiency_summary.csv'}")
    print(summary.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
