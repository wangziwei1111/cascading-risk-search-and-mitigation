from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from evaluate_rts79_paper_gcn_search import (
    SearchEvalConfig,
    _build_full_cascade_truth,
    _load_gcn_model,
    _make_detection_curve,
    _make_line_order,
    _make_oracle_order,
    _make_random_order,
    _make_search_summary,
    _normalize_with_saved_stats,
    _predict_gcn_shed_probability,
)
from rts79_cascade import (
    Rts79InitialConfig,
    line_label_to_index_1based,
    run_initial_dcopf,
    run_sequential_initial_outages_dcpf,
    search_all_n2_cascade_paths,
)
from rts79_lodf import calculate_physical_vulnerability_y_p


@dataclass(frozen=True)
class StrictAlgorithm1Config:
    """Strict Algorithm 1 evaluation config; strict means recursive GCN-then-y_P search."""

    seed: int = 20260722
    beta: float = 1.2
    security_limit: float = 1.0
    gcn_threshold: float = 0.5
    random_failure_limit_r: int = 2
    random_seed: int = 20260512


def evaluate_strict_algorithm1(
    model_path: str | Path,
    normalizer_path: str | Path,
    output_dir: str | Path,
    config: StrictAlgorithm1Config,
) -> pd.DataFrame:
    """Evaluate the paper Algorithm 1 recursion: y_GCN positives first, then y_P order."""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model, adjacency_powers = _load_gcn_model(model_path)
    normalizer = json.loads(Path(normalizer_path).read_text(encoding="utf-8"))
    search_config = SearchEvalConfig(
        seed=config.seed,
        beta=config.beta,
        security_limit=config.security_limit,
        gcn_threshold=config.gcn_threshold,
        random_seed=config.random_seed,
    )
    initial_config = Rts79InitialConfig(random_seed=config.seed)
    exhaustive = search_all_n2_cascade_paths(
        config=initial_config,
        relay_threshold_beta=config.beta,
        security_limit=config.security_limit,
    ).summary_table
    full_truth = _build_full_cascade_truth(exhaustive, initial_config, search_config)
    critical_paths = set(full_truth.loc[full_truth["critical"], "full_cascade_path"].tolist())
    full_truth.to_csv(out / "rts79_algorithm1_strict_exhaustive_truth.csv", index=False, encoding="utf-8-sig")

    strict_order, strict_trace = _make_strict_algorithm1_order(
        model=model,
        adjacency_powers=adjacency_powers,
        normalizer=normalizer,
        initial_config=initial_config,
        config=config,
    )
    method_orders = {
        "Algorithm1_strict_GCN_yP": strict_order,
        "line_order": _make_line_order(),
        "random": _make_random_order(config.random_seed),
        "oracle": _make_oracle_order(exhaustive),
    }

    curves: list[pd.DataFrame] = []
    orders: list[pd.DataFrame] = []
    for method, ordered_paths in method_orders.items():
        curve = _make_detection_curve(method, ordered_paths, critical_paths, full_truth)
        curves.append(curve)
        orders.append(
            pd.DataFrame(
                {
                    "search_method": method,
                    "search_attempt": np.arange(1, len(ordered_paths) + 1),
                    "path": ordered_paths,
                }
            )
        )

    curve_table = pd.concat(curves, ignore_index=True)
    order_table = pd.concat(orders, ignore_index=True)
    summary = _make_search_summary(curve_table, len(critical_paths))
    curve_table.to_csv(out / "rts79_algorithm1_strict_efficiency_curve.csv", index=False, encoding="utf-8-sig")
    order_table.to_csv(out / "rts79_algorithm1_strict_search_order.csv", index=False, encoding="utf-8-sig")
    strict_trace.to_csv(out / "rts79_algorithm1_strict_node_trace.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(out / "rts79_algorithm1_strict_summary.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_algorithm1_strict_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[Algorithm1严格搜索] 真实关键路径数量: {len(critical_paths)}")
    print(summary.to_string(index=False))
    return summary


def _make_strict_algorithm1_order(
    model: torch.nn.Module,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    initial_config: Rts79InitialConfig,
    config: StrictAlgorithm1Config,
) -> tuple[list[str], pd.DataFrame]:
    root_case = run_initial_dcopf(initial_config).case
    leaf_paths: list[str] = []
    trace_records: list[dict] = []
    visited_leaf_paths: set[str] = set()

    def recurse(active_sequence: tuple[str, ...], state_case: dict) -> None:
        if len(active_sequence) >= config.random_failure_limit_r:
            path = "->".join(active_sequence)
            if path not in visited_leaf_paths:
                visited_leaf_paths.add(path)
                leaf_paths.append(path)
            return

        candidate_order, node_table = _strict_node_candidate_order(
            case=state_case,
            active_sequence=active_sequence,
            model=model,
            adjacency_powers=adjacency_powers,
            normalizer=normalizer,
            config=config,
        )
        trace_records.extend(node_table.to_dict(orient="records"))
        for candidate in candidate_order:
            if candidate in active_sequence:
                continue
            next_sequence = tuple([*active_sequence, candidate])
            next_state = run_sequential_initial_outages_dcpf(
                next_sequence,
                config=initial_config,
                relay_threshold_beta=config.beta,
                security_limit=config.security_limit,
            )
            recurse(next_sequence, next_state.case)

    recurse(tuple(), root_case)
    return leaf_paths, pd.DataFrame(trace_records)


def _strict_node_candidate_order(
    case: dict,
    active_sequence: tuple[str, ...],
    model: torch.nn.Module,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    config: StrictAlgorithm1Config,
) -> tuple[list[str], pd.DataFrame]:
    probability = _predict_gcn_shed_probability(model, adjacency_powers, normalizer, case, config.beta)
    y_p_table = calculate_physical_vulnerability_y_p(case, beta=config.beta).dropna(subset=["y_P"])
    online_labels = y_p_table["candidate_line"].tolist()
    online_set = set(online_labels)
    used = set(active_sequence)
    gcn_positive = [
        label
        for label in [f"L{i:02d}" for i in range(1, 39)]
        if label in online_set
        and label not in used
        and probability[line_label_to_index_1based(label) - 1] >= config.gcn_threshold
    ]
    y_p_order = [
        str(row["candidate_line"])
        for _, row in y_p_table.sort_values(["y_P", "candidate_line"], ascending=[False, True]).iterrows()
        if str(row["candidate_line"]) not in used
    ]
    ordered: list[str] = []
    searched_by: dict[str, str] = {}
    for label in gcn_positive:
        if label not in searched_by:
            searched_by[label] = "GCN"
            ordered.append(label)
    for label in y_p_order:
        if label not in searched_by:
            searched_by[label] = "y_P"
            ordered.append(label)

    y_p_by_label = {str(row["candidate_line"]): float(row["y_P"]) for _, row in y_p_table.iterrows()}
    node_name = "root" if not active_sequence else "->".join(active_sequence)
    trace = pd.DataFrame(
        [
            {
                "active_sequence": node_name,
                "active_depth": len(active_sequence),
                "candidate_rank": rank,
                "candidate_line": label,
                "searched_by": searched_by[label],
                "p_shed": float(probability[line_label_to_index_1based(label) - 1]),
                "y_P": y_p_by_label.get(label, np.nan),
            }
            for rank, label in enumerate(ordered, start=1)
        ]
    )
    return ordered, trace


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate strict recursive Algorithm 1 search on RTS-79.")
    parser.add_argument("--model", required=True, help="GCN model .pt file.")
    parser.add_argument("--normalizer", required=True, help="Feature normalizer JSON file.")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "algorithm1_strict_search_eval"))
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--gcn-threshold", type=float, default=0.5)
    parser.add_argument("--random-failure-limit-r", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = StrictAlgorithm1Config(
        seed=args.seed,
        beta=args.beta,
        security_limit=args.security_limit,
        gcn_threshold=args.gcn_threshold,
        random_failure_limit_r=args.random_failure_limit_r,
    )
    evaluate_strict_algorithm1(args.model, args.normalizer, args.output_dir, config)


if __name__ == "__main__":
    main()
