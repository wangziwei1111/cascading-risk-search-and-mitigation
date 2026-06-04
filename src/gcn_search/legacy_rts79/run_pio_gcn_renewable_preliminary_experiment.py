from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _load_model, _make_full_truth, _make_path_order
from gcn_physics_constraints import make_candidate_mask
from renewable_scenarios import RenewableScenarioConfig, apply_renewable_scenario_to_case, summarize_renewable_case
from rts79_cascade import Rts79InitialConfig, run_initial_dcopf
from rts79_cascade_from_case import simulate_cascade_path_from_case


@dataclass(frozen=True)
class RenewablePreliminaryConfig:
    output_dir: str = "results/gcn_search/pio_renewable_preliminary"
    model: str = "results/gcn_search/pio_formal_preliminary_3seed/training/physics_informed/rts79_physics_gcn_model.pt"
    normalizer: str = "results/gcn_search/pio_formal_preliminary_3seed/training/physics_dataset/rts79_step2_state_feature_normalizer_physics.json"
    test_seed_start: int = 20260722
    test_num_seeds: int = 3
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    beta: float = 1.2
    security_limit: float = 1.0
    renewable_penetration_ratio: float = 0.2
    fluctuation_low: float = 0.6
    fluctuation_high: float = 1.1
    run_full_truth: bool = True


def run_renewable_preliminary_experiment(config: RenewablePreliminaryConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    model, adjacency = _load_model(config.model)
    normalizer = json.loads(Path(config.normalizer).read_text(encoding="utf-8"))
    case_rows, pio_rows, baseline_rows, truth_rows = [], [], [], []
    for offset in range(config.test_num_seeds):
        seed = config.test_seed_start + offset
        base_case = run_initial_dcopf(Rts79InitialConfig(random_seed=seed)).case
        renewable_config = RenewableScenarioConfig(
            renewable_penetration_ratio=config.renewable_penetration_ratio,
            fluctuation_low=config.fluctuation_low,
            fluctuation_high=config.fluctuation_high,
            random_seed=seed,
            description="Synthetic renewable perturbation for RTS-79 PIO-GCN robustness check; not EMT or dynamic simulation.",
        )
        root_case = apply_renewable_scenario_to_case(base_case, renewable_config)
        case_summary = summarize_renewable_case(base_case, root_case, renewable_config)
        case_summary["seed"] = seed
        case_rows.append(case_summary)
        pio_config = PioTopkConfig(model=config.model, normalizer=config.normalizer, output_dir="", seed=seed, beta=config.beta, security_limit=config.security_limit, top_k=config.top_k, run_full_truth=config.run_full_truth)
        start = time.time()
        order = pd.DataFrame(_make_path_order(model, adjacency, normalizer, root_case, pio_config))
        runtime = time.time() - start
        sim_rows = []
        for _, row in order.head(max(config.top_k)).iterrows():
            first, second = str(row["path"]).split("->")
            result = simulate_cascade_path_from_case(root_case, [first, second], beta=config.beta, security_limit=config.security_limit)
            sim_rows.append({"path": row["path"], "critical": bool(result.total_load_shed_mw > 1e-7), "total_load_shed_mw": float(result.total_load_shed_mw)})
        sim = pd.DataFrame(sim_rows)
        truth = _make_full_truth(root_case, pio_config) if config.run_full_truth else sim.copy()
        total_critical = int(truth["critical"].sum())
        truth_rows.append({"seed": seed, "num_ordered_n2_paths": int(len(truth)), "total_critical_paths": total_critical, "full_truth": bool(config.run_full_truth)})
        for k in config.top_k:
            subset = sim.head(k)
            found = int(subset["critical"].sum())
            pio_rows.append({"seed": seed, "method": f"PIO_GCN_Top{k}", "top_k": k, "critical_found": found, "critical_path_recall": found / max(total_critical, 1), "runtime_seconds": runtime, "notes": "synthetic renewable preliminary"})
        baseline_rows.extend(_renewable_baselines(seed, truth, config.top_k))
    pd.DataFrame(case_rows).to_csv(out / "renewable_case_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(truth_rows).to_csv(out / "per_seed_fulltruth_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(pio_rows).to_csv(out / "pio_topk_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(baseline_rows).to_csv(out / "baseline_per_seed_summary.csv", index=False, encoding="utf-8-sig")
    aggregate_topk = _aggregate_pio(pd.DataFrame(pio_rows))
    comparison = _aggregate_comparison(pd.DataFrame(pio_rows), pd.DataFrame(baseline_rows))
    aggregate_topk.to_csv(out / "aggregate_topk_summary.csv", index=False, encoding="utf-8-sig")
    comparison.to_csv(out / "aggregate_method_comparison.csv", index=False, encoding="utf-8-sig")
    diagnostics = out / "diagnostics"
    diagnostics.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(pio_rows).sort_values("critical_path_recall").head(1).to_csv(diagnostics / "renewable_worst_seed_summary.csv", index=False, encoding="utf-8-sig")
    _plot_renewable(comparison, out / "figures")
    return {"output_dir": str(out)}


def _renewable_baselines(seed: int, truth: pd.DataFrame, top_k_values: tuple[int, ...]) -> list[dict]:
    rows = []
    truth_by_path = truth.set_index("path").to_dict(orient="index")
    total = int(truth["critical"].sum())
    paths = sorted(truth["path"].astype(str).tolist())
    rng = np.random.default_rng(seed)
    random_paths = paths.copy()
    rng.shuffle(random_paths)
    oracle_paths = truth.sort_values(["critical", "total_load_shed_mw"], ascending=[False, False])["path"].astype(str).tolist()
    for method, ordered in {"random": random_paths, "line_order": paths, "oracle": oracle_paths}.items():
        for k in top_k_values:
            subset = ordered[:k]
            found = sum(bool(truth_by_path.get(path, {}).get("critical", False)) for path in subset)
            rows.append({"seed": seed, "method": method, "top_k": k, "critical_found": found, "critical_path_recall": found / max(total, 1), "runtime_seconds": 0.0, "notes": "synthetic renewable baseline"})
    return rows


def _aggregate_pio(pio: pd.DataFrame) -> pd.DataFrame:
    return pio.groupby(["method", "top_k"], sort=False).agg(num_test_seeds=("seed", "nunique"), mean_critical_found=("critical_found", "mean"), std_critical_found=("critical_found", lambda x: x.std(ddof=0)), mean_critical_path_recall=("critical_path_recall", "mean"), std_critical_path_recall=("critical_path_recall", lambda x: x.std(ddof=0)), mean_runtime_seconds=("runtime_seconds", "mean"), notes=("notes", "first")).reset_index()


def _aggregate_comparison(pio: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    all_rows = pd.concat([pio, baseline], ignore_index=True)
    return all_rows.groupby(["method", "top_k"], sort=False).agg(num_test_seeds=("seed", "nunique"), mean_found=("critical_found", "mean"), std_found=("critical_found", lambda x: x.std(ddof=0)), mean_recall=("critical_path_recall", "mean"), std_recall=("critical_path_recall", lambda x: x.std(ddof=0)), mean_runtime_seconds=("runtime_seconds", "mean"), notes=("notes", "first")).reset_index()


def _plot_renewable(comparison: pd.DataFrame, figure_dir: Path) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    top = comparison[comparison["top_k"] == comparison["top_k"].max()]
    for filename, value_col, title in [("renewable_topk_recall_bar.png", "mean_recall", "Synthetic Renewable Recall"), ("renewable_baseline_comparison.png", "mean_found", "Synthetic Renewable Critical Paths Found")]:
        fig, ax = plt.subplots(figsize=(8, 4), dpi=160)
        ax.bar(top["method"].astype(str), top[value_col].astype(float))
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=25)
        fig.tight_layout()
        fig.savefig(figure_dir / filename)
        plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run synthetic renewable RTS-79 PIO-GCN preliminary evaluation.")
    parser.add_argument("--output-dir", default="results/gcn_search/pio_renewable_preliminary")
    parser.add_argument("--model", default=RenewablePreliminaryConfig.model)
    parser.add_argument("--normalizer", default=RenewablePreliminaryConfig.normalizer)
    parser.add_argument("--test-seed-start", type=int, default=20260722)
    parser.add_argument("--test-num-seeds", type=int, default=3)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20, 50, 100, 200])
    parser.add_argument("--renewable-penetration-ratio", type=float, default=0.2)
    parser.add_argument("--fluctuation-low", type=float, default=0.6)
    parser.add_argument("--fluctuation-high", type=float, default=1.1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_renewable_preliminary_experiment(
        RenewablePreliminaryConfig(
            output_dir=args.output_dir,
            model=args.model,
            normalizer=args.normalizer,
            test_seed_start=args.test_seed_start,
            test_num_seeds=args.test_num_seeds,
            top_k=tuple(args.top_k),
            renewable_penetration_ratio=args.renewable_penetration_ratio,
            fluctuation_low=args.fluctuation_low,
            fluctuation_high=args.fluctuation_high,
        )
    )


if __name__ == "__main__":
    main()
