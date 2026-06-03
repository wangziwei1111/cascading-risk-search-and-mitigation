from __future__ import annotations

import argparse
import json

from ._common import load_config, resolve_path
from gcn_search.ieee14.training import train_branch_gcn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gcn_search/ieee14/ieee14_gcn.yaml")
    parser.add_argument("--epochs", type=int)
    args = parser.parse_args()
    cfg = load_config(args.config)
    training_cfg = cfg["training"]
    metrics = train_branch_gcn(
        dataset_dir=resolve_path(cfg["dataset"]["output_dir"]),
        checkpoint_dir=resolve_path(training_cfg["checkpoint_dir"]),
        eval_dir=resolve_path(cfg["evaluation"]["output_dir"]),
        seed=training_cfg.get("seed", 7),
        epochs=args.epochs or training_cfg.get("epochs", 120),
        learning_rate=training_cfg.get("learning_rate", 0.01),
        hidden_dim=training_cfg.get("hidden_dim", 32),
        outage_loss_weight=training_cfg.get("outage_loss_weight", 6.0),
    )
    print(json.dumps(metrics["test"], indent=2))


if __name__ == "__main__":
    main()

