from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from rts79_cascade import Rts79InitialConfig, run_sequential_initial_outages_dcpf
from rts79_cascade import search_all_n2_cascade_paths
from train_rts79_paper_gcn import (
    PaperGcnDatasetConfig,
    _fit_x_normalizer,
    _make_x_gcn,
    _make_y_gcn_and_mask,
    _normalize_x,
)


@dataclass(frozen=True)
class ResumableGenerationConfig:
    """可恢复生成配置；resume 是“断点续跑”。"""

    num_scenarios: int = 211
    first_seed: int = 20260511
    load_scale: float = 1.1
    load_random_low: float = 0.9
    load_random_high: float = 1.1
    relay_threshold_beta: float = 1.2
    security_limit: float = 1.0


def generate_resumable_paper_gcn_dataset(
    output_dir: str | Path,
    config: ResumableGenerationConfig,
) -> Path:
    """生成约 8000 个论文式 X_GCN~y_GCN 样本；每个场景完成后立即保存。"""

    out = Path(output_dir)
    checkpoint_dir = out / "scenario_checkpoints"
    path_dir = out / "path_search_by_scenario"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    path_dir.mkdir(parents=True, exist_ok=True)
    (out / "rts79_paper_gcn_8000_generation_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for scenario_id in range(1, config.num_scenarios + 1):
        seed = config.first_seed + scenario_id - 1
        checkpoint_path = checkpoint_dir / f"scenario_{scenario_id:04d}_paper_gcn_raw.npz"
        summary_path = path_dir / f"scenario_{scenario_id:04d}_n2_path_summary.csv"
        if checkpoint_path.exists():
            print(f"[断点续跑] 场景 {scenario_id}/{config.num_scenarios} 已完成，跳过。")
            continue

        print(f"[场景搜索] 场景 {scenario_id}/{config.num_scenarios}，seed={seed}")
        initial_config = Rts79InitialConfig(
            random_seed=seed,
            load_scale=config.load_scale,
            load_random_low=config.load_random_low,
            load_random_high=config.load_random_high,
        )
        if summary_path.exists():
            path_table = pd.read_csv(summary_path)
            print(f"[场景搜索] 读取已有路径表: {summary_path}")
        else:
            search_result = search_all_n2_cascade_paths(
                config=initial_config,
                relay_threshold_beta=config.relay_threshold_beta,
                security_limit=config.security_limit,
            )
            path_table = search_result.summary_table.copy()
            path_table.insert(0, "scenario_id", scenario_id)
            path_table.insert(1, "seed", seed)
            path_table.to_csv(summary_path, index=False, encoding="utf-8-sig")

        checkpoint = _build_one_scenario_paper_gcn_checkpoint(
            scenario_id=scenario_id,
            seed=seed,
            path_table=path_table,
            initial_config=initial_config,
            dataset_config=PaperGcnDatasetConfig(
                load_scale=config.load_scale,
                load_random_low=config.load_random_low,
                load_random_high=config.load_random_high,
                relay_threshold_beta=config.relay_threshold_beta,
                security_limit=config.security_limit,
            ),
        )
        np.savez(
            checkpoint_path,
            x_gcn_raw=checkpoint["x_gcn_raw"],
            y_gcn=checkpoint["y_gcn"],
            loss_mask=checkpoint["loss_mask"],
            scenario_id=checkpoint["scenario_id"],
            seed=checkpoint["seed"],
            first_line=checkpoint["first_line"],
            current_outage_labels=checkpoint["current_outage_labels"],
        )
        print(f"[场景保存] 已保存: {checkpoint_path}")

    return consolidate_checkpoints(out, config)


def consolidate_checkpoints(output_dir: str | Path, config: ResumableGenerationConfig) -> Path:
    """合并所有场景检查点，统一归一化并保存最终 NPZ 数据集。"""

    out = Path(output_dir)
    checkpoint_dir = out / "scenario_checkpoints"
    checkpoint_paths = sorted(checkpoint_dir.glob("scenario_*_paper_gcn_raw.npz"))
    if not checkpoint_paths:
        raise RuntimeError(f"没有找到场景检查点: {checkpoint_dir}")

    x_parts: list[np.ndarray] = []
    y_parts: list[np.ndarray] = []
    mask_parts: list[np.ndarray] = []
    scenario_parts: list[np.ndarray] = []
    seed_parts: list[np.ndarray] = []
    first_line_parts: list[np.ndarray] = []
    outage_parts: list[np.ndarray] = []
    for checkpoint_path in checkpoint_paths:
        data = np.load(checkpoint_path, allow_pickle=True)
        x_parts.append(data["x_gcn_raw"])
        y_parts.append(data["y_gcn"])
        mask_parts.append(data["loss_mask"])
        scenario_parts.append(data["scenario_id"])
        seed_parts.append(data["seed"])
        first_line_parts.append(data["first_line"])
        outage_parts.append(data["current_outage_labels"])

    x_raw = np.concatenate(x_parts, axis=0).astype(np.float32)
    y = np.concatenate(y_parts, axis=0).astype(np.int64)
    loss_mask = np.concatenate(mask_parts, axis=0).astype(bool)
    scenario_id = np.concatenate(scenario_parts, axis=0).astype(np.int64)
    seed = np.concatenate(seed_parts, axis=0).astype(np.int64)
    first_line = np.concatenate(first_line_parts, axis=0).astype(str)
    current_outage_labels = np.concatenate(outage_parts, axis=0).astype(str)
    normalizer = _fit_x_normalizer(x_raw)
    x_gcn = _normalize_x(x_raw, normalizer).astype(np.float32)

    final_path = out / "rts79_paper_gcn_8000_dataset.npz"
    np.savez(
        final_path,
        x_gcn=x_gcn,
        y_gcn=y,
        loss_mask=loss_mask,
        scenario_id=scenario_id,
        seed=seed,
        first_line=first_line,
    )
    summary = pd.DataFrame(
        {
            "scenario_id": scenario_id,
            "seed": seed,
            "first_line": first_line,
            "current_outage_labels": current_outage_labels,
            "num_positive_labels": (y * loss_mask).sum(axis=1),
            "num_candidate_labels": loss_mask.sum(axis=1),
        }
    )
    summary.to_csv(out / "rts79_paper_gcn_8000_sample_summary.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_paper_gcn_8000_feature_normalizer.json").write_text(
        json.dumps(normalizer, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    dataset_stats = {
        "num_samples": int(x_gcn.shape[0]),
        "num_scenarios_completed": int(len(set(scenario_id.tolist()))),
        "num_branch_nodes": int(x_gcn.shape[1]),
        "num_features": int(x_gcn.shape[2]),
        "num_candidate_labels": int(loss_mask.sum()),
        "num_positive_labels": int((y * loss_mask).sum()),
        "positive_ratio": float((y * loss_mask).sum() / max(loss_mask.sum(), 1)),
        "target_num_scenarios": int(config.num_scenarios),
        "target_num_samples": int(config.num_scenarios * 38),
    }
    (out / "rts79_paper_gcn_8000_dataset_stats.json").write_text(
        json.dumps(dataset_stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[合并完成] 最终数据集: {final_path}")
    print(json.dumps(dataset_stats, ensure_ascii=False, indent=2))
    return final_path


def _build_one_scenario_paper_gcn_checkpoint(
    scenario_id: int,
    seed: int,
    path_table: pd.DataFrame,
    initial_config: Rts79InitialConfig,
    dataset_config: PaperGcnDatasetConfig,
) -> dict[str, np.ndarray]:
    clean = path_table.loc[path_table["error"].fillna("") == ""].copy()
    samples: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    scenario_values: list[int] = []
    seed_values: list[int] = []
    first_lines: list[str] = []
    current_outages: list[str] = []

    grouped = clean.groupby("first_line", sort=True)
    for first_line, group in grouped:
        state = run_sequential_initial_outages_dcpf(
            [str(first_line)],
            config=initial_config,
            relay_threshold_beta=dataset_config.relay_threshold_beta,
            security_limit=dataset_config.security_limit,
        )
        x_gcn = _make_x_gcn(state.case, dataset_config.relay_threshold_beta)
        y_gcn, loss_mask = _make_y_gcn_and_mask(group, str(first_line))
        samples.append(x_gcn)
        labels.append(y_gcn)
        masks.append(loss_mask)
        scenario_values.append(scenario_id)
        seed_values.append(seed)
        first_lines.append(str(first_line))
        current_outages.append(",".join(state.final_outage_labels))

    return {
        "x_gcn_raw": np.stack(samples).astype(np.float32),
        "y_gcn": np.stack(labels).astype(np.int64),
        "loss_mask": np.stack(masks).astype(bool),
        "scenario_id": np.array(scenario_values, dtype=np.int64),
        "seed": np.array(seed_values, dtype=np.int64),
        "first_line": np.array(first_lines, dtype=str),
        "current_outage_labels": np.array(current_outages, dtype=str),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="可恢复地生成 RTS-79 论文式 GCN 约 8000 个训练样本。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "paper_gcn_8000"), help="输出目录。")
    parser.add_argument("--num-scenarios", type=int, default=211, help="负荷场景数量；211 个场景约等于 8018 个样本。")
    parser.add_argument("--first-seed", type=int, default=20260511, help="第一个随机种子。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--consolidate-only", action="store_true", help="只合并已有检查点，不继续仿真。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = ResumableGenerationConfig(
        num_scenarios=args.num_scenarios,
        first_seed=args.first_seed,
        relay_threshold_beta=args.beta,
        security_limit=args.security_limit,
    )
    if args.consolidate_only:
        consolidate_checkpoints(args.output_dir, config)
    else:
        generate_resumable_paper_gcn_dataset(args.output_dir, config)


if __name__ == "__main__":
    main()
