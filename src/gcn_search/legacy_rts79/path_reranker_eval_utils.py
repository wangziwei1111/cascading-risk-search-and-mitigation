from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_path_reranker_dataset import (
    PathRerankerDatasetConfig,
    _line_abs_flow,
    _line_loading_ratio,
    _make_lodf_score_lookup,
    _max_loading_ratio,
    _num_overloaded,
    _rank_lookup,
)
from evaluate_pio_gcn_ensemble_ranking import _make_score_table
from evaluate_pio_gcn_hard_negative_rerank import WEIGHTS
from evaluate_rts79_paper_gcn_search import _load_gcn_model, _predict_gcn_shed_probability
from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _load_model as _load_pio_model, _make_full_truth, _make_path_order
from gcn_physics_constraints import make_candidate_mask
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf
from rts79_cascade_from_case import run_sequential_outages_from_case
from train_path_reranker import TrainPathRerankerConfig, _fit_model, _predict_table


DEFAULT_TOP_K = (20, 50, 100, 200)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_truth_from_case(root_case: dict, seed: int, config: PathRerankerDatasetConfig) -> pd.DataFrame:
    pio_config = PioTopkConfig(
        model=config.pio_model,
        normalizer=config.pio_normalizer,
        output_dir="",
        seed=seed,
        beta=config.beta,
        security_limit=config.security_limit,
        top_k=config.top_k,
        run_full_truth=True,
    )
    return _make_full_truth(root_case, pio_config)


def make_path_feature_table(root_case: dict, seed: int, truth: pd.DataFrame, config: PathRerankerDatasetConfig) -> pd.DataFrame:
    pio_model, pio_adjacency = _load_pio_model(config.pio_model)
    pio_normalizer = json.loads(Path(config.pio_normalizer).read_text(encoding="utf-8"))
    paper_model, paper_adjacency = _load_gcn_model(config.paper_model)
    paper_normalizer = json.loads(Path(config.paper_normalizer).read_text(encoding="utf-8"))
    score_table = _make_score_table(seed, config, pio_model, pio_adjacency, pio_normalizer, paper_model, paper_adjacency, paper_normalizer)
    return make_path_feature_table_from_scores(root_case, seed, truth, config, score_table)


def make_score_table_from_case(root_case: dict, seed: int, config: PathRerankerDatasetConfig) -> pd.DataFrame:
    pio_model, pio_adjacency = _load_pio_model(config.pio_model)
    pio_normalizer = json.loads(Path(config.pio_normalizer).read_text(encoding="utf-8"))
    paper_model, paper_adjacency = _load_gcn_model(config.paper_model)
    paper_normalizer = json.loads(Path(config.paper_normalizer).read_text(encoding="utf-8"))
    pio_order = _make_path_order(
        pio_model,
        pio_adjacency,
        pio_normalizer,
        root_case,
        PioTopkConfig(model=config.pio_model, normalizer=config.pio_normalizer, output_dir="", seed=seed, beta=config.beta, security_limit=config.security_limit, top_k=config.top_k),
    )
    pio_scores = {row["path"]: float(row["score"]) for row in pio_order}
    paper_scores = _make_paper_scores_from_case(root_case, config, paper_model, paper_adjacency, paper_normalizer)
    all_paths = sorted(set(pio_scores) | set(paper_scores))
    table = pd.DataFrame({"path": all_paths, "pio_score": [pio_scores.get(path, 0.0) for path in all_paths], "paper_score": [paper_scores.get(path, 0.0) for path in all_paths]})
    table["normalized_pio_score"] = minmax(table["pio_score"].to_numpy())
    table["normalized_paper_score"] = minmax(table["paper_score"].to_numpy())
    return table


def _make_paper_scores_from_case(root_case: dict, config: PathRerankerDatasetConfig, model, adjacency, normalizer: dict) -> dict[str, float]:
    first_probability = _predict_gcn_shed_probability(model, adjacency, normalizer, root_case, config.beta)
    first_mask = make_candidate_mask(root_case)
    scores: dict[str, float] = {}
    for first_idx in np.where(first_mask)[0]:
        first_line = f"L{first_idx + 1:02d}"
        state = run_sequential_outages_from_case(root_case, [first_line], beta=config.beta, security_limit=config.security_limit)
        second_probability = _predict_gcn_shed_probability(model, adjacency, normalizer, state["case"], config.beta)
        second_mask = make_candidate_mask(state["case"], used_lines=[first_line])
        for second_idx in np.where(second_mask)[0]:
            second_line = f"L{second_idx + 1:02d}"
            scores[f"{first_line}->{second_line}"] = float(first_probability[first_idx] * second_probability[second_idx])
    return scores


def make_path_feature_table_from_scores(root_case: dict, seed: int, truth: pd.DataFrame, config: PathRerankerDatasetConfig, score_table: pd.DataFrame) -> pd.DataFrame:
    score_by_path = score_table.set_index("path").to_dict(orient="index")
    pio_rank = _rank_lookup(score_table, "pio_score")
    paper_rank = _rank_lookup(score_table, "paper_score")
    lodf_score = _make_lodf_score_lookup(root_case, config)
    lodf_rank = _rank_lookup(pd.DataFrame({"path": list(lodf_score), "lodf_score": list(lodf_score.values())}), "lodf_score")
    rows: list[dict] = []
    first_state_cache: dict[str, dict] = {}
    for _, item in truth.iterrows():
        path = str(item["path"])
        first, second = path.split("->")
        if first not in first_state_cache:
            first_state_cache[first] = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        first_state = first_state_cache[first]
        score_row = score_by_path.get(path, {})
        first_loading = _line_loading_ratio(root_case, first)
        second_loading = _line_loading_ratio(first_state["case"], second)
        first_outage_max_loading = _max_loading_ratio(first_state["case"])
        max_loading = float(max(first_loading, second_loading, first_outage_max_loading))
        rows.append(
            {
                "seed": int(seed),
                "first_line": first,
                "second_line": second,
                "path": path,
                "is_critical": int(bool(item["critical"])),
                "total_load_shed_mw": float(item.get("total_load_shed_mw", 0.0)),
                "rank_in_pio": int(pio_rank.get(path, 999999)),
                "rank_in_paper": int(paper_rank.get(path, 999999)),
                "rank_in_lodf": int(lodf_rank.get(path, 999999)),
                "pio_score": float(score_row.get("pio_score", 0.0)),
                "paper_score": float(score_row.get("paper_score", 0.0)),
                "lodf_score": float(lodf_score.get(path, 0.0)),
                "ensemble_score_alpha_0_75": 0.75 * float(score_row.get("normalized_pio_score", 0.0)) + 0.25 * float(score_row.get("normalized_paper_score", 0.0)),
                "first_line_loading_ratio": first_loading,
                "second_line_loading_ratio": second_loading,
                "max_loading_ratio": max_loading,
                "min_security_margin": float(config.security_limit - max_loading),
                "min_relay_margin": float(config.beta - max_loading),
                "first_line_abs_flow": _line_abs_flow(root_case, first),
                "second_line_abs_flow": _line_abs_flow(first_state["case"], second),
                "first_outage_num_overloaded_lines": _num_overloaded(first_state["case"], config.security_limit),
                "first_outage_max_loading_ratio": first_outage_max_loading,
                "first_outage_total_load_shed_mw": float(first_state.get("island_load_shed_mw", 0.0)) + float(first_state.get("redispatch_load_shed_mw", 0.0)),
                "candidate_position_min_rank": min(int(pio_rank.get(path, 999999)), int(paper_rank.get(path, 999999)), int(lodf_rank.get(path, 999999))),
                "y_critical": int(bool(item["critical"])),
                "y_load_shed": float(item.get("total_load_shed_mw", 0.0)),
            }
        )
    return pd.DataFrame(rows)


def train_reranker_models(train_dataset_dir: str | Path, epochs: int = 80) -> dict[str, tuple[object, dict]]:
    train = pd.concat([pd.read_csv(Path(train_dataset_dir) / name) for name in ["path_reranker_train.csv", "path_reranker_val.csv", "path_reranker_test.csv"]], ignore_index=True)
    config = TrainPathRerankerConfig(epochs=epochs, lambda_pairwise_rank=0.05)
    return {
        "learned_logistic_reranker_external": _fit_model(train, config, "logistic"),
        "learned_mlp_reranker_external": _fit_model(train, config, "mlp"),
    }


def make_orders(dataset: pd.DataFrame, models: dict[str, tuple[object, dict]], suffix: str = "external") -> dict[str, list[str]]:
    orders = {
        "PIO_GCN": dataset.sort_values(["pio_score", "path"], ascending=[False, True])["path"].tolist(),
        "paper_GCN_path_prob_strong": dataset.sort_values(["paper_score", "path"], ascending=[False, True])["path"].tolist(),
        "LODF_yP": dataset.sort_values(["lodf_score", "path"], ascending=[False, True])["path"].tolist(),
        "rerank_physical_stress": _physical_stress_order(dataset),
        "oracle": dataset.sort_values(["y_critical", "total_load_shed_mw", "path"], ascending=[False, False, True])["path"].tolist(),
    }
    for method, (model, normalizer) in models.items():
        model_type = "mlp" if "mlp" in method else "logistic"
        pred = _predict_table(model, normalizer, dataset, model_type, int(dataset["seed"].iloc[0]))
        name = method if method.endswith(suffix) else f"{method}_{suffix}"
        orders[name] = pred.sort_values(["learned_score", "path"], ascending=[False, True])["path"].tolist()
    return orders


def _physical_stress_order(dataset: pd.DataFrame) -> list[str]:
    work = dataset.copy()
    weights = WEIGHTS["rerank_physical_stress"]
    work["normalized_pio_score"] = minmax(work["pio_score"].to_numpy())
    work["normalized_lodf_score"] = minmax(work["lodf_score"].to_numpy())
    work["normalized_loading_stress"] = minmax(work["max_loading_ratio"].to_numpy())
    work["normalized_relay_risk"] = minmax(np.maximum(0.0, -work["min_relay_margin"].to_numpy(dtype=float)))
    work["physical_stress_score"] = (
        weights["pio"] * work["normalized_pio_score"]
        + weights["lodf"] * work["normalized_lodf_score"]
        + weights["loading"] * work["normalized_loading_stress"]
        + weights["relay"] * work["normalized_relay_risk"]
    )
    return work.sort_values(["physical_stress_score", "path"], ascending=[False, True])["path"].tolist()


def evaluate_orders(seed: int, truth: pd.DataFrame, orders: dict[str, list[str]], top_k: tuple[int, ...], notes: dict[str, str] | None = None) -> pd.DataFrame:
    truth_by_path = truth.set_index("path")["critical"].astype(bool).to_dict()
    total = int(truth["critical"].sum())
    rows: list[dict] = []
    for method, order in orders.items():
        for k in top_k:
            subset = order[:k]
            found = sum(bool(truth_by_path.get(path, False)) for path in subset)
            rows.append(
                {
                    "seed": int(seed),
                    "method": method,
                    "top_k": int(k),
                    "critical_found": int(found),
                    "critical_path_recall": float(found / max(total, 1)),
                    "notes": (notes or {}).get(method, ""),
                }
            )
    return pd.DataFrame(rows)


def aggregate(per_seed: pd.DataFrame) -> pd.DataFrame:
    return (
        per_seed.groupby(["method", "top_k"], sort=False)
        .agg(
            num_test_seeds=("seed", "nunique"),
            mean_found=("critical_found", "mean"),
            std_found=("critical_found", lambda x: x.std(ddof=0)),
            mean_recall=("critical_path_recall", "mean"),
            std_recall=("critical_path_recall", lambda x: x.std(ddof=0)),
            notes=("notes", "first"),
        )
        .reset_index()
    )


def rank_shift_diagnostics(seed: int, dataset: pd.DataFrame, orders: dict[str, list[str]], base_method: str = "PIO_GCN") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    critical = dataset[dataset["y_critical"] == 1].copy()
    base_rank = {path: rank for rank, path in enumerate(orders.get(base_method, []), start=1)}
    rank_rows: list[dict] = []
    missed: list[dict] = []
    rescued: list[dict] = []
    for method, order in orders.items():
        rank = {path: r for r, path in enumerate(order, start=1)}
        for _, item in critical.iterrows():
            path = str(item["path"])
            method_rank = int(rank.get(path, 999999))
            pio_rank = int(base_rank.get(path, 999999))
            row = {"seed": int(seed), "method": method, "path": path, "rank": method_rank, "pio_rank": pio_rank, "rank_shift_pio_minus_method": pio_rank - method_rank}
            rank_rows.append(row)
            if method_rank > 200:
                missed.append(row)
            if method_rank <= 200 and pio_rank > 200:
                rescued.append(row)
    return pd.DataFrame(rank_rows), pd.DataFrame(missed), pd.DataFrame(rescued)


def minmax(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return values
    lo = float(np.nanmin(values))
    hi = float(np.nanmax(values))
    if hi - lo < 1e-12:
        return np.zeros_like(values, dtype=float)
    return (values - lo) / (hi - lo)


def plot_recall_bar(comparison: pd.DataFrame, path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=160)
    ax.bar(top["method"].astype(str), top["mean_recall"].astype(float))
    ax.set_ylabel("Mean recall")
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_topk_curve(comparison: pd.DataFrame, path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 4.5), dpi=160)
    for method, group in comparison.groupby("method", sort=False):
        group = group.sort_values("top_k")
        ax.plot(group["top_k"], group["mean_recall"], marker="o", label=method)
    ax.set_xlabel("Top-K")
    ax.set_ylabel("Mean recall")
    ax.set_title(title)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def dataclass_payload(config: object) -> dict[str, Any]:
    payload = asdict(config)
    return {key: list(value) if isinstance(value, tuple) else value for key, value in payload.items()}
