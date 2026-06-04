from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from generate_rts79_step2_state_dataset import Step2StateDatasetConfig, generate_step2_state_dataset
from train_rts79_physics_gcn import PhysicsGcnRunConfig, train_physics_gcn


@dataclass(frozen=True)
class StrongPaperBaselineConfig:
    output_dir: str
    training_num_scenarios: int = 20
    training_first_seed: int = 20260750
    training_epochs: int = 5
    training_max_active_depth: int = 1
    candidate_line_filter_mode: str = "high_flow_top_n"
    max_first_lines: int | None = 10
    beta: float = 1.2
    security_limit: float = 1.0
    skip_training_if_exists: bool = False


def train_strong_paper_baseline(config: StrongPaperBaselineConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dataset_dir = out / "paper_dataset"
    train_dir = out / "paper_train_ce_only"
    dataset_npz = dataset_dir / "rts79_step2_state_dataset.npz"
    model_path = train_dir / "rts79_physics_gcn_model.pt"
    normalizer_path = dataset_dir / "rts79_step2_state_feature_normalizer.json"

    (out / "paper_baseline_train_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if not (config.skip_training_if_exists and dataset_npz.exists()):
        generate_step2_state_dataset(
            Step2StateDatasetConfig(
                num_scenarios=config.training_num_scenarios,
                first_seed=config.training_first_seed,
                max_active_depth=config.training_max_active_depth,
                relay_threshold_beta=config.beta,
                security_limit=config.security_limit,
                feature_mode="paper",
                candidate_line_filter_mode=config.candidate_line_filter_mode,
                max_first_lines=config.max_first_lines,
            ),
            dataset_dir,
        )

    if not (config.skip_training_if_exists and model_path.exists()):
        train_physics_gcn(
            PhysicsGcnRunConfig(
                dataset_npz=str(dataset_npz),
                output_dir=str(train_dir),
                epochs=config.training_epochs,
                lambda_mask=0.0,
                lambda_relay=0.0,
                lambda_monotonic=0.0,
                lambda_rank=0.0,
                beta=config.beta,
                security_limit=config.security_limit,
            )
        )

    _copy_if_exists(train_dir / "rts79_physics_gcn_metrics.csv", out / "paper_baseline_training_metrics.csv")
    _copy_if_exists(train_dir / "rts79_physics_gcn_epoch_log.csv", out / "paper_baseline_epoch_log.csv")
    _copy_if_exists(dataset_dir / "rts79_step2_state_dataset_stats.json", out / "paper_baseline_dataset_stats.json")

    eval_summary = {
        "model_path": str(model_path),
        "normalizer_path": str(normalizer_path),
        "feature_mode": "paper",
        "notes": "paper-feature GCN_path_prob baseline trained with the stronger Step2-state configuration; model weights are not intended for git tracking",
    }
    if (out / "paper_baseline_training_metrics.csv").exists():
        metrics = pd.read_csv(out / "paper_baseline_training_metrics.csv")
        if not metrics.empty:
            eval_summary.update(metrics.iloc[-1].to_dict())
    pd.DataFrame([eval_summary]).to_csv(out / "paper_baseline_eval_summary.csv", index=False, encoding="utf-8-sig")
    return eval_summary


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copyfile(src, dst)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a stronger paper-feature RTS-79 GCN_path_prob baseline.")
    parser.add_argument("--output-dir", default="results/gcn_search/paper_baseline_strong")
    parser.add_argument("--training-num-scenarios", type=int, default=20)
    parser.add_argument("--training-first-seed", type=int, default=20260750)
    parser.add_argument("--training-epochs", type=int, default=5)
    parser.add_argument("--training-max-active-depth", type=int, default=1)
    parser.add_argument("--candidate-line-filter-mode", choices=["all", "first_n", "high_flow_top_n"], default="high_flow_top_n")
    parser.add_argument("--max-first-lines", type=int, default=10)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--skip-training-if-exists", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train_strong_paper_baseline(
        StrongPaperBaselineConfig(
            output_dir=args.output_dir,
            training_num_scenarios=args.training_num_scenarios,
            training_first_seed=args.training_first_seed,
            training_epochs=args.training_epochs,
            training_max_active_depth=args.training_max_active_depth,
            candidate_line_filter_mode=args.candidate_line_filter_mode,
            max_first_lines=args.max_first_lines,
            beta=args.beta,
            security_limit=args.security_limit,
            skip_training_if_exists=args.skip_training_if_exists,
        )
    )


if __name__ == "__main__":
    main()
