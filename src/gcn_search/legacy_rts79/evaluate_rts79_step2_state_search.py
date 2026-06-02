from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from evaluate_rts79_paper_gcn_search import SearchEvalConfig, evaluate_search_methods
from rts79_cascade import line_label_to_index_1based
from train_rts79_paper_gcn import PaperGcnTrainConfig, PaperStyleRts79Gcn


@dataclass(frozen=True)
class Step2SearchConfig:
    """Step2-State 搜索评估配置。"""

    first_seed: int = 20260722
    num_scenarios: int = 5
    beta: float = 1.2
    security_limit: float = 1.0
    gcn_threshold: float = 0.5


def evaluate_step2_state_models(
    one_step_model: str | Path,
    reachable_model: str | Path,
    normalizer: str | Path,
    output_dir: str | Path,
    config: Step2SearchConfig,
) -> pd.DataFrame:
    """分别评估 one_step 与 reachable 模型的搜索效率。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    all_rows: list[pd.DataFrame] = []
    for label_scheme, model_path in [
        ("one_step", one_step_model),
        ("reachable", reachable_model),
    ]:
        for scenario_offset in range(config.num_scenarios):
            seed = config.first_seed + scenario_offset
            scenario_dir = out / label_scheme / f"seed_{seed}"
            print(f"[Step2搜索评估] label={label_scheme}, seed={seed}")
            summary = evaluate_search_methods(
                model_path=model_path,
                normalizer_path=normalizer,
                output_dir=scenario_dir,
                config=SearchEvalConfig(
                    seed=seed,
                    beta=config.beta,
                    security_limit=config.security_limit,
                    gcn_threshold=config.gcn_threshold,
                ),
            )
            summary.insert(0, "label_scheme", label_scheme)
            summary.insert(1, "seed", seed)
            all_rows.append(summary)

    all_summary = pd.concat(all_rows, ignore_index=True)
    all_summary.to_csv(out / "rts79_step2_search_per_scenario.csv", index=False, encoding="utf-8-sig")
    mean_summary = (
        all_summary.groupby(["label_scheme", "search_method"], as_index=False)
        .agg(
            mean_total_critical_count=("total_critical_count", "mean"),
            mean_attempts_to_find_all=("attempts_to_find_all", "mean"),
            mean_found_after_50_attempts=("found_after_50_attempts", "mean"),
            mean_found_after_100_attempts=("found_after_100_attempts", "mean"),
            mean_found_after_200_attempts=("found_after_200_attempts", "mean"),
            mean_found_after_500_attempts=("found_after_500_attempts", "mean"),
        )
        .sort_values(["label_scheme", "mean_attempts_to_find_all"])
        .reset_index(drop=True)
    )
    mean_summary.to_csv(out / "rts79_step2_search_mean_summary.csv", index=False, encoding="utf-8-sig")
    print("[Step2搜索评估] 平均结果：")
    print(mean_summary.to_string(index=False))
    return mean_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评估 Step2-State one_step/reachable GCN 搜索效率。")
    parser.add_argument("--one-step-model", required=True, help="one_step 模型 .pt 文件。")
    parser.add_argument("--reachable-model", required=True, help="reachable 模型 .pt 文件。")
    parser.add_argument("--normalizer", required=True, help="Step2-State 特征归一化 JSON 文件。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "step2_state_search_eval"), help="输出目录。")
    parser.add_argument("--first-seed", type=int, default=20260722, help="第一个测试随机种子。")
    parser.add_argument("--num-scenarios", type=int, default=5, help="测试场景数量。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--gcn-threshold", type=float, default=0.5, help="GCN 判为危险支路的概率阈值。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Step2SearchConfig(
        first_seed=args.first_seed,
        num_scenarios=args.num_scenarios,
        beta=args.beta,
        security_limit=args.security_limit,
        gcn_threshold=args.gcn_threshold,
    )
    evaluate_step2_state_models(args.one_step_model, args.reachable_model, args.normalizer, args.output_dir, config)


if __name__ == "__main__":
    main()
