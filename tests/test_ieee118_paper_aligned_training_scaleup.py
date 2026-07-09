from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
SCALEUP = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"


def test_scaleup_scripts_expose_required_cli_options() -> None:
    calibration = (IEEE118 / "sweep_ieee118_training_calibration.py").read_text(encoding="utf-8")
    builder = (IEEE118 / "build_ieee118_paper_gcn_training_dataset.py").read_text(encoding="utf-8")
    sweep = (IEEE118 / "sweep_ieee118_paper_gcn_weights.py").read_text(encoding="utf-8")
    assert "--output-stem" in calibration
    assert "--target-state-samples" in builder
    assert "--samples-per-scenario" in builder
    assert "--positive-weights" in sweep
    assert "original_paper_default" in sweep
    assert "best_sensitivity" in sweep


def test_pilot_config_keeps_heldout_seed_out_of_train_when_artifact_exists() -> None:
    meta_path = SCALEUP / "pilot_200" / "ieee118_paper_gcn_dataset_metadata.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert 20260708 in set(meta["test_seeds"])
    assert 20260708 not in set(meta["train_seeds"])
    assert 20260708 not in set(meta["validation_seeds"])
    assert meta["feature_mode"] == "paper"
    assert meta["input_channels"] == 4


def test_weight_sweep_summary_fields_when_artifact_exists() -> None:
    summary_path = SCALEUP / "pilot_2000_weight_sweep" / "ieee118_paper_gcn_weight_sweep_summary.csv"
    if not summary_path.exists():
        return
    summary = pd.read_csv(summary_path)
    required = {
        "positive_weight",
        "setting_role",
        "overall_hit_rate",
        "overall_cover_rate",
        "overall_f1",
        "overall_average_precision",
        "S0_hit_rate",
        "S0_cover_rate",
        "S0_average_precision",
        "S1_hit_rate",
        "S1_cover_rate",
        "S1_average_precision",
        "positive_prediction_rate_at_0.5",
        "positive_prediction_rate_at_0.8",
        "is_best_sensitivity_by_average_precision",
    }
    assert required.issubset(summary.columns)
    assert "original_paper_default" in set(summary["setting_role"])
    default_rows = summary.loc[summary["positive_weight"].astype(float).eq(20.0)]
    assert not default_rows.empty
    assert set(default_rows["setting_role"]) == {"original_paper_default"}


def test_search_eval_supports_paper_aligned_normalizer_and_pfw() -> None:
    evaluator = (IEEE118 / "evaluate_ieee118_rts79_protocol_search.py").read_text(encoding="utf-8")
    assert "--feature-normalizer-json" in evaluator
    assert 'METHOD_PFW = "PFW"' in evaluator


def test_missing_dataset_error_is_clear_for_weight_sweep(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "sweep_ieee118_paper_gcn_weights.py"),
            "--dataset-npz",
            str(tmp_path / "missing.npz"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "Missing paper-aligned IEEE118 GCN dataset" in proc.stderr


def test_scaleup_large_artifacts_are_not_tracked() -> None:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    forbidden_suffixes = (
        "ieee118_paper_gcn_dataset.npz",
        "ieee118_paper_gcn_model.pt",
        "ieee118_paper_gcn_full_predictions.csv",
        "ieee118_step2_state_samples.csv",
    )
    tracked_scaleup = [path for path in tracked if "ieee118_paper_aligned_training_scaleup" in path]
    assert not [path for path in tracked_scaleup if path.endswith(forbidden_suffixes)]
