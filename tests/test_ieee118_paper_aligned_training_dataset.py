from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
ARTIFACT = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_training_smoke"
sys.path.insert(0, str(IEEE118))

import build_ieee118_paper_gcn_training_dataset as dataset_builder
from build_ieee118_paper_gcn_training_dataset import build_dataset


def test_committed_smoke_metadata_contains_s0_and_s1_samples() -> None:
    meta = json.loads((ARTIFACT / "ieee118_paper_gcn_dataset_metadata.json").read_text(encoding="utf-8"))
    assert meta["feature_mode"] == "paper"
    assert meta["input_channels"] == 4
    assert meta["num_s0_samples"] > 0
    assert meta["num_s1_samples"] > 0
    assert meta["num_first_step_critical_labels"] > 0
    assert meta["positive_label_ratio"] > 0
    assert meta["normalizer_fit_split"] == "train"
    assert meta["paper_aligned_target_state_samples"] == 8000


def test_committed_sample_summary_has_seed_separated_splits() -> None:
    summary = pd.read_csv(ARTIFACT / "ieee118_paper_gcn_sample_summary.csv")
    split_seeds = {split: set(group["seed"].astype(int)) for split, group in summary.groupby("split")}
    assert {"train", "validation", "test"}.issubset(split_seeds)
    assert not (split_seeds["train"] & split_seeds["validation"])
    assert not (split_seeds["train"] & split_seeds["test"])
    assert not (split_seeds["validation"] & split_seeds["test"])
    assert set(summary["sample_type"]) == {"S0", "S1"}


def tiny_builder_args(tmp_path: Path, *, resume: bool = False, load_scale: float = 1.1) -> argparse.Namespace:
    return argparse.Namespace(
            seeds=[20260701],
            num_load_scenarios=None,
            samples_per_scenario=1,
            target_state_samples=2,
            load_scale=load_scale,
            load_random_low=0.9,
            load_random_high=1.1,
            limit_mode="flow_scaled",
            flow_limit_scale=8.0,
            min_rate_a=1.0,
            beta=1.2,
            security_limit=1.0,
            first_step_critical_policy="skip",
            feature_mode="paper",
            sample_seed=1,
            resume=resume,
            checkpoint_every=1,
            train_seeds=[20260701],
            validation_seeds=[],
            test_seeds=[],
            output_dir=tmp_path,
        )


def test_tiny_builder_outputs_loss_mask_and_no_seed_leakage(tmp_path: Path) -> None:
    meta = build_dataset(tiny_builder_args(tmp_path))
    data = np.load(tmp_path / "ieee118_paper_gcn_dataset.npz", allow_pickle=True)
    assert data["x_gcn"].shape[2] == 4
    assert data["loss_mask"].any()
    assert int(data["y_gcn"][data["loss_mask"]].sum()) == meta["num_positive_labels"]
    assert set(data["sample_type"].astype(str)) == {"S0", "S1"}
    s1_active = data["active_first_line"][data["sample_type"].astype(str) == "S1"].astype(str).tolist()
    assert len(s1_active) == 1 and s1_active[0].startswith("L")
    progress = json.loads((tmp_path / "ieee118_paper_gcn_checkpoint.json").read_text(encoding="utf-8"))
    assert progress["status"] == "complete"
    assert progress["num_state_samples"] == 2
    assert progress["shards"]


def test_completed_checkpoint_resume_does_not_rerun_cascade(tmp_path: Path, monkeypatch) -> None:
    first = build_dataset(tiny_builder_args(tmp_path))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("completed --resume run must not rerun cascade simulation")

    monkeypatch.setattr(dataset_builder, "run_sequential_outages_for_case", fail_if_called)
    resumed = build_dataset(tiny_builder_args(tmp_path, resume=True))
    assert resumed == first


def test_checkpoint_resume_rejects_changed_physics_config(tmp_path: Path) -> None:
    build_dataset(tiny_builder_args(tmp_path))
    with pytest.raises(ValueError, match="Checkpoint configuration does not match"):
        build_dataset(tiny_builder_args(tmp_path, resume=True, load_scale=1.05))


def test_calibration_sweep_outputs_exist() -> None:
    sweep = pd.read_csv(ARTIFACT / "ieee118_training_calibration_sweep.csv")
    assert {"load_scale", "flow_limit_scale", "positive_label_ratio", "recommended_setting"}.issubset(sweep.columns)
    assert len(sweep) == 9
    assert (sweep["error_count"] == 0).all()
    data = json.loads((ARTIFACT / "ieee118_training_calibration_sweep.json").read_text(encoding="utf-8"))
    assert len(data) == 9


def test_large_npz_and_model_are_not_tracked() -> None:
    # The smoke run may leave these files locally, but they should not be committed.
    import subprocess

    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    forbidden = {
        "results/gcn_search/ieee118_flow_scaled_800_paper_aligned_training_smoke/ieee118_paper_gcn_dataset.npz",
        "results/gcn_search/ieee118_flow_scaled_800_paper_aligned_training_smoke/ieee118_paper_gcn_model.pt",
    }
    assert forbidden.isdisjoint(set(tracked))
