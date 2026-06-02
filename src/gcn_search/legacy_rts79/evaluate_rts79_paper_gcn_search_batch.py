from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from evaluate_rts79_paper_gcn_search import SearchEvalConfig, evaluate_search_methods


@dataclass(frozen=True)
class BatchSearchEvalConfig:
    """批量搜索评估配置；batch 是“批量”。"""

    first_seed: int = 20260722
    num_scenarios: int = 10
    beta: float = 1.2
    security_limit: float = 1.0
    gcn_threshold: float = 0.5


def evaluate_search_batch(
    model_path: str | Path,
    normalizer_path: str | Path,
    output_dir: str | Path,
    config: BatchSearchEvalConfig,
) -> pd.DataFrame:
    """对多个测试负荷场景评估论文式 GCN+y_P 搜索效率。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scenario_summaries: list[pd.DataFrame] = []
    for scenario_offset in range(config.num_scenarios):
        seed = config.first_seed + scenario_offset
        scenario_dir = out / f"seed_{seed}"
        print(f"[批量搜索评估] 场景 {scenario_offset + 1}/{config.num_scenarios}, seed={seed}")
        summary = evaluate_search_methods(
            model_path=model_path,
            normalizer_path=normalizer_path,
            output_dir=scenario_dir,
            config=SearchEvalConfig(
                seed=seed,
                beta=config.beta,
                security_limit=config.security_limit,
                gcn_threshold=config.gcn_threshold,
            ),
        )
        summary.insert(0, "seed", seed)
        scenario_summaries.append(summary)

    all_summary = pd.concat(scenario_summaries, ignore_index=True)
    all_summary.to_csv(out / "rts79_batch_search_efficiency_per_scenario.csv", index=False, encoding="utf-8-sig")
    mean_summary = (
        all_summary.groupby("search_method", as_index=False)
        .agg(
            mean_total_critical_count=("total_critical_count", "mean"),
            mean_attempts_to_find_all=("attempts_to_find_all", "mean"),
            mean_found_after_50_attempts=("found_after_50_attempts", "mean"),
            mean_found_after_100_attempts=("found_after_100_attempts", "mean"),
            mean_found_after_200_attempts=("found_after_200_attempts", "mean"),
            mean_found_after_500_attempts=("found_after_500_attempts", "mean"),
        )
        .sort_values("mean_attempts_to_find_all")
        .reset_index(drop=True)
    )
    mean_summary.to_csv(out / "rts79_batch_search_efficiency_mean.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_batch_search_eval_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[批量搜索评估] 平均结果：")
    print(mean_summary.to_string(index=False))
    return mean_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量评估论文式 GCN+y_P 在 RTS-79 N-2 搜索中的效率。")
    parser.add_argument("--model", required=True, help="论文式 GCN 模型 .pt 文件。")
    parser.add_argument("--normalizer", required=True, help="论文式 GCN 特征归一化 JSON 文件。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "paper_gcn_search_eval_batch"), help="输出目录。")
    parser.add_argument("--first-seed", type=int, default=20260722, help="第一个测试场景随机种子。")
    parser.add_argument("--num-scenarios", type=int, default=10, help="测试场景数量。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--gcn-threshold", type=float, default=0.5, help="GCN 判为危险支路的概率阈值。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = BatchSearchEvalConfig(
        first_seed=args.first_seed,
        num_scenarios=args.num_scenarios,
        beta=args.beta,
        security_limit=args.security_limit,
        gcn_threshold=args.gcn_threshold,
    )
    evaluate_search_batch(args.model, args.normalizer, args.output_dir, config)


if __name__ == "__main__":
    main()
