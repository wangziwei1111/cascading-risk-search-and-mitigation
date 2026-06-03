from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS

from rts79_cascade import (
    Rts79InitialConfig,
    copy_case,
    line_label_to_index_1based,
    open_branches,
    run_initial_dcopf,
    run_sequential_initial_outages_dcpf,
    simulate_cascade_path,
)
from train_rts79_paper_gcn import _fit_x_normalizer, _make_x_gcn, _make_x_gcn_physics, _normalize_x


@dataclass(frozen=True)
class Step2StateDatasetConfig:
    """Step2-state 数据集配置；state 是“状态”，label 是“标签”。"""

    num_scenarios: int = 3
    first_seed: int = 20260750
    scenario_id_offset: int = 0
    max_active_depth: int = 1
    random_failure_limit_r: int = 2
    load_scale: float = 1.1
    load_random_low: float = 0.9
    load_random_high: float = 1.1
    relay_threshold_beta: float = 1.2
    security_limit: float = 1.0
    feature_mode: str = "paper"


def generate_step2_state_dataset(config: Step2StateDatasetConfig, output_dir: str | Path) -> dict:
    """生成 Algorithm 1 的 Step 2* 决策状态数据集。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = out / "scenario_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (out / "rts79_step2_state_generation_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for scenario_offset in range(config.num_scenarios):
        scenario_id = config.scenario_id_offset + scenario_offset + 1
        seed = config.first_seed + scenario_offset
        suffix = "" if config.feature_mode == "paper" else f"_{config.feature_mode}"
        checkpoint_path = checkpoint_dir / f"scenario_{scenario_id:04d}_step2_state_raw{suffix}.npz"
        if checkpoint_path.exists():
            print(f"[Step2断点续跑] scenario={scenario_id}/{config.num_scenarios} 已完成，跳过。")
            continue
        checkpoint = _generate_one_scenario_checkpoint(scenario_id, seed, config)
        np.savez(checkpoint_path, **checkpoint)
        print(f"[Step2场景保存] 已保存: {checkpoint_path}")

    return consolidate_step2_state_checkpoints(out, config)


def consolidate_step2_state_checkpoints(output_dir: str | Path, config: Step2StateDatasetConfig) -> dict:
    """合并 Step2-State 场景检查点并统一归一化。"""

    out = Path(output_dir)
    checkpoint_dir = out / "scenario_checkpoints"
    suffix = "" if config.feature_mode == "paper" else f"_{config.feature_mode}"
    checkpoint_paths = sorted(checkpoint_dir.glob(f"scenario_*_step2_state_raw{suffix}.npz"))
    if not checkpoint_paths:
        raise RuntimeError(f"没有找到 Step2-State 检查点: {checkpoint_dir}")
    samples: list[np.ndarray] = []
    one_step_labels: list[np.ndarray] = []
    reachable_labels: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    records: list[dict] = []
    state_offset = 0
    for checkpoint_path in checkpoint_paths:
        data = np.load(checkpoint_path, allow_pickle=True)
        x_part = data["x_gcn_raw"]
        y_one_part = data["y_one_step"]
        y_reach_part = data["y_reachable"]
        mask_part = data["loss_mask"]
        samples.append(x_part)
        one_step_labels.append(y_one_part)
        reachable_labels.append(y_reach_part)
        masks.append(mask_part)
        for local_idx in range(x_part.shape[0]):
            state_offset += 1
            records.append(
                {
                    "state_id": state_offset,
                    "feature_mode": config.feature_mode,
                    "num_features": int(x_part.shape[2]),
                    "scenario_id": int(data["scenario_id"][local_idx]),
                    "seed": int(data["seed"][local_idx]),
                    "active_depth": int(data["active_depth"][local_idx]),
                    "active_outage_sequence": str(data["active_outage_sequence"][local_idx]),
                    "num_candidate_lines": int(mask_part[local_idx].sum()),
                    "num_one_step_positive": int((y_one_part[local_idx] * mask_part[local_idx]).sum()),
                    "num_reachable_positive": int((y_reach_part[local_idx] * mask_part[local_idx]).sum()),
                }
            )

    x_raw = np.concatenate(samples, axis=0).astype(np.float32)
    y_one_step = np.concatenate(one_step_labels, axis=0).astype(np.int64)
    y_reachable = np.concatenate(reachable_labels, axis=0).astype(np.int64)
    loss_mask = np.concatenate(masks, axis=0).astype(bool)
    normalizer = _fit_x_normalizer(x_raw)
    x_gcn = _normalize_x(x_raw, normalizer).astype(np.float32)
    sample_table = pd.DataFrame(records)
    suffix = "" if config.feature_mode == "paper" else f"_{config.feature_mode}"
    np.savez(
        out / f"rts79_step2_state_dataset{suffix}.npz",
        x_gcn=x_gcn,
        y_one_step=y_one_step,
        y_reachable=y_reachable,
        loss_mask=loss_mask,
        state_id=sample_table["state_id"].to_numpy(dtype=np.int64),
        scenario_id=sample_table["scenario_id"].to_numpy(dtype=np.int64),
        seed=sample_table["seed"].to_numpy(dtype=np.int64),
        active_depth=sample_table["active_depth"].to_numpy(dtype=np.int64),
        active_outage_sequence=sample_table["active_outage_sequence"].to_numpy(dtype=str),
    )
    sample_table.to_csv(out / "rts79_step2_state_sample_summary.csv", index=False, encoding="utf-8-sig")
    (out / f"rts79_step2_state_feature_normalizer{suffix}.json").write_text(
        json.dumps(normalizer, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    stats = {
        "feature_mode": config.feature_mode,
        "num_features": int(x_gcn.shape[2]),
        "num_states": int(x_gcn.shape[0]),
        "num_candidate_labels": int(loss_mask.sum()),
        "num_one_step_positive": int((y_one_step * loss_mask).sum()),
        "num_reachable_positive": int((y_reachable * loss_mask).sum()),
        "one_step_positive_ratio": float((y_one_step * loss_mask).sum() / max(loss_mask.sum(), 1)),
        "reachable_positive_ratio": float((y_reachable * loss_mask).sum() / max(loss_mask.sum(), 1)),
    }
    (out / f"rts79_step2_state_dataset_stats{suffix}.json").write_text(
        json.dumps({**asdict(config), **stats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[Step2数据集] 统计：")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return {
        "x_gcn": x_gcn,
        "y_one_step": y_one_step,
        "y_reachable": y_reachable,
        "loss_mask": loss_mask,
    }


def _generate_one_scenario_checkpoint(scenario_id: int, seed: int, config: Step2StateDatasetConfig) -> dict:
    initial_config = Rts79InitialConfig(
        random_seed=seed,
        load_scale=config.load_scale,
        load_random_low=config.load_random_low,
        load_random_high=config.load_random_high,
    )
    initial_state = run_initial_dcopf(initial_config)
    state_specs = _make_state_specs(initial_state.case, initial_config, config)
    samples: list[np.ndarray] = []
    one_step_labels: list[np.ndarray] = []
    reachable_labels: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    scenario_values: list[int] = []
    seed_values: list[int] = []
    active_depth_values: list[int] = []
    active_sequence_values: list[str] = []
    for local_state_id, (active_sequence, state_case) in enumerate(state_specs, start=1):
        print(
            "[Step2数据集] "
            f"scenario={scenario_id}/{config.num_scenarios}, "
            f"local_state={local_state_id}, "
            f"active_sequence={_format_sequence(active_sequence)}"
        )
        x_gcn = _make_state_x_gcn(state_case, config)
        y_one, y_reach, mask = _label_state(
            active_sequence=active_sequence,
            initial_config=initial_config,
            state_case=state_case,
            config=config,
        )
        samples.append(x_gcn)
        one_step_labels.append(y_one)
        reachable_labels.append(y_reach)
        masks.append(mask)
        scenario_values.append(scenario_id)
        seed_values.append(seed)
        active_depth_values.append(len(active_sequence))
        active_sequence_values.append(_format_sequence(active_sequence))
    return {
        "x_gcn_raw": np.stack(samples).astype(np.float32),
        "y_one_step": np.stack(one_step_labels).astype(np.int64),
        "y_reachable": np.stack(reachable_labels).astype(np.int64),
        "loss_mask": np.stack(masks).astype(bool),
        "scenario_id": np.array(scenario_values, dtype=np.int64),
        "seed": np.array(seed_values, dtype=np.int64),
        "active_depth": np.array(active_depth_values, dtype=np.int64),
        "active_outage_sequence": np.array(active_sequence_values, dtype=str),
    }


def _make_state_x_gcn(case: dict, config: Step2StateDatasetConfig) -> np.ndarray:
    if config.feature_mode == "paper":
        return _make_x_gcn(case, config.relay_threshold_beta)
    if config.feature_mode == "physics":
        return _make_x_gcn_physics(case, config.relay_threshold_beta, security_limit=config.security_limit)
    raise ValueError(f"Unsupported feature_mode: {config.feature_mode}")


def _make_state_specs(base_case: dict, initial_config: Rts79InitialConfig, config: Step2StateDatasetConfig) -> list[tuple[tuple[str, ...], dict]]:
    specs: list[tuple[tuple[str, ...], dict]] = [(tuple(), base_case)]
    if config.max_active_depth >= 1:
        for line_idx in range(1, base_case["branch"].shape[0] + 1):
            first_line = f"L{line_idx:02d}"
            sequence_state = run_sequential_initial_outages_dcpf(
                [first_line],
                config=initial_config,
                relay_threshold_beta=config.relay_threshold_beta,
                security_limit=config.security_limit,
            )
            if sequence_state.total_load_shed_mw > 1e-7:
                continue
            specs.append(((first_line,), sequence_state.case))
    return specs


def _label_state(
    active_sequence: tuple[str, ...],
    initial_config: Rts79InitialConfig,
    state_case: dict,
    config: Step2StateDatasetConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y_one_step = np.zeros(38, dtype=np.int64)
    y_reachable = np.zeros(38, dtype=np.int64)
    mask = _candidate_mask(state_case)
    for line_idx in np.where(mask)[0]:
        candidate = f"L{line_idx + 1:02d}"
        next_sequence = tuple(list(active_sequence) + [candidate])
        one_step_shed = _simulate_one_step_from_state(state_case, candidate, config)
        reachable_shed = _simulate_reachable_from_initial_sequence(next_sequence, initial_config, config)
        y_one_step[line_idx] = int(one_step_shed > 1e-7)
        y_reachable[line_idx] = int(reachable_shed > 1e-7)
    return y_one_step, y_reachable, mask


def _candidate_mask(case: dict) -> np.ndarray:
    return case["branch"][:, BR_STATUS].astype(int) == 1


def _simulate_one_step_from_state(state_case: dict, candidate: str, config: Step2StateDatasetConfig) -> float:
    updated = open_branches(copy_case(state_case), [line_label_to_index_1based(candidate)])
    from rts79_cascade import balance_islands_by_load_shedding, redispatch_minimize_load_shed, solve_islanded_dcpf

    total_island_shed = 0.0
    current = updated
    for _ in range(20):
        island_state = balance_islands_by_load_shedding(current)
        total_island_shed += float(island_state.total_load_shed_mw)
        result, success = solve_islanded_dcpf(island_state.case)
        if not success:
            break
        from rts79_cascade import _build_branch_table

        branch_table = _build_branch_table(result)
        overloaded = branch_table.loc[(branch_table["status"] == 1) & (branch_table["loading_ratio"] > config.relay_threshold_beta), "line_label"].tolist()
        if not overloaded:
            current = result
            break
        current = open_branches(result, [line_label_to_index_1based(label) for label in overloaded])
    redispatch = redispatch_minimize_load_shed(current, security_limit=config.security_limit)
    return total_island_shed + float(redispatch.total_load_shed_mw)


def _simulate_reachable_from_initial_sequence(
    next_sequence: tuple[str, ...],
    initial_config: Rts79InitialConfig,
    config: Step2StateDatasetConfig,
) -> float:
    if len(next_sequence) >= config.random_failure_limit_r:
        result = simulate_cascade_path(
            next_sequence,
            config=initial_config,
            relay_threshold_beta=config.relay_threshold_beta,
            security_limit=config.security_limit,
        )
        return float(result.total_load_shed_mw)

    # For RTS-79 N-2, remaining depth after the root state is one step.
    best_shed = 0.0
    used = set(next_sequence)
    for line_idx in range(1, 39):
        candidate = f"L{line_idx:02d}"
        if candidate in used:
            continue
        result = simulate_cascade_path(
            tuple(list(next_sequence) + [candidate]),
            config=initial_config,
            relay_threshold_beta=config.relay_threshold_beta,
            security_limit=config.security_limit,
        )
        best_shed = max(best_shed, float(result.total_load_shed_mw))
    return best_shed


def _format_sequence(sequence: tuple[str, ...]) -> str:
    return "->".join(sequence)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 RTS-79 Algorithm 1 Step2-state GCN 数据集。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "step2_state_dataset_preview"), help="输出目录。")
    parser.add_argument("--num-scenarios", type=int, default=3, help="负荷场景数量。")
    parser.add_argument("--first-seed", type=int, default=20260750, help="第一个随机种子。")
    parser.add_argument("--max-active-depth", type=int, default=1, help="纳入数据集的最大主动故障深度。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--consolidate-only", action="store_true", help="只合并已有检查点，不继续生成。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Step2StateDatasetConfig(
        num_scenarios=args.num_scenarios,
        first_seed=args.first_seed,
        max_active_depth=args.max_active_depth,
        relay_threshold_beta=args.beta,
        security_limit=args.security_limit,
    )
    if args.consolidate_only:
        consolidate_step2_state_checkpoints(args.output_dir, config)
    else:
        generate_step2_state_dataset(config, args.output_dir)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RTS-79 Algorithm 1 Step2-state GCN dataset.")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "step2_state_dataset_preview"), help="Output directory.")
    parser.add_argument("--num-scenarios", type=int, default=3, help="Number of load scenarios.")
    parser.add_argument("--first-seed", type=int, default=20260750, help="First random seed.")
    parser.add_argument("--max-active-depth", type=int, default=1, help="Maximum active outage depth included in states.")
    parser.add_argument("--beta", type=float, default=1.2, help="Relay threshold beta.")
    parser.add_argument("--security-limit", type=float, default=1.0, help="Redispatch security loading limit.")
    parser.add_argument("--feature-mode", choices=["paper", "physics"], default="paper", help="GCN feature mode.")
    parser.add_argument("--consolidate-only", action="store_true", help="Only consolidate existing checkpoints.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Step2StateDatasetConfig(
        num_scenarios=args.num_scenarios,
        first_seed=args.first_seed,
        max_active_depth=args.max_active_depth,
        relay_threshold_beta=args.beta,
        security_limit=args.security_limit,
        feature_mode=args.feature_mode,
    )
    if args.consolidate_only:
        consolidate_step2_state_checkpoints(args.output_dir, config)
    else:
        generate_step2_state_dataset(config, args.output_dir)


if __name__ == "__main__":
    main()
