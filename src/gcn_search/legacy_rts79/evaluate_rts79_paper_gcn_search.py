from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from rts79_cascade import (
    Rts79InitialConfig,
    line_label_to_index_1based,
    run_initial_dcopf,
    run_sequential_initial_outages_dcpf,
    search_all_n2_cascade_paths,
    simulate_cascade_path,
)
from rts79_lodf import calculate_physical_vulnerability_y_p
from train_rts79_paper_gcn import PaperGcnTrainConfig, PaperStyleRts79Gcn, _make_x_gcn


@dataclass(frozen=True)
class SearchEvalConfig:
    """搜索评估配置；search 是“搜索”，evaluation 是“评估”。"""

    seed: int = 20260722
    beta: float = 1.2
    security_limit: float = 1.0
    gcn_threshold: float = 0.5
    random_seed: int = 20260512


def evaluate_search_methods(
    model_path: str | Path,
    normalizer_path: str | Path,
    output_dir: str | Path,
    config: SearchEvalConfig,
) -> pd.DataFrame:
    """按论文 Algorithm 1 评估 GCN+y_P 引导搜索效率。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model, adjacency_powers = _load_gcn_model(model_path)
    normalizer = json.loads(Path(normalizer_path).read_text(encoding="utf-8"))
    initial_config = Rts79InitialConfig(random_seed=config.seed)
    exhaustive = search_all_n2_cascade_paths(
        config=initial_config,
        relay_threshold_beta=config.beta,
        security_limit=config.security_limit,
    ).summary_table
    full_truth = _build_full_cascade_truth(exhaustive, initial_config, config)
    critical_paths = set(full_truth.loc[full_truth["critical"], "full_cascade_path"].tolist())
    full_truth.to_csv(out / "rts79_search_eval_exhaustive_truth.csv", index=False, encoding="utf-8-sig")

    method_orders = {
        "GCN_yP": _make_gcn_yp_order(model, adjacency_powers, normalizer, initial_config, config),
        "GCN_filter_yP": _make_gcn_filter_yp_order(model, adjacency_powers, normalizer, initial_config, config),
        "GCN_prob": _make_gcn_probability_order(model, adjacency_powers, normalizer, initial_config, config, use_y_p=False),
        "GCN_prob_yP": _make_gcn_probability_order(model, adjacency_powers, normalizer, initial_config, config, use_y_p=True),
        "GCN_path_prob": _make_gcn_path_probability_order(model, adjacency_powers, normalizer, initial_config, config),
        "LODF_yP": _make_lodf_order(initial_config, config),
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
                    "full_cascade_path": [_lookup_full_path(path, full_truth) for path in ordered_paths],
                    "is_critical": [_lookup_full_path(path, full_truth) in critical_paths for path in ordered_paths],
                }
            )
        )

    curve_table = pd.concat(curves, ignore_index=True)
    order_table = pd.concat(orders, ignore_index=True)
    curve_table.to_csv(out / "rts79_search_efficiency_curve.csv", index=False, encoding="utf-8-sig")
    order_table.to_csv(out / "rts79_search_order.csv", index=False, encoding="utf-8-sig")
    summary = _make_search_summary(curve_table, len(critical_paths))
    summary.to_csv(out / "rts79_search_efficiency_summary.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_search_eval_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[搜索评估] 真实关键路径数量: {len(critical_paths)}")
    print(summary.to_string(index=False))
    return summary


def _build_full_cascade_truth(
    exhaustive: pd.DataFrame,
    initial_config: Rts79InitialConfig,
    config: SearchEvalConfig,
) -> pd.DataFrame:
    records: list[dict] = []
    for _, row in exhaustive.iterrows():
        path = str(row["path"])
        if not bool(row["critical"]):
            records.append(
                {
                    **row.to_dict(),
                    "full_cascade_path": "",
                    "full_cascade_length": 0,
                }
            )
            continue
        first_line, second_line = path.split("->")
        result = simulate_cascade_path(
            [first_line, second_line],
            config=initial_config,
            relay_threshold_beta=config.beta,
            security_limit=config.security_limit,
        )
        full_path = _extract_ordered_full_cascade_path([first_line, second_line], result.protection_event_table)
        records.append(
            {
                **row.to_dict(),
                "full_cascade_path": "->".join(full_path),
                "full_cascade_length": len(full_path),
            }
        )
    return pd.DataFrame(records)


def _extract_ordered_full_cascade_path(initial_sequence: list[str], event_table: pd.DataFrame) -> list[str]:
    full_path = [label.strip().upper() for label in initial_sequence]
    if event_table.empty or "newly_tripped" not in event_table:
        return full_path
    for _, event in event_table.sort_values(["event", "round"]).iterrows():
        newly_tripped = str(event.get("newly_tripped", "")).strip()
        if not newly_tripped:
            continue
        for label in newly_tripped.split(","):
            normalized = label.strip().upper()
            if normalized:
                full_path.append(normalized)
    return full_path


def _lookup_full_path(path: str, truth_table: pd.DataFrame) -> str:
    matched = truth_table.loc[truth_table["path"] == path, "full_cascade_path"]
    if matched.empty:
        return ""
    return str(matched.iloc[0])


def _load_gcn_model(model_path: str | Path) -> tuple[PaperStyleRts79Gcn, torch.Tensor]:
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    train_config = PaperGcnTrainConfig(**checkpoint["train_config"])
    model = PaperStyleRts79Gcn(input_channels=4, config=train_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    adjacency_powers = torch.tensor(checkpoint["adjacency_powers"], dtype=torch.float32)
    return model, adjacency_powers


def _make_gcn_yp_order(
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    initial_config: Rts79InitialConfig,
    config: SearchEvalConfig,
) -> list[str]:
    root_case = run_initial_dcopf(initial_config).case
    first_order = _rank_candidates_by_gcn_then_yp(root_case, model, adjacency_powers, normalizer, config)
    paths: list[str] = []
    for first_line in first_order:
        state = run_sequential_initial_outages_dcpf(
            [first_line],
            config=initial_config,
            relay_threshold_beta=config.beta,
            security_limit=config.security_limit,
        )
        second_order = _rank_candidates_by_gcn_then_yp(state.case, model, adjacency_powers, normalizer, config)
        for second_line in second_order:
            if second_line == first_line:
                continue
            paths.append(f"{first_line}->{second_line}")
    return _dedupe_ordered_paths(paths)


def _make_gcn_filter_yp_order(
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    initial_config: Rts79InitialConfig,
    config: SearchEvalConfig,
) -> list[str]:
    root_case = run_initial_dcopf(initial_config).case
    first_order = _rank_candidates_by_gcn_filter_then_yp(root_case, model, adjacency_powers, normalizer, config)
    paths: list[str] = []
    for first_line in first_order:
        state = run_sequential_initial_outages_dcpf(
            [first_line],
            config=initial_config,
            relay_threshold_beta=config.beta,
            security_limit=config.security_limit,
        )
        second_order = _rank_candidates_by_gcn_filter_then_yp(state.case, model, adjacency_powers, normalizer, config)
        for second_line in second_order:
            if second_line == first_line:
                continue
            paths.append(f"{first_line}->{second_line}")
    return _dedupe_ordered_paths(paths)


def _make_gcn_probability_order(
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    initial_config: Rts79InitialConfig,
    config: SearchEvalConfig,
    use_y_p: bool,
) -> list[str]:
    root_case = run_initial_dcopf(initial_config).case
    first_order = _rank_candidates_by_gcn_probability(root_case, model, adjacency_powers, normalizer, config, use_y_p)
    paths: list[str] = []
    for first_line in first_order:
        state = run_sequential_initial_outages_dcpf(
            [first_line],
            config=initial_config,
            relay_threshold_beta=config.beta,
            security_limit=config.security_limit,
        )
        second_order = _rank_candidates_by_gcn_probability(state.case, model, adjacency_powers, normalizer, config, use_y_p)
        for second_line in second_order:
            if second_line == first_line:
                continue
            paths.append(f"{first_line}->{second_line}")
    return _dedupe_ordered_paths(paths)


def _make_gcn_path_probability_order(
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    initial_config: Rts79InitialConfig,
    config: SearchEvalConfig,
) -> list[str]:
    root_case = run_initial_dcopf(initial_config).case
    first_probability = _predict_gcn_shed_probability(model, adjacency_powers, normalizer, root_case, config.beta)
    first_candidates = _online_candidate_labels(root_case, config)
    scored_paths: list[tuple[float, float, float, str]] = []
    for first_line in first_candidates:
        first_idx = line_label_to_index_1based(first_line) - 1
        state = run_sequential_initial_outages_dcpf(
            [first_line],
            config=initial_config,
            relay_threshold_beta=config.beta,
            security_limit=config.security_limit,
        )
        second_probability = _predict_gcn_shed_probability(model, adjacency_powers, normalizer, state.case, config.beta)
        second_candidates = _online_candidate_labels(state.case, config)
        for second_line in second_candidates:
            if second_line == first_line:
                continue
            second_idx = line_label_to_index_1based(second_line) - 1
            score = float(first_probability[first_idx] * second_probability[second_idx])
            scored_paths.append(
                (
                    -score,
                    -float(first_probability[first_idx]),
                    -float(second_probability[second_idx]),
                    f"{first_line}->{second_line}",
                )
            )
    scored_paths.sort()
    return _dedupe_ordered_paths([path for _, _, _, path in scored_paths])


def _online_candidate_labels(case: dict, config: SearchEvalConfig) -> list[str]:
    y_p_table = calculate_physical_vulnerability_y_p(case, beta=config.beta)
    online = set(y_p_table.dropna(subset=["y_P"])["candidate_line"].tolist())
    return [f"L{i:02d}" for i in range(1, 39) if f"L{i:02d}" in online]


def _rank_candidates_by_gcn_probability(
    case: dict,
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    config: SearchEvalConfig,
    use_y_p: bool,
) -> list[str]:
    probability = _predict_gcn_shed_probability(model, adjacency_powers, normalizer, case, config.beta)
    labels = [f"L{i:02d}" for i in range(1, 39)]
    y_p: dict[str, float] = {}
    if use_y_p:
        y_p_table = calculate_physical_vulnerability_y_p(case, beta=config.beta)
        y_p = {row["candidate_line"]: float(row["y_P"]) for _, row in y_p_table.dropna(subset=["y_P"]).iterrows()}
        online_labels = [label for label in labels if label in y_p]
    else:
        y_p_table = calculate_physical_vulnerability_y_p(case, beta=config.beta)
        online = set(y_p_table.dropna(subset=["y_P"])["candidate_line"].tolist())
        online_labels = [label for label in labels if label in online]
    return sorted(
        online_labels,
        key=lambda label: (
            -probability[line_label_to_index_1based(label) - 1],
            -y_p.get(label, 0.0),
            label,
        ),
    )


def _rank_candidates_by_gcn_then_yp(
    case: dict,
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    config: SearchEvalConfig,
) -> list[str]:
    probability = _predict_gcn_shed_probability(model, adjacency_powers, normalizer, case, config.beta)
    y_p_table = calculate_physical_vulnerability_y_p(case, beta=config.beta)
    y_p = {row["candidate_line"]: float(row["y_P"]) for _, row in y_p_table.dropna(subset=["y_P"]).iterrows()}
    labels = [f"L{i:02d}" for i in range(1, 39)]
    online_labels = [label for label in labels if label in y_p]
    gcn_positive = [label for label in online_labels if probability[line_label_to_index_1based(label) - 1] >= config.gcn_threshold]
    gcn_positive.sort(key=lambda label: (-probability[line_label_to_index_1based(label) - 1], -y_p[label], label))
    remaining = [label for label in online_labels if label not in set(gcn_positive)]
    remaining.sort(key=lambda label: (-y_p[label], label))
    return gcn_positive + remaining


def _rank_candidates_by_gcn_filter_then_yp(
    case: dict,
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    config: SearchEvalConfig,
) -> list[str]:
    probability = _predict_gcn_shed_probability(model, adjacency_powers, normalizer, case, config.beta)
    y_p_table = calculate_physical_vulnerability_y_p(case, beta=config.beta)
    y_p = {row["candidate_line"]: float(row["y_P"]) for _, row in y_p_table.dropna(subset=["y_P"]).iterrows()}
    labels = [f"L{i:02d}" for i in range(1, 39)]
    online_labels = [label for label in labels if label in y_p]
    gcn_positive = [
        label for label in online_labels if probability[line_label_to_index_1based(label) - 1] >= config.gcn_threshold
    ]
    gcn_positive.sort(key=lambda label: (-y_p[label], label))
    remaining = [label for label in online_labels if label not in set(gcn_positive)]
    remaining.sort(key=lambda label: (-y_p[label], label))
    return gcn_positive + remaining


def _predict_gcn_shed_probability(
    model: PaperStyleRts79Gcn,
    adjacency_powers: torch.Tensor,
    normalizer: dict,
    case: dict,
    beta: float,
) -> np.ndarray:
    x_raw = _make_x_gcn(case, beta)[None, :, :]
    x = _normalize_with_saved_stats(x_raw, normalizer)
    with torch.no_grad():
        logits = model(torch.tensor(x, dtype=torch.float32), adjacency_powers)
        return torch.softmax(logits, dim=2)[0, :, 1].numpy()


def _normalize_with_saved_stats(x: np.ndarray, normalizer: dict) -> np.ndarray:
    normalized = x.copy()
    names = [
        "x_t 拓扑状态，支路断开为1，在线为0",
        "x_p 保护继电器指标，等于 |L_k|/(beta L_k^max)",
        "x_b 支路潮流绝对值",
        "x_l 支路两端母线较大负荷",
    ]
    for idx, name in enumerate(names):
        normalized[:, :, idx] = (normalized[:, :, idx] - normalizer[name]["mean"]) / normalizer[name]["std"]
    return normalized


def _make_lodf_order(initial_config: Rts79InitialConfig, config: SearchEvalConfig) -> list[str]:
    root_case = run_initial_dcopf(initial_config).case
    first_order = _rank_candidates_by_yp(root_case, config)
    paths: list[str] = []
    for first_line in first_order:
        state = run_sequential_initial_outages_dcpf(
            [first_line],
            config=initial_config,
            relay_threshold_beta=config.beta,
            security_limit=config.security_limit,
        )
        second_order = _rank_candidates_by_yp(state.case, config)
        for second_line in second_order:
            if second_line == first_line:
                continue
            paths.append(f"{first_line}->{second_line}")
    return _dedupe_ordered_paths(paths)


def _rank_candidates_by_yp(case: dict, config: SearchEvalConfig) -> list[str]:
    table = calculate_physical_vulnerability_y_p(case, beta=config.beta).dropna(subset=["y_P"])
    return table.sort_values(["y_P", "candidate_line"], ascending=[False, True])["candidate_line"].tolist()


def _make_line_order() -> list[str]:
    labels = [f"L{i:02d}" for i in range(1, 39)]
    return [f"{first}->{second}" for first in labels for second in labels if second != first]


def _make_random_order(random_seed: int) -> list[str]:
    paths = _make_line_order()
    rng = random.Random(random_seed)
    rng.shuffle(paths)
    return paths


def _make_oracle_order(exhaustive: pd.DataFrame) -> list[str]:
    ordered = exhaustive.sort_values(["critical", "total_load_shed_mw"], ascending=[False, False])
    return ordered["path"].tolist()


def _dedupe_ordered_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def _make_detection_curve(
    method: str,
    ordered_paths: list[str],
    critical_paths: set[str],
    truth_table: pd.DataFrame,
) -> pd.DataFrame:
    truth_by_path = truth_table.set_index("path").to_dict(orient="index")
    found: set[str] = set()
    records: list[dict] = []
    for attempt, path in enumerate(ordered_paths, start=1):
        truth = truth_by_path.get(path, {})
        full_path = str(truth.get("full_cascade_path", ""))
        is_critical = bool(full_path and full_path in critical_paths)
        if is_critical:
            found.add(full_path)
        records.append(
            {
                "search_method": method,
                "search_attempt": attempt,
                "path": path,
                "full_cascade_path": full_path,
                "is_critical": is_critical,
                "total_load_shed_mw": float(truth.get("total_load_shed_mw", 0.0)),
                "found_critical_count": len(found),
            }
        )
    return pd.DataFrame(records)


def _make_search_summary(curve_table: pd.DataFrame, total_critical_count: int) -> pd.DataFrame:
    records: list[dict] = []
    for method, group in curve_table.groupby("search_method"):
        full = group.loc[group["found_critical_count"] >= total_critical_count]
        attempts_to_find_all = int(full["search_attempt"].iloc[0]) if not full.empty else np.nan
        records.append(
            {
                "search_method": method,
                "total_critical_count": total_critical_count,
                "attempts_to_find_all": attempts_to_find_all,
                "found_after_50_attempts": int(group.loc[group["search_attempt"] <= 50, "found_critical_count"].max()),
                "found_after_100_attempts": int(group.loc[group["search_attempt"] <= 100, "found_critical_count"].max()),
                "found_after_200_attempts": int(group.loc[group["search_attempt"] <= 200, "found_critical_count"].max()),
                "found_after_500_attempts": int(group.loc[group["search_attempt"] <= 500, "found_critical_count"].max()),
            }
        )
    return pd.DataFrame(records).sort_values("attempts_to_find_all", na_position="last").reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评估论文式 GCN+y_P 在 RTS-79 N-2 搜索中的效率。")
    parser.add_argument("--model", required=True, help="论文式 GCN 模型 .pt 文件。")
    parser.add_argument("--normalizer", required=True, help="论文式 GCN 特征归一化 JSON 文件。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "paper_gcn_search_eval"), help="输出目录。")
    parser.add_argument("--seed", type=int, default=20260722, help="测试负荷场景随机种子。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--gcn-threshold", type=float, default=0.5, help="GCN 判为危险支路的概率阈值。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = SearchEvalConfig(
        seed=args.seed,
        beta=args.beta,
        security_limit=args.security_limit,
        gcn_threshold=args.gcn_threshold,
    )
    evaluate_search_methods(args.model, args.normalizer, args.output_dir, config)


if __name__ == "__main__":
    main()
