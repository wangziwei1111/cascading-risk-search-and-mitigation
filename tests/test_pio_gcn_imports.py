"""Lightweight import smoke tests for PIO-GCN PathRank modules."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def test_pio_gcn_key_modules_import() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
    if str(legacy_dir) not in sys.path:
        sys.path.insert(0, str(legacy_dir))

    module_names = [
        "gcn_physics_constraints",
        "online_state_update",
        "rts79_cascade_from_case",
        "train_rts79_physics_gcn",
        "evaluate_rts79_pio_gcn_topk",
        "run_pio_gcn_formal_small_experiment",
        "run_pio_gcn_formal_ablation",
        "run_pio_gcn_rank_loss_experiment",
    ]

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None
