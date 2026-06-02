from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from train_rts79_step2_state_gcn import Step2TrainConfig, _train_one_label


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train only the reachable RTS-79 Step2-State GCN.")
    parser.add_argument("--dataset", "--dataset-npz", dest="dataset_npz", required=True, help="Step2-State NPZ dataset.")
    parser.add_argument("--output-dir", required=True, help="Output directory for reachable model.")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = np.load(args.dataset_npz, allow_pickle=True)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    config = Step2TrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
    )
    _train_one_label(
        x=data["x_gcn"].astype(np.float32),
        y=data["y_reachable"].astype(np.int64),
        loss_mask=data["loss_mask"].astype(bool),
        active_depth=data["active_depth"].astype(np.int64),
        output_dir=output_dir / "reachable",
        config=config,
        label_name="reachable",
    )


if __name__ == "__main__":
    main()
