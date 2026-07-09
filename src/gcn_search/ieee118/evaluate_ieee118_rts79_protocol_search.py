from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS, PF


ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_adapter import build_case_adapter, run_sequential_outages_for_case
from evaluate_ieee118_search_efficiency import budget_table, calculate_lodf_y_p
from generate_ieee118_ordered_n2_fulltruth import apply_ieee118_load_scenario, apply_thermal_limit_mode
from train_ieee118_with_original_rts79_gcn import build_branch_graph_adjacency_from_endpoints, load_original_rts79_gcn_symbols
from convert_ieee118_step2_to_rts79_gcn_format import PAPER_FEATURE_NAMES, normalize_x


METHOD_GCN_PROB = "RTS79_GCN_prob_reused_on_IEEE118"
METHOD_GCN_PROB_YP = "RTS79_GCN_prob_yP_reused_on_IEEE118"
METHOD_GCN_PATH_PROB = "RTS79_GCN_path_prob_reused_on_IEEE118"
METHOD_SECOND_ONLY = "RTS79_GCN_second_only_reused_on_IEEE118"
METHOD_PFW = "PFW"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate IEEE118 using the RTS-79 original GCN search protocol.")
    parser.add_argument("--dataset-npz", type=Path, required=True)
    parser.add_argument("--path-index-csv", type=Path, required=True)
    parser.add_argument("--fulltruth-csv", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--first-step-probabilities-csv", type=Path, required=True)
    parser.add_argument("--feature-normalizer-json", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument("--load-scale", type=float, default=1.0)
    parser.add_argument("--limit-mode", choices=["original_rate_a", "flow_scaled"], default="flow_scaled")
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--random-seeds", type=int, nargs="+", default=list(range(10)))
    parser.add_argument("--topk-output-rows", type=int, default=5000)
    parser.add_argument("--method-suffix", default="", help="Suffix appended to GCN method names, e.g. _earlystop.")
    parser.add_argument("--output-prefix", default="ieee118_rts79_protocol")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_rts79_protocol_eval",
    )
    return parser.parse_args()


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}. This script reads local artifacts and will not regenerate full truth.")


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def split_labels(value: Any) -> list[str]:
    text = "" if value is None or (isinstance(value, float) and np.isnan(value)) else str(value)
    labels = []
    for token in text.replace(";", ",").split(","):
        label = token.strip().upper()
        if label:
            labels.append(label)
    return labels


def construct_full_cascade_path(row: pd.Series) -> str:
    ordered: list[str] = [str(row["first_line"]).upper(), str(row["second_line"]).upper()]
    relay_labels = split_labels(row.get("relay_trip_labels", ""))
    fallback_final = split_labels(row.get("final_outage_labels", ""))
    for label in relay_labels or fallback_final:
        if label not in ordered:
            ordered.append(label)
    return "->".join(ordered)


def load_truth(path: Path) -> pd.DataFrame:
    require_file(path, "IEEE118 full-truth CSV")
    truth = pd.read_csv(path)
    required = {"path", "first_line", "second_line", "critical", "critical_mechanism", "total_load_shed_mw"}
    missing = sorted(required - set(truth.columns))
    if missing:
        raise ValueError(f"Full-truth CSV missing required columns: {missing}")
    if "valid_ordered_n2" in truth.columns:
        truth = truth.loc[truth["valid_ordered_n2"].fillna(True).astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    if "first_step_critical" in truth.columns:
        truth = truth.loc[~truth["first_step_critical"].fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})].copy()
    if truth.empty:
        raise ValueError("Full-truth CSV contains no valid ordered N-2 rows after early-stop filtering.")
    truth["critical"] = coerce_bool(truth["critical"])
    truth["relay_cascade"] = truth["critical_mechanism"].fillna("").astype(str).eq("relay_cascade")
    truth["total_load_shed_mw"] = pd.to_numeric(truth["total_load_shed_mw"], errors="coerce").fillna(0.0)
    truth["full_cascade_path"] = truth.apply(construct_full_cascade_path, axis=1)
    return truth.reset_index(drop=True)


def load_external_normalizer(path: Path | None) -> dict[str, dict[str, float]] | None:
    if path is None:
        return None
    require_file(path, "paper-aligned feature normalizer JSON")
    normalizer = json.loads(path.read_text(encoding="utf-8"))
    missing = [name for name in PAPER_FEATURE_NAMES if name not in normalizer]
    if missing:
        raise ValueError(f"Feature normalizer missing paper-style keys: {missing}")
    return normalizer


def predict_s1_probabilities(dataset_npz: Path, model_path: Path, feature_normalizer_json: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    require_file(dataset_npz, "IEEE118 RTS-79 GCN dataset NPZ")
    require_file(model_path, "trained original RTS-79 GCN model")
    data = np.load(dataset_npz, allow_pickle=True)
    normalizer = load_external_normalizer(feature_normalizer_json)
    if normalizer is not None:
        if "physics_raw_features" not in data:
            raise ValueError("Dataset NPZ must contain physics_raw_features when --feature-normalizer-json is used.")
        x = normalize_x(data["physics_raw_features"].astype(np.float32), normalizer, PAPER_FEATURE_NAMES).astype(np.float32)
    else:
        x = data["x_gcn"].astype(np.float32)
    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    train_config = PaperGcnTrainConfig(**checkpoint["train_config"])
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=train_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    adjacency = build_branch_graph_adjacency_from_endpoints(data["branch_from_bus"], data["branch_to_bus"])
    adjacency_powers = torch.tensor(build_adjacency_powers(adjacency, train_config.k_gcn), dtype=torch.float32)
    probs = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            logits = model(torch.tensor(x[start : start + 128], dtype=torch.float32), adjacency_powers)
            probs.append(torch.softmax(logits, dim=2)[:, :, 1].detach().cpu().numpy())
    return np.concatenate(probs), data["line_labels"].astype(str)


def make_path_score_table(path_index_csv: Path, first_prob_csv: Path, s1_probability: np.ndarray, truth: pd.DataFrame) -> pd.DataFrame:
    require_file(path_index_csv, "IEEE118 RTS-79 GCN path index CSV")
    require_file(first_prob_csv, "IEEE118 first-step probability CSV")
    path_index = pd.read_csv(path_index_csv)
    first = pd.read_csv(first_prob_csv)
    first_prob = {str(row["line_label"]): float(row["p_shed_first"]) for _, row in first.iterrows()}
    rows = []
    truth_small = truth[
        [
            "path",
            "critical",
            "relay_cascade",
            "total_load_shed_mw",
            "full_cascade_path",
        ]
    ]
    for _, row in path_index.iterrows():
        sample_idx = int(row["sample_index"])
        line_idx = int(row["line_index"])
        first_line = str(row["first_line"])
        second_line = str(row["second_line"])
        p_first = float(first_prob[first_line])
        p_second = float(s1_probability[sample_idx, line_idx])
        rows.append(
            {
                "path": str(row["path"]),
                "first_line": first_line,
                "second_line": second_line,
                "p_shed_first": p_first,
                "p_shed_second": p_second,
                "path_product_score": p_first * p_second,
                "label_critical": int(row["label_critical"]),
                "label_relay_cascade": int(row["label_relay_cascade"]),
            }
        )
    score = pd.DataFrame(rows).merge(truth_small, on="path", how="left")
    return score


def build_y_p_scores(args: argparse.Namespace) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
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
    second_scores: dict[str, dict[str, float]] = {}
    for first_line in adapter.line_labels:
        state = run_sequential_outages_for_case(
            scenario_case,
            adapter,
            [first_line],
            beta=args.beta,
            security_limit=args.security_limit,
        )
        table = calculate_lodf_y_p(state["case"], adapter.line_labels, beta=args.beta).dropna(subset=["y_P"])
        second_scores[first_line] = {str(row["candidate_line"]): float(row["y_P"]) for _, row in table.iterrows()}
    return first_scores, second_scores


def pfw_scores_from_case(case: dict, line_labels: tuple[str, ...]) -> dict[str, float]:
    branch = case["branch"]
    if branch.shape[1] <= PF:
        raise ValueError("Branch matrix does not contain PF results required for PFW scoring.")
    status = branch[:, BR_STATUS].astype(int)
    flow = np.where(status == 1, np.abs(branch[:, PF].astype(float)), -np.inf)
    return {label: float(flow[idx]) for idx, label in enumerate(line_labels)}


def build_pfw_scores(args: argparse.Namespace) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    adapter = build_case_adapter("ieee118")
    scenario_case = apply_ieee118_load_scenario(adapter.case, seed=args.seed, load_scale=args.load_scale)
    scenario_case = apply_thermal_limit_mode(
        scenario_case,
        limit_mode=args.limit_mode,
        flow_limit_scale=args.flow_limit_scale,
        min_rate_a=args.min_rate_a,
    )
    first_scores = pfw_scores_from_case(scenario_case, adapter.line_labels)
    second_scores: dict[str, dict[str, float]] = {}
    for first_line in adapter.line_labels:
        state = run_sequential_outages_for_case(
            scenario_case,
            adapter,
            [first_line],
            beta=args.beta,
            security_limit=args.security_limit,
        )
        second_scores[first_line] = pfw_scores_from_case(state["case"], adapter.line_labels)
    return first_scores, second_scores


def dedupe_order(paths: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for path in paths:
        if path not in seen:
            ordered.append(path)
            seen.add(path)
    return ordered


def label_method(method: str, suffix: str) -> str:
    if suffix and method.startswith("RTS79_GCN_"):
        return f"{method}{suffix}"
    return method


def make_orders(
    score: pd.DataFrame,
    y_p_first: dict[str, float],
    y_p_second: dict[str, dict[str, float]],
    pfw_first: dict[str, float],
    pfw_second: dict[str, dict[str, float]],
    random_seeds: list[int],
    *,
    method_suffix: str = "",
) -> dict[str, list[str]]:
    all_paths = score["path"].astype(str).tolist()
    first_lines = sorted(score["first_line"].astype(str).unique())
    orders: dict[str, list[str]] = {"line_order": all_paths}
    paths = []
    first_order = sorted(first_lines, key=lambda line: (-float(score.loc[score["first_line"] == line, "p_shed_first"].iloc[0]), line))
    for first in first_order:
        group = score.loc[score["first_line"] == first].copy()
        group = group.sort_values(["p_shed_second", "second_line"], ascending=[False, True])
        paths.extend(group["path"].astype(str).tolist())
    orders[label_method(METHOD_GCN_PROB, method_suffix)] = dedupe_order(paths)

    paths = []
    first_order = sorted(
        first_lines,
        key=lambda line: (
            -float(score.loc[score["first_line"] == line, "p_shed_first"].iloc[0]),
            -float(y_p_first.get(line, 0.0)),
            line,
        ),
    )
    for first in first_order:
        group = score.loc[score["first_line"] == first].copy()
        group["second_y_p"] = group["second_line"].map(lambda second: float(y_p_second.get(first, {}).get(str(second), 0.0)))
        group = group.sort_values(["p_shed_second", "second_y_p", "second_line"], ascending=[False, False, True])
        paths.extend(group["path"].astype(str).tolist())
    orders[label_method(METHOD_GCN_PROB_YP, method_suffix)] = dedupe_order(paths)

    orders[label_method(METHOD_GCN_PATH_PROB, method_suffix)] = score.sort_values(
        ["path_product_score", "p_shed_first", "p_shed_second", "path"],
        ascending=[False, False, False, True],
    )["path"].astype(str).tolist()
    orders[label_method(METHOD_SECOND_ONLY, method_suffix)] = score.sort_values(["p_shed_second", "path"], ascending=[False, True])["path"].astype(str).tolist()

    paths = []
    first_order = sorted(first_lines, key=lambda line: (-float(y_p_first.get(line, -np.inf)), line))
    for first in first_order:
        group = score.loc[score["first_line"] == first].copy()
        group["second_y_p"] = group["second_line"].map(lambda second: float(y_p_second.get(first, {}).get(str(second), -np.inf)))
        group = group.sort_values(["second_y_p", "second_line"], ascending=[False, True])
        paths.extend(group["path"].astype(str).tolist())
    orders["LODF_yP"] = dedupe_order(paths)
    paths = []
    first_order = sorted(first_lines, key=lambda line: (-float(pfw_first.get(line, -np.inf)), line))
    for first in first_order:
        group = score.loc[score["first_line"] == first].copy()
        group["second_pfw"] = group["second_line"].map(lambda second: float(pfw_second.get(first, {}).get(str(second), -np.inf)))
        group = group.sort_values(["second_pfw", "second_line"], ascending=[False, True])
        paths.extend(group["path"].astype(str).tolist())
    orders[METHOD_PFW] = dedupe_order(paths)

    for seed in random_seeds:
        shuffled = list(all_paths)
        random.Random(seed).shuffle(shuffled)
        orders[f"random_seed_{seed}"] = shuffled
    return orders


def evaluate_order(method: str, ordered_paths: list[str], truth: pd.DataFrame, budgets: pd.DataFrame) -> pd.DataFrame:
    truth_by_path = truth.set_index("path")
    ranked = truth_by_path.reindex(ordered_paths).dropna(subset=["critical"]).reset_index()
    total_paths = len(truth)
    total_critical = int(truth["critical"].sum())
    total_relay = int(truth["relay_cascade"].sum())
    total_shed = float(truth["total_load_shed_mw"].sum())
    total_relay_shed = float(truth.loc[truth["relay_cascade"], "total_load_shed_mw"].sum())
    rows = []
    for _, budget in budgets.iterrows():
        k = int(budget["K"])
        top = ranked.head(k)
        critical_hits = int(top["critical"].sum())
        relay_hits = int(top["relay_cascade"].sum())
        shed = float(top["total_load_shed_mw"].sum())
        relay_shed = float(top.loc[top["relay_cascade"], "total_load_shed_mw"].sum())
        rows.append(
            {
                "method": method,
                "budget_type": budget["budget_type"],
                "budget_label": budget["budget_label"],
                "K": k,
                "search_budget_ratio": k / total_paths,
                "critical_hit_count": critical_hits,
                "relay_cascade_hit_count": relay_hits,
                "recall_critical": critical_hits / max(total_critical, 1),
                "recall_relay_cascade": relay_hits / max(total_relay, 1),
                "precision_at_k": critical_hits / max(k, 1),
                "captured_load_shed_mw": shed,
                "captured_load_shed_ratio": shed / max(total_shed, 1e-12),
                "captured_relay_cascade_load_shed_mw": relay_shed,
                "captured_relay_cascade_load_shed_ratio": relay_shed / max(total_relay_shed, 1e-12),
            }
        )
    return pd.DataFrame(rows)


def summarize_random(rows: list[pd.DataFrame]) -> pd.DataFrame:
    raw = pd.concat(rows, ignore_index=True).assign(method="random")
    group_cols = ["method", "budget_type", "budget_label", "K", "search_budget_ratio"]
    metric_cols = [col for col in raw.columns if col not in group_cols]
    out = []
    for key, group in raw.groupby(group_cols, sort=False):
        row = dict(zip(group_cols, key))
        for col in metric_cols:
            vals = pd.to_numeric(group[col], errors="coerce")
            row[col] = float(vals.mean())
            row[f"{col}_std"] = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
        out.append(row)
    return pd.DataFrame(out)


def sparse_curve_points(method: str, ordered_paths: list[str], truth: pd.DataFrame, budgets: pd.DataFrame) -> pd.DataFrame:
    truth_by_path = truth.set_index("path")
    ranked = truth_by_path.reindex(ordered_paths).dropna(subset=["critical"]).reset_index()
    fixed_points = set(int(k) for k in budgets["K"].tolist())
    for k in range(50, min(1000, len(ranked)) + 1, 50):
        fixed_points.add(k)
    for k in range(1500, len(ranked) + 1, 500):
        fixed_points.add(k)
    fixed_points.add(len(ranked))
    rows = []
    found_full_paths: set[str] = set()
    critical_hits = 0
    relay_hits = 0
    captured_shed = 0.0
    point_iter = iter(sorted(fixed_points))
    next_point = next(point_iter, None)
    for idx, row in enumerate(ranked.itertuples(index=False), start=1):
        is_critical = bool(getattr(row, "critical"))
        if is_critical:
            critical_hits += 1
            found_full_paths.add(str(getattr(row, "full_cascade_path")))
        if bool(getattr(row, "relay_cascade")):
            relay_hits += 1
        captured_shed += float(getattr(row, "total_load_shed_mw"))
        while next_point is not None and idx == next_point:
            rows.append(
                {
                    "method": method,
                    "candidate_evaluations": idx,
                    "found_critical_count_full_cascade_dedup": len(found_full_paths),
                    "critical_hit_count_path_level": critical_hits,
                    "relay_cascade_hit_count_path_level": relay_hits,
                    "captured_load_shed_mw": captured_shed,
                }
            )
            next_point = next(point_iter, None)
    return pd.DataFrame(rows)


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def load_first_step_stats(fulltruth_csv: Path) -> dict[str, Any]:
    first_path = fulltruth_csv.with_name("ieee118_first_step_summary.csv")
    if not first_path.exists():
        return {
            "num_first_step_critical_lines": 0,
            "first_step_critical_total_load_shed_mw_sum": 0.0,
            "first_step_critical_lines": [],
            "num_skipped_ordered_n2_paths": 0,
            "source": None,
        }
    first = pd.read_csv(first_path)
    critical = first["first_step_critical"].fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})
    return {
        "num_first_step_critical_lines": int(critical.sum()),
        "first_step_critical_total_load_shed_mw_sum": float(pd.to_numeric(first.loc[critical, "first_step_total_load_shed_mw"], errors="coerce").fillna(0.0).sum()),
        "first_step_critical_lines": first.loc[critical, "first_line"].astype(str).tolist(),
        "num_skipped_ordered_n2_paths": int(pd.to_numeric(first.get("num_skipped_second_lines", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()),
        "source": str(first_path),
    }


def evaluate_protocol(args: argparse.Namespace) -> pd.DataFrame:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    truth = load_truth(args.fulltruth_csv)
    first_step_stats = load_first_step_stats(args.fulltruth_csv)
    s1_probability, line_labels = predict_s1_probabilities(args.dataset_npz, args.model_path, args.feature_normalizer_json)
    score = make_path_score_table(args.path_index_csv, args.first_step_probabilities_csv, s1_probability, truth)
    y_p_first, y_p_second = build_y_p_scores(args)
    pfw_first, pfw_second = build_pfw_scores(args)
    orders = make_orders(score, y_p_first, y_p_second, pfw_first, pfw_second, args.random_seeds, method_suffix=args.method_suffix)
    budgets = budget_table(len(truth))
    summary_parts = []
    random_parts = []
    curve_parts = []
    for method, order in orders.items():
        if method.startswith("random_seed_"):
            random_parts.append(evaluate_order(method, order, truth, budgets))
            continue
        summary_parts.append(evaluate_order(method, order, truth, budgets))
        curve_parts.append(sparse_curve_points(method, order, truth, budgets))
    summary_parts.append(summarize_random(random_parts))
    summary = pd.concat(summary_parts, ignore_index=True, sort=False)
    prefix = str(args.output_prefix)
    summary.to_csv(args.output_dir / f"{prefix}_search_summary.csv", index=False, encoding="utf-8-sig")
    write_json(args.output_dir / f"{prefix}_search_summary.json", summary.to_dict("records"))
    pd.concat(curve_parts, ignore_index=True, sort=False).to_csv(
        args.output_dir / f"{prefix}_curve_points_sparse.csv",
        index=False,
        encoding="utf-8-sig",
    )
    top_rows = []
    for method in [
        label_method(METHOD_GCN_PATH_PROB, args.method_suffix),
        label_method(METHOD_GCN_PROB, args.method_suffix),
        label_method(METHOD_GCN_PROB_YP, args.method_suffix),
        label_method(METHOD_SECOND_ONLY, args.method_suffix),
        METHOD_PFW,
        "LODF_yP",
    ]:
        ranked = score.set_index("path").reindex(orders[method]).dropna(subset=["first_line"]).reset_index().head(args.topk_output_rows)
        ranked.insert(0, "method", method)
        ranked.insert(1, "rank", np.arange(1, len(ranked) + 1))
        top_rows.append(ranked)
    pd.concat(top_rows, ignore_index=True, sort=False).to_csv(
        args.output_dir / f"{prefix}_topk_paths.csv",
        index=False,
        encoding="utf-8-sig",
    )
    first_step_out = args.output_dir / f"{prefix}_first_step_probabilities.csv"
    if args.first_step_probabilities_csv.resolve() != first_step_out.resolve():
        pd.read_csv(args.first_step_probabilities_csv).to_csv(first_step_out, index=False, encoding="utf-8-sig")
    write_json(
        args.output_dir / f"{prefix}_config.json",
        {
            "dataset_npz": str(args.dataset_npz),
            "path_index_csv": str(args.path_index_csv),
            "fulltruth_csv": str(args.fulltruth_csv),
            "model_path": str(args.model_path),
            "first_step_probabilities_csv": str(args.first_step_probabilities_csv),
            "feature_normalizer_json": str(args.feature_normalizer_json) if args.feature_normalizer_json else None,
            "feature_mode": "paper",
            "line_labels": "L001-L186",
            "main_method": label_method(METHOD_GCN_PATH_PROB, args.method_suffix),
            "second_only_ablation": label_method(METHOD_SECOND_ONLY, args.method_suffix),
            "pfw_baseline": METHOD_PFW,
            "num_valid_ordered_n2_paths": int(len(truth)),
            **first_step_stats,
            "full_cascade_path_rule": "first_line -> second_line -> relay_trip_labels in recorded order; fallback to final_outage_labels when relay_trip_labels is empty.",
        },
    )
    (args.output_dir / f"{prefix}_readme.md").write_text(
        "# IEEE118 RTS-79 Protocol Search\n\n"
        f"Main method: `{label_method(METHOD_GCN_PATH_PROB, args.method_suffix)}`, using `p_shed(Li|S0) * p_shed(Lj|S1(i))`.\n"
        f"`{label_method(METHOD_SECOND_ONLY, args.method_suffix)}` is retained only as an ablation.\n"
        f"`{METHOD_PFW}` is the power-flow-weighted baseline using absolute PF in S0 and S1 states.\n"
        f"Valid ordered N-2 paths: {len(truth)}.\n"
        "Curve points are sparse and include RTS-79-style full-cascade-path deduplicated counts.\n"
        "The full-cascade path is an approximate reconstruction from relay/final outage labels, "
        "not an exact protection_event_table replay.\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    args = parse_args()
    summary = evaluate_protocol(args)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
