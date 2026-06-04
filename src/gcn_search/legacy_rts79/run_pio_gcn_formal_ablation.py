from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_rts79_paper_gcn_search import (
    SearchEvalConfig,
    _load_gcn_model as _load_paper_model,
    _make_gcn_path_probability_order,
    _make_line_order,
    _make_lodf_order,
    _make_random_order,
)
from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _load_model as _load_physics_model, _make_path_order
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf
from run_pio_gcn_formal_small_experiment import FormalSmallExperimentConfig, run_formal_small_experiment


@dataclass(frozen=True)
class FormalAblationConfig:
    output_dir: str
    base_experiment_dir: str
    test_seed_start: int = 20260722
    test_num_seeds: int = 3
    top_k: tuple[int, ...] = (20, 50, 100)
    beta: float = 1.2
    security_limit: float = 1.0


def run_formal_ablation(config: FormalAblationConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    diagnostics_dir = out / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    base = Path(config.base_experiment_dir)
    _ensure_base_artifacts(base, config)
    artifact_paths = _artifact_paths(base)
    training_config = _read_training_config(base, artifact_paths)
    (out / "config.json").write_text(
        json.dumps({**asdict(config), "training_config": training_config}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    model_cache = _load_ablation_models(artifact_paths)
    per_seed_rows: list[dict] = []
    score_rows: list[pd.DataFrame] = []
    found_rows: list[pd.DataFrame] = []
    missed_rows: list[pd.DataFrame] = []
    rank_rows: list[pd.DataFrame] = []

    for offset in range(config.test_num_seeds):
        seed = config.test_seed_start + offset
        truth = _load_and_validate_truth(base, seed, config)
        root_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        method_orders = _make_method_orders(seed, root_case, truth, config, model_cache, artifact_paths)
        total_critical = int(truth["critical"].sum())
        for method, order_table in method_orders.items():
            started = time.time()
            order_table = order_table.copy()
            order_table["rank"] = np.arange(1, len(order_table) + 1)
            runtime_seconds = float(time.time() - started + float(order_table.attrs.get("runtime_seconds", 0.0)))
            rows = _summarize_method(seed, method, order_table, truth, total_critical, runtime_seconds, config.top_k)
            per_seed_rows.extend(rows)
            score_rows.append(_score_distribution(seed, method, order_table))
            found, missed, ranks = _critical_rank_diagnostics(seed, method, order_table, truth)
            found_rows.append(found)
            missed_rows.append(missed)
            rank_rows.append(ranks)

    per_seed = pd.DataFrame(per_seed_rows)
    aggregate = _make_aggregate_summary(per_seed)
    comparison = _make_method_comparison(per_seed)
    per_seed.to_csv(out / "ablation_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    aggregate.to_csv(out / "ablation_aggregate_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(out / "ablation_method_comparison.csv", index=False, encoding="utf-8-sig")
    pd.concat(score_rows, ignore_index=True).to_csv(diagnostics_dir / "per_method_score_distribution.csv", index=False, encoding="utf-8-sig")
    pd.concat(found_rows, ignore_index=True).to_csv(diagnostics_dir / "per_method_top100_found_critical.csv", index=False, encoding="utf-8-sig")
    pd.concat(missed_rows, ignore_index=True).to_csv(diagnostics_dir / "per_method_top100_missed_critical.csv", index=False, encoding="utf-8-sig")
    pd.concat(rank_rows, ignore_index=True).to_csv(diagnostics_dir / "per_method_rank_of_critical_paths.csv", index=False, encoding="utf-8-sig")
    _plot_ablation_outputs(aggregate, comparison, out / "figures")
    return {"output_dir": str(out), "aggregate": str(out / "ablation_aggregate_summary.csv")}


def _artifact_paths(base: Path) -> dict[str, Path]:
    return {
        "physics_informed_model": base / "training" / "physics_informed" / "rts79_physics_gcn_model.pt",
        "physics_ce_model": base / "training" / "physics_ce_only" / "rts79_physics_gcn_model.pt",
        "physics_normalizer": base / "training" / "physics_dataset" / "rts79_step2_state_feature_normalizer_physics.json",
        "paper_model": Path("results/gcn_search/pio_validation_round2/paper_train_ce_only/rts79_physics_gcn_model.pt"),
        "paper_normalizer": Path("results/gcn_search/pio_validation_round2/paper_dataset/rts79_step2_state_feature_normalizer.json"),
    }


def _ensure_base_artifacts(base: Path, config: FormalAblationConfig) -> None:
    paths = _artifact_paths(base)
    required = [paths["physics_informed_model"], paths["physics_ce_model"], paths["physics_normalizer"]]
    if all(path.exists() for path in required):
        return
    run_formal_small_experiment(
        FormalSmallExperimentConfig(
            output_dir=str(base),
            training_num_scenarios=10,
            training_epochs=5,
            training_max_active_depth=1,
            candidate_line_filter_mode="high_flow_top_n",
            max_first_lines=10,
            test_seed_start=config.test_seed_start,
            test_num_seeds=config.test_num_seeds,
            top_k=config.top_k,
            beta=config.beta,
            security_limit=config.security_limit,
            skip_training_if_exists=True,
        )
    )


def _read_training_config(base: Path, paths: dict[str, Path]) -> dict:
    dataset_stats = json.loads((base / "training_dataset_stats.json").read_text(encoding="utf-8"))
    informed_config = json.loads((base / "training" / "physics_informed" / "rts79_physics_gcn_train_config.json").read_text(encoding="utf-8"))
    ce_config = json.loads((base / "training" / "physics_ce_only" / "rts79_physics_gcn_train_config.json").read_text(encoding="utf-8"))
    return {
        "training_num_scenarios": dataset_stats.get("num_scenarios"),
        "training_epochs": informed_config.get("epochs"),
        "training_max_active_depth": dataset_stats.get("max_active_depth"),
        "candidate_line_filter_mode": dataset_stats.get("candidate_line_filter_mode"),
        "max_first_lines": dataset_stats.get("max_first_lines"),
        "physics_informed_lambdas": {
            "lambda_mask": informed_config.get("lambda_mask"),
            "lambda_relay": informed_config.get("lambda_relay"),
            "lambda_monotonic": informed_config.get("lambda_monotonic"),
        },
        "physics_ce_lambdas": {
            "lambda_mask": ce_config.get("lambda_mask"),
            "lambda_relay": ce_config.get("lambda_relay"),
            "lambda_monotonic": ce_config.get("lambda_monotonic"),
        },
        "physics_informed_model": str(paths["physics_informed_model"]),
        "physics_ce_model": str(paths["physics_ce_model"]),
    }


def _load_ablation_models(paths: dict[str, Path]) -> dict:
    physics_informed = _load_physics_model(paths["physics_informed_model"])
    physics_ce = _load_physics_model(paths["physics_ce_model"])
    physics_normalizer = json.loads(paths["physics_normalizer"].read_text(encoding="utf-8"))
    paper = None
    if paths["paper_model"].exists() and paths["paper_normalizer"].exists():
        paper = (
            *_load_paper_model(paths["paper_model"]),
            json.loads(paths["paper_normalizer"].read_text(encoding="utf-8")),
        )
    return {
        "physics_informed": physics_informed,
        "physics_ce": physics_ce,
        "physics_normalizer": physics_normalizer,
        "paper": paper,
    }


def _load_and_validate_truth(base: Path, seed: int, config: FormalAblationConfig) -> pd.DataFrame:
    truth_path = base / "seeds" / f"seed_{seed}" / "pio_topk_full_truth" / "pio_gcn_topk_full_truth.csv"
    if not truth_path.exists():
        raise FileNotFoundError(f"Missing full truth for seed {seed}: {truth_path}")
    truth = pd.read_csv(truth_path)
    if len(truth) != 1406:
        raise ValueError(f"Expected 1406 ordered N-2 paths for seed {seed}, got {len(truth)}")
    summary_path = base / "per_seed_full_truth_summary.csv"
    if summary_path.exists():
        summary = pd.read_csv(summary_path)
        row = summary.loc[summary["seed"] == seed]
        if row.empty or int(row["total_critical_paths"].iloc[0]) != int(truth["critical"].sum()):
            raise ValueError(f"Full-truth summary mismatch for seed {seed}")
    config_path = base / "config.json"
    if config_path.exists():
        base_config = json.loads(config_path.read_text(encoding="utf-8"))
        if float(base_config.get("beta", config.beta)) != float(config.beta):
            raise ValueError("Base experiment beta does not match ablation beta.")
        if float(base_config.get("security_limit", config.security_limit)) != float(config.security_limit):
            raise ValueError("Base experiment security_limit does not match ablation security_limit.")
    return truth


def _make_method_orders(seed: int, root_case: dict, truth: pd.DataFrame, config: FormalAblationConfig, models: dict, paths: dict[str, Path]) -> dict[str, pd.DataFrame]:
    orders: dict[str, pd.DataFrame] = {}
    method_specs = {
        "physics_ce_no_mask": (models["physics_ce"], False),
        "physics_ce_mask": (models["physics_ce"], True),
        "physics_loss_no_mask": (models["physics_informed"], False),
        "physics_loss_mask": (models["physics_informed"], True),
    }
    for method, ((model, adjacency_powers), use_mask) in method_specs.items():
        started = time.time()
        rows = _make_path_order(
            model,
            adjacency_powers,
            models["physics_normalizer"],
            root_case,
            PioTopkConfig(
                model="",
                normalizer="",
                output_dir="",
                seed=seed,
                beta=config.beta,
                security_limit=config.security_limit,
                top_k=config.top_k,
                use_candidate_probability_mask=use_mask,
            ),
        )
        table = pd.DataFrame(rows)
        table.attrs["runtime_seconds"] = time.time() - started
        table["method_score"] = table["score"]
        orders[method] = table[["path", "method_score", "first_probability", "second_probability"]]
    if models["paper"] is not None:
        paper_model, paper_adjacency, paper_normalizer = models["paper"]
        started = time.time()
        paper_order = _make_gcn_path_probability_order(
            paper_model,
            paper_adjacency,
            paper_normalizer,
            Rts79InitialConfig(random_seed=seed),
            SearchEvalConfig(seed=seed, beta=config.beta, security_limit=config.security_limit, random_seed=seed),
        )
        orders["paper_gcn_path_prob"] = _order_to_table(paper_order, time.time() - started, note_score=False)
    started = time.time()
    orders["LODF_yP"] = _order_to_table(_make_lodf_order(Rts79InitialConfig(random_seed=seed), SearchEvalConfig(seed=seed, beta=config.beta, security_limit=config.security_limit)), time.time() - started)
    started = time.time()
    orders["random"] = _order_to_table(_make_random_order(seed), time.time() - started)
    started = time.time()
    orders["line_order"] = _order_to_table(_make_line_order(), time.time() - started)
    started = time.time()
    oracle_order = truth.sort_values(["critical", "total_load_shed_mw"], ascending=[False, False])["path"].astype(str).tolist()
    orders["oracle"] = _order_to_table(oracle_order, time.time() - started)
    return orders


def _order_to_table(order: list[str], runtime_seconds: float, note_score: bool = True) -> pd.DataFrame:
    table = pd.DataFrame({"path": order})
    table["method_score"] = -np.arange(1, len(table) + 1, dtype=float) if note_score else np.nan
    table["first_probability"] = np.nan
    table["second_probability"] = np.nan
    table.attrs["runtime_seconds"] = runtime_seconds
    return table


def _summarize_method(seed: int, method: str, order: pd.DataFrame, truth: pd.DataFrame, total_critical: int, runtime_seconds: float, top_k_values: tuple[int, ...]) -> list[dict]:
    truth_by_path = truth.set_index("path").to_dict(orient="index")
    rows = []
    for top_k in top_k_values:
        subset = order.head(top_k)
        critical_flags = [bool(truth_by_path.get(path, {}).get("critical", False)) for path in subset["path"]]
        found = int(sum(critical_flags))
        total_shed = sum(float(truth_by_path.get(path, {}).get("total_load_shed_mw", 0.0)) for path, is_critical in zip(subset["path"], critical_flags) if is_critical)
        rows.append(
            {
                "seed": seed,
                "method": method,
                "top_k": int(top_k),
                "total_critical_paths": total_critical,
                "critical_found": found,
                "critical_path_recall": float(found / max(total_critical, 1)),
                "total_load_shed_found_mw": float(total_shed),
                "runtime_seconds": runtime_seconds,
                "notes": _method_notes(method),
            }
        )
    return rows


def _method_notes(method: str) -> str:
    notes = {
        "physics_ce_no_mask": "physics features; CE-only; no candidate probability mask",
        "physics_ce_mask": "physics features; CE-only; candidate probability mask enabled",
        "physics_loss_no_mask": "physics features; physics-informed loss; no candidate probability mask",
        "physics_loss_mask": "physics features; physics-informed loss; candidate probability mask enabled",
        "paper_gcn_path_prob": "original paper 4-feature GCN_path_prob; weak paper model if trained from smoke data",
        "LODF_yP": "physical-rule ranking baseline",
        "random": "fixed random seed baseline",
        "line_order": "line-number order baseline",
        "oracle": "upper bound only; not deployable",
    }
    return notes.get(method, "")


def _score_distribution(seed: int, method: str, order: pd.DataFrame) -> pd.DataFrame:
    table = order.copy()
    table.insert(0, "seed", seed)
    table.insert(1, "method", method)
    return table[["seed", "method", "rank", "path", "method_score", "first_probability", "second_probability"]]


def _critical_rank_diagnostics(seed: int, method: str, order: pd.DataFrame, truth: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    rank_by_path = order.set_index("path")["rank"].to_dict()
    score_by_path = order.set_index("path")["method_score"].to_dict()
    critical = truth.loc[truth["critical"]].copy()
    critical["seed"] = seed
    critical["method"] = method
    critical["rank"] = critical["path"].map(rank_by_path)
    critical["method_score"] = critical["path"].map(score_by_path)
    critical["in_candidate_order"] = critical["rank"].notna()
    critical["ranked_after_100"] = critical["rank"].fillna(np.inf).astype(float) > 100
    keep = ["seed", "method", "path", "total_load_shed_mw", "rank", "method_score", "in_candidate_order", "ranked_after_100"]
    found = critical.loc[critical["rank"].fillna(np.inf).astype(float) <= 100, keep]
    missed = critical.loc[critical["rank"].fillna(np.inf).astype(float) > 100, keep]
    return found, missed, critical[keep]


def _make_aggregate_summary(per_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, top_k), group in per_seed.groupby(["method", "top_k"], sort=False):
        rows.append(
            {
                "method": method,
                "top_k": int(top_k),
                "num_test_seeds": int(group["seed"].nunique()),
                "mean_total_critical_paths": float(group["total_critical_paths"].mean()),
                "mean_critical_found": float(group["critical_found"].mean()),
                "std_critical_found": float(group["critical_found"].std(ddof=0)),
                "mean_critical_path_recall": float(group["critical_path_recall"].mean()),
                "std_critical_path_recall": float(group["critical_path_recall"].std(ddof=0)),
                "mean_total_load_shed_found_mw": float(group["total_load_shed_found_mw"].mean()),
                "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
                "notes": str(group["notes"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def _make_method_comparison(per_seed: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, group in per_seed.groupby("method", sort=False):
        by_top = group.set_index("top_k")
        rows.append(
            {
                "method": method,
                "num_test_seeds": int(group["seed"].nunique()),
                "mean_total_critical_paths": float(group["total_critical_paths"].mean()),
                "mean_found_after_20": _mean_for_top(group, 20, "critical_found"),
                "mean_found_after_50": _mean_for_top(group, 50, "critical_found"),
                "mean_found_after_100": _mean_for_top(group, 100, "critical_found"),
                "mean_recall_at_20": _mean_for_top(group, 20, "critical_path_recall"),
                "mean_recall_at_50": _mean_for_top(group, 50, "critical_path_recall"),
                "mean_recall_at_100": _mean_for_top(group, 100, "critical_path_recall"),
                "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
                "notes": str(group["notes"].iloc[0]),
            }
        )
    return pd.DataFrame(rows)


def _mean_for_top(group: pd.DataFrame, top_k: int, column: str) -> float:
    subset = group.loc[group["top_k"] == top_k, column]
    return float(subset.mean()) if not subset.empty else float("nan")


def _plot_ablation_outputs(aggregate: pd.DataFrame, comparison: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    top100 = aggregate.loc[aggregate["top_k"] == 100]
    _bar(top100["method"], top100["mean_critical_path_recall"], "Ablation Recall at Top-100", "Mean recall", figure_dir / "ablation_recall_at_100.png")
    found = comparison[["method", "mean_found_after_20", "mean_found_after_50", "mean_found_after_100"]].copy()
    labels = found["method"].tolist()
    x = np.arange(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(10.5, 5.0), dpi=160)
    for offset, col in enumerate(["mean_found_after_20", "mean_found_after_50", "mean_found_after_100"]):
        ax.bar(x + (offset - 1) * width, found[col], width, label=col.replace("mean_", ""))
    ax.set_title("Ablation Critical Paths Found")
    ax.set_ylabel("Mean critical paths found")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "ablation_found_after_k.png")
    plt.close(fig)
    _bar(comparison["method"], comparison["mean_runtime_seconds"], "Ablation Runtime", "Mean runtime (seconds)", figure_dir / "ablation_runtime.png")


def _bar(labels, values, title: str, ylabel: str, path: Path) -> None:
    label_list = [str(label) for label in labels]
    x = np.arange(len(label_list))
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
    bars = ax.bar(x, [float(value) for value in values], color="#1f77b4")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(label_list, rotation=30, ha="right")
    ax.bar_label(bars, fmt="%.3g", padding=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run formal preliminary PIO-GCN ablation on RTS-79.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--base-experiment-dir", required=True)
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=3)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100])
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_formal_ablation(
        FormalAblationConfig(
            output_dir=args.output_dir,
            base_experiment_dir=args.base_experiment_dir,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            beta=args.beta,
            security_limit=args.security_limit,
        )
    )


if __name__ == "__main__":
    main()
