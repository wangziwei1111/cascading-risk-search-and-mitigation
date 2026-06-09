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
        "run_pio_gcn_extended_fulltruth_experiment",
        "train_rts79_paper_baseline_strong",
        "renewable_scenarios",
        "run_pio_gcn_renewable_preliminary_experiment",
        "analyze_topk_depth_tradeoff",
        "evaluate_pio_gcn_ensemble_ranking",
        "evaluate_pio_gcn_hard_negative_rerank",
        "build_path_reranker_dataset",
        "train_path_reranker",
        "evaluate_path_reranker_fulltruth",
        "mine_hard_negative_paths",
        "audit_path_reranker_leakage",
        "evaluate_path_reranker_strict_heldout",
        "path_reranker_eval_utils",
        "run_path_reranker_extended_strict_eval",
        "evaluate_path_reranker_renewable",
        "run_path_reranker_cross_scenario_eval",
        "analyze_path_pattern_memorization",
        "run_path_reranker_feature_ablation",
        "analyze_pio_gcn_loss_diagnostics",
        "export_simulink_dynamic_cases",
        "export_rts79_simulink_basecase",
        "make_mock_simulink_dynamic_results",
        "analyze_simulink_dynamic_results",
    ]

    for module_name in module_names:
        assert importlib.import_module(module_name) is not None
