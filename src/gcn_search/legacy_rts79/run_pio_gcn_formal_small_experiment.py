from __future__ import annotations

import argparse
import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_rts79_paper_gcn_search import (
    SearchEvalConfig,
    _load_gcn_model,
    _make_gcn_path_probability_order,
    _make_line_order,
    _make_lodf_order,
    _make_random_order,
)
from evaluate_rts79_pio_gcn_topk import PioTopkConfig, evaluate_pio_gcn_topk
from generate_rts79_step2_state_dataset import Step2StateDatasetConfig, generate_step2_state_dataset
from rts79_cascade import Rts79InitialConfig
from train_rts79_physics_gcn import PhysicsGcnRunConfig, train_physics_gcn


@dataclass(frozen=True)
class FormalSmallExperimentConfig:
    output_dir: str
    training_num_scenarios: int = 50
    training_first_seed: int = 20260750
    training_epochs: int = 10
    training_max_active_depth: int = 1
    test_seed_start: int = 20260722
    test_num_seeds: int = 5
    top_k: tuple[int, ...] = (20, 50, 100)
    beta: float = 1.2
    security_limit: float = 1.0
    skip_training_if_exists: bool = False
    paper_baseline_model: str | None = None
    paper_baseline_normalizer: str | None = None
    candidate_line_filter_mode: str = "all"
    max_first_lines: int | None = None


def run_formal_small_experiment(config: FormalSmallExperimentConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")

    paths = _prepare_training_artifacts(config, out)
    per_truth_rows: list[dict] = []
    pio_rows: list[dict] = []
    baseline_rows: list[dict] = []

    for offset in range(config.test_num_seeds):
        seed = config.test_seed_start + offset
        seed_dir = out / "seeds" / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        pio_dir = seed_dir / "pio_topk_full_truth"
        pio_start = time.time()
        evaluate_pio_gcn_topk(
            PioTopkConfig(
                model=str(paths["physics_model"]),
                normalizer=str(paths["physics_normalizer"]),
                output_dir=str(pio_dir),
                seed=seed,
                beta=config.beta,
                security_limit=config.security_limit,
                top_k=config.top_k,
                run_full_truth=True,
            )
        )
        pio_runtime = time.time() - pio_start
        truth = pd.read_csv(pio_dir / "pio_gcn_topk_full_truth.csv")
        order = pd.read_csv(pio_dir / "pio_gcn_topk_order.csv")
        simulation = pd.read_csv(pio_dir / "pio_gcn_topk_simulation_results.csv")
        pio_summary = pd.read_csv(pio_dir / "pio_gcn_topk_summary.csv")
        total_critical = int(truth["critical"].sum())
        per_truth_rows.append(
            {
                "seed": seed,
                "num_ordered_n2_paths": int(len(truth)),
                "total_critical_paths": total_critical,
                "full_truth": True,
                "truth_path": str(pio_dir / "pio_gcn_topk_full_truth.csv"),
            }
        )
        for _, row in pio_summary.iterrows():
            top_k = int(row["top_k"])
            subset = simulation.head(top_k)
            pio_rows.append(
                {
                    "seed": seed,
                    "top_k": top_k,
                    "total_critical_paths": total_critical,
                    "critical_found": int(row["num_critical_found"]),
                    "critical_path_recall": float(row["critical_path_recall"]),
                    "total_load_shed_found_mw": float(subset.loc[subset["critical"], "total_load_shed_mw"].sum()) if not subset.empty else 0.0,
                    "runtime_seconds": float(pio_runtime),
                    "notes": "physics-informed model; formal small experiment full truth",
                }
            )
        baseline_rows.extend(_evaluate_baselines_for_seed(seed, truth, config, paths, seed_dir))
        _write_seed_diagnostics(seed, truth, order, simulation, out / "diagnostics")

    per_truth = pd.DataFrame(per_truth_rows)
    pio_per_seed = pd.DataFrame(pio_rows)
    baseline_per_seed = pd.DataFrame(baseline_rows)
    per_truth.to_csv(out / "per_seed_full_truth_summary.csv", index=False, encoding="utf-8-sig")
    pio_per_seed.to_csv(out / "pio_topk_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    baseline_per_seed.to_csv(out / "baseline_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    aggregate_topk = _make_aggregate_topk_summary(pio_per_seed)
    aggregate_method = _make_aggregate_method_comparison(pio_per_seed, baseline_per_seed)
    aggregate_topk.to_csv(out / "aggregate_topk_summary.csv", index=False, encoding="utf-8-sig")
    aggregate_method.to_csv(out / "aggregate_method_comparison.csv", index=False, encoding="utf-8-sig")
    _plot_outputs(aggregate_topk, aggregate_method, out / "figures")
    return {
        "output_dir": str(out),
        "aggregate_topk_summary": str(out / "aggregate_topk_summary.csv"),
        "aggregate_method_comparison": str(out / "aggregate_method_comparison.csv"),
    }


def _prepare_training_artifacts(config: FormalSmallExperimentConfig, out: Path) -> dict[str, Path]:
    physics_dataset_dir = out / "training" / "physics_dataset"
    physics_train_dir = out / "training" / "physics_informed"
    physics_ce_train_dir = out / "training" / "physics_ce_only"
    physics_dataset = physics_dataset_dir / "rts79_step2_state_dataset_physics.npz"
    if not (config.skip_training_if_exists and physics_dataset.exists()):
        generate_step2_state_dataset(
            Step2StateDatasetConfig(
                num_scenarios=config.training_num_scenarios,
                first_seed=config.training_first_seed,
                relay_threshold_beta=config.beta,
                security_limit=config.security_limit,
                max_active_depth=config.training_max_active_depth,
                feature_mode="physics",
                candidate_line_filter_mode=config.candidate_line_filter_mode,
                max_first_lines=config.max_first_lines,
            ),
            physics_dataset_dir,
        )
    if not (config.skip_training_if_exists and (physics_train_dir / "rts79_physics_gcn_model.pt").exists()):
        train_physics_gcn(
            PhysicsGcnRunConfig(
                dataset_npz=str(physics_dataset),
                output_dir=str(physics_train_dir),
                epochs=config.training_epochs,
                lambda_mask=0.1,
                lambda_relay=0.1,
                lambda_monotonic=0.1,
                beta=config.beta,
                security_limit=config.security_limit,
            )
        )
    if not (config.skip_training_if_exists and (physics_ce_train_dir / "rts79_physics_gcn_model.pt").exists()):
        train_physics_gcn(
            PhysicsGcnRunConfig(
                dataset_npz=str(physics_dataset),
                output_dir=str(physics_ce_train_dir),
                epochs=config.training_epochs,
                lambda_mask=0.0,
                lambda_relay=0.0,
                lambda_monotonic=0.0,
                beta=config.beta,
                security_limit=config.security_limit,
            )
        )
    _copy_if_exists(physics_dataset_dir / "rts79_step2_state_dataset_stats_physics.json", out / "training_dataset_stats.json")
    _copy_if_exists(physics_train_dir / "rts79_physics_gcn_metrics.csv", out / "physics_training_metrics.csv")
    _copy_if_exists(physics_ce_train_dir / "rts79_physics_gcn_metrics.csv", out / "physics_ce_training_metrics.csv")
    paper_model, paper_normalizer = _resolve_paper_baseline(config)
    return {
        "physics_model": physics_train_dir / "rts79_physics_gcn_model.pt",
        "physics_normalizer": physics_dataset_dir / "rts79_step2_state_feature_normalizer_physics.json",
        "paper_model": paper_model,
        "paper_normalizer": paper_normalizer,
    }


def _resolve_paper_baseline(config: FormalSmallExperimentConfig) -> tuple[Path | None, Path | None]:
    default_model = Path("results/gcn_search/pio_validation_round2/paper_train_ce_only/rts79_physics_gcn_model.pt")
    default_normalizer = Path("results/gcn_search/pio_validation_round2/paper_dataset/rts79_step2_state_feature_normalizer.json")
    model = Path(config.paper_baseline_model) if config.paper_baseline_model else default_model
    normalizer = Path(config.paper_baseline_normalizer) if config.paper_baseline_normalizer else default_normalizer
    if not model.exists() or not normalizer.exists():
        return None, None
    return model, normalizer


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copyfile(src, dst)


def _write_seed_diagnostics(seed: int, truth: pd.DataFrame, order: pd.DataFrame, simulation: pd.DataFrame, diagnostics_dir: Path) -> None:
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    order = order.copy()
    truth = truth.copy()
    simulation = simulation.copy()
    order["seed"] = seed
    truth["seed"] = seed
    simulation["seed"] = seed
    _append_csv(order[["seed", "rank", "path", "score", "first_probability", "second_probability"]], diagnostics_dir / "topk_score_distribution.csv")
    _append_csv(
        pd.DataFrame(
            [
                {
                    "seed": seed,
                    "num_ordered_paths": int(len(order)),
                    "num_candidate_paths_scored": int(order["path"].nunique()),
                    "num_simulated_topk_paths": int(len(simulation)),
                }
            ]
        ),
        diagnostics_dir / "per_seed_candidate_count.csv",
    )
    rank_by_path = order.set_index("path")["rank"].to_dict()
    score_by_path = order.set_index("path")["score"].to_dict()
    top100_paths = set(order.sort_values("rank").head(100)["path"].astype(str))
    critical = truth.loc[truth["critical"]].copy()
    found = critical.loc[critical["path"].astype(str).isin(top100_paths)].copy()
    missed = critical.loc[~critical["path"].astype(str).isin(top100_paths)].copy()
    for table in (found, missed):
        table["rank"] = table["path"].map(rank_by_path)
        table["score"] = table["path"].map(score_by_path)
        table["ranked_after_100"] = table["rank"].fillna(10**9).astype(float) > 100
    keep = ["seed", "path", "total_load_shed_mw", "rank", "score", "ranked_after_100"]
    _append_csv(found[keep], diagnostics_dir / "found_critical_paths.csv")
    _append_csv(missed[keep], diagnostics_dir / "missed_critical_paths.csv")


def _append_csv(table: pd.DataFrame, path: Path) -> None:
    if path.exists():
        old = pd.read_csv(path)
        table = pd.concat([old, table], ignore_index=True)
    table.to_csv(path, index=False, encoding="utf-8-sig")


def _evaluate_baselines_for_seed(seed: int, truth: pd.DataFrame, config: FormalSmallExperimentConfig, paths: dict[str, Path], seed_dir: Path) -> list[dict]:
    rows = []
    truth = truth.copy()
    truth["path"] = truth["path"].astype(str)
    truth_by_path = truth.set_index("path").to_dict(orient="index")
    total_critical = int(truth["critical"].sum())
    search_config = SearchEvalConfig(seed=seed, beta=config.beta, security_limit=config.security_limit, random_seed=seed)
    initial_config = Rts79InitialConfig(random_seed=seed)
    order_builders = {
        "LODF_yP": lambda: _make_lodf_order(initial_config, search_config),
        "random": lambda: _make_random_order(seed),
        "line_order": _make_line_order,
        "oracle": lambda: truth.sort_values(["critical", "total_load_shed_mw"], ascending=[False, False])["path"].tolist(),
    }
    if paths["paper_model"] is not None and paths["paper_normalizer"] is not None:
        paper_model, paper_adjacency = _load_gcn_model(paths["paper_model"])
        paper_normalizer = json.loads(paths["paper_normalizer"].read_text(encoding="utf-8"))
        paper_method = "paper_GCN_path_prob_strong" if config.paper_baseline_model else "original_GCN_path_prob"
        order_builders = {
            paper_method: lambda: _make_gcn_path_probability_order(paper_model, paper_adjacency, paper_normalizer, initial_config, search_config),
            **order_builders,
        }
    for method, builder in order_builders.items():
        start = time.time()
        ordered_paths = list(builder())
        summary = _summarize_order(method, seed, ordered_paths, truth_by_path, total_critical, time.time() - start, config.top_k)
        summary["notes"] = _baseline_notes(method)
        rows.append(summary)
    pd.DataFrame(rows).to_csv(seed_dir / "baseline_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    return rows


def _summarize_order(method: str, seed: int, ordered_paths: list[str], truth_by_path: dict, total_critical: int, runtime: float, top_k_values: tuple[int, ...] = (20, 50, 100)) -> dict:
    found: set[str] = set()
    attempts_to_find_all = np.nan
    found_after = {int(k): 0 for k in top_k_values}
    for attempt, path in enumerate(ordered_paths, start=1):
        truth = truth_by_path.get(path)
        if truth and bool(truth.get("critical", False)):
            found.add(path)
        for k in found_after:
            if attempt <= k:
                found_after[k] = len(found)
        if total_critical and len(found) >= total_critical and np.isnan(attempts_to_find_all):
            attempts_to_find_all = attempt
            break
    return {
        "seed": seed,
        "method": method,
        "attempts_to_find_all": attempts_to_find_all,
        **{f"found_after_{k}": int(found_after[k]) for k in found_after},
        **{f"recall_at_{k}": float(found_after[k] / max(total_critical, 1)) for k in found_after},
        "total_critical_paths": total_critical,
        "runtime_seconds": float(runtime),
    }


def _baseline_notes(method: str) -> str:
    if method == "oracle":
        return "upper bound only; not a deployable search method"
    if method == "paper_GCN_path_prob_strong":
        return "paper-feature GCN_path_prob trained with the strong baseline configuration"
    if method == "original_GCN_path_prob":
        return "weak paper-feature model trained inside this small experiment; preliminary result"
    if method == "LODF_yP":
        return "physical-rule ranking baseline"
    if method == "random":
        return "fixed random seed per test seed"
    return "line-number order baseline"


def _make_aggregate_topk_summary(pio: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for top_k, group in pio.groupby("top_k", sort=True):
        rows.append(
            {
                "method": f"PIO_GCN_Top{int(top_k)}",
                "top_k": int(top_k),
                "num_test_seeds": int(group["seed"].nunique()),
                "mean_total_critical_paths": float(group["total_critical_paths"].mean()),
                "mean_critical_found": float(group["critical_found"].mean()),
                "std_critical_found": float(group["critical_found"].std(ddof=0)),
                "mean_critical_path_recall": float(group["critical_path_recall"].mean()),
                "std_critical_path_recall": float(group["critical_path_recall"].std(ddof=0)),
                "mean_total_load_shed_found_mw": float(group["total_load_shed_found_mw"].mean()),
                "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
                "notes": "full ordered N-2 truth; formal small RTS-79 experiment",
            }
        )
    return pd.DataFrame(rows)


def _make_aggregate_method_comparison(pio: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in _make_aggregate_topk_summary(pio).iterrows():
        rows.append(
            {
                "method": row["method"],
                "num_test_seeds": row["num_test_seeds"],
                "mean_total_critical_paths": row["mean_total_critical_paths"],
                **{f"mean_found_after_{int(row['top_k'])}": row["mean_critical_found"]},
                **{f"std_found_after_{int(row['top_k'])}": row["std_critical_found"]},
                "mean_attempts_to_find_all": "",
                "std_attempts_to_find_all": "",
                **{f"mean_recall_at_{int(row['top_k'])}": row["mean_critical_path_recall"]},
                **{f"std_recall_at_{int(row['top_k'])}": row["std_critical_path_recall"]},
                "mean_runtime_seconds": row["mean_runtime_seconds"],
                "std_runtime_seconds": "",
                "notes": row["notes"],
            }
        )
    for method, group in baseline.groupby("method", sort=False):
        row = {
            "method": method,
            "num_test_seeds": int(group["seed"].nunique()),
            "mean_total_critical_paths": float(group["total_critical_paths"].mean()),
            "mean_attempts_to_find_all": float(pd.to_numeric(group["attempts_to_find_all"], errors="coerce").mean()),
            "std_attempts_to_find_all": float(pd.to_numeric(group["attempts_to_find_all"], errors="coerce").std(ddof=0)),
            "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
            "std_runtime_seconds": float(group["runtime_seconds"].std(ddof=0)),
            "notes": str(group["notes"].iloc[0]),
        }
        for col in sorted([c for c in group.columns if c.startswith("found_after_")], key=lambda name: int(name.rsplit("_", 1)[1])):
            k = col.rsplit("_", 1)[1]
            row[f"mean_found_after_{k}"] = float(group[col].mean())
            row[f"std_found_after_{k}"] = float(group[col].std(ddof=0))
        for col in sorted([c for c in group.columns if c.startswith("recall_at_")], key=lambda name: int(name.rsplit("_", 1)[1])):
            k = col.rsplit("_", 1)[1]
            row[f"mean_recall_at_{k}"] = float(group[col].mean())
            row[f"std_recall_at_{k}"] = float(group[col].std(ddof=0))
        rows.append(
            row
        )
    return pd.DataFrame(rows)


def _plot_outputs(topk: pd.DataFrame, comparison: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    _simple_bar(topk["method"], topk["mean_critical_path_recall"], "Top-K Recall", "Mean critical path recall", figure_dir / "topk_recall_bar.png")
    found = comparison[["method", "mean_found_after_20", "mean_found_after_50", "mean_found_after_100"]].copy()
    found = found.fillna("").replace("", np.nan)
    labels = found["method"].tolist()
    x = np.arange(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9.5, 4.8), dpi=160)
    for offset, col in enumerate(["mean_found_after_20", "mean_found_after_50", "mean_found_after_100"]):
        ax.bar(x + (offset - 1) * width, pd.to_numeric(found[col], errors="coerce").fillna(0.0), width, label=col.replace("mean_", ""))
    ax.set_title("Critical Paths Found After K Attempts")
    ax.set_ylabel("Mean critical paths found")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_dir / "found_after_k_comparison.png")
    plt.close(fig)
    _simple_bar(comparison["method"], comparison["mean_runtime_seconds"], "Runtime Comparison", "Mean runtime (seconds)", figure_dir / "runtime_comparison.png")


def _simple_bar(labels, values, title: str, ylabel: str, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.0, 4.4), dpi=160)
    label_list = [str(label) for label in labels]
    x = np.arange(len(label_list))
    bars = ax.bar(x, [float(value) for value in values], color="#1f77b4")
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(label_list, rotation=25, ha="right")
    ax.bar_label(bars, fmt="%.3g", padding=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a formal small RTS-79 PIO-GCN experiment.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--training-num-scenarios", type=int, default=50)
    parser.add_argument("--training-first-seed", type=int, default=20260750)
    parser.add_argument("--training-epochs", type=int, default=10)
    parser.add_argument("--training-max-active-depth", type=int, default=1)
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=5)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100])
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--skip-training-if-exists", action="store_true")
    parser.add_argument("--paper-baseline-model")
    parser.add_argument("--paper-baseline-normalizer")
    parser.add_argument("--candidate-line-filter-mode", choices=["all", "first_n", "high_flow_top_n"], default="all")
    parser.add_argument("--max-first-lines", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_formal_small_experiment(
        FormalSmallExperimentConfig(
            output_dir=args.output_dir,
            training_num_scenarios=args.training_num_scenarios,
            training_first_seed=args.training_first_seed,
            training_epochs=args.training_epochs,
            training_max_active_depth=args.training_max_active_depth,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            beta=args.beta,
            security_limit=args.security_limit,
            skip_training_if_exists=args.skip_training_if_exists,
            paper_baseline_model=args.paper_baseline_model,
            paper_baseline_normalizer=args.paper_baseline_normalizer,
            candidate_line_filter_mode=args.candidate_line_filter_mode,
            max_first_lines=args.max_first_lines,
        )
    )


if __name__ == "__main__":
    main()
