import sys
from pathlib import Path

import numpy as np
import pandas as pd

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from train_rts79_physics_gcn import PhysicsGcnRunConfig, train_physics_gcn


def test_physics_training_uses_raw_loading_ratio_for_loss(tmp_path):
    x_normalized = np.zeros((1, 38, 9), dtype=np.float32)
    x_raw = np.zeros((1, 38, 9), dtype=np.float32)
    x_raw[:, :, 7] = 1.0
    x_raw[:, :, 8] = 1.0
    x_raw[0, 0, 4] = 1.25
    y = np.zeros((1, 38), dtype=np.int64)
    mask = np.ones((1, 38), dtype=bool)
    dataset = tmp_path / "dataset.npz"
    np.savez(dataset, x_gcn=x_normalized, x_gcn_raw=x_raw, physics_raw_features=x_raw, y_reachable=y, loss_mask=mask)
    out = tmp_path / "train"
    train_physics_gcn(
        PhysicsGcnRunConfig(
            dataset_npz=str(dataset),
            output_dir=str(out),
            epochs=1,
            batch_size=1,
            lambda_relay=1.0,
            beta=1.2,
            p_min_relay=0.5,
        )
    )
    log = pd.read_csv(out / "rts79_physics_gcn_epoch_log.csv")
    assert float(log.loc[0, "relay_priority_loss"]) > 0.0
