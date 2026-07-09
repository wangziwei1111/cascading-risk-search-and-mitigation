from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
ARTIFACT = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_training_smoke"


def test_training_metrics_include_overall_s0_and_s1() -> None:
    metrics = json.loads((ARTIFACT / "ieee118_paper_gcn_metrics.json").read_text(encoding="utf-8"))
    assert metrics["model_class"] == "PaperStyleRts79Gcn"
    assert metrics["source_model_file"] == "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py"
    assert metrics["input_channels"] == 4
    for key in ["overall", "S0", "S1", "train", "validation", "test"]:
        assert key in metrics["classification_metrics"]
        split_metrics = metrics["classification_metrics"][key]
        for metric in [
            "total_accuracy",
            "hit_rate",
            "cover_rate",
            "precision",
            "recall",
            "f1",
            "average_precision",
            "positive_prediction_rate_at_0.5",
            "positive_prediction_rate_at_0.8",
        ]:
            assert metric in split_metrics


def test_training_log_and_compact_predictions_exist() -> None:
    assert (ARTIFACT / "ieee118_paper_gcn_training_log.csv").exists()
    compact = ARTIFACT / "ieee118_paper_gcn_validation_predictions_compact.csv"
    assert compact.exists()
    assert compact.stat().st_size > 0


def test_training_script_mentions_original_rts79_model_only() -> None:
    script = (IEEE118 / "train_ieee118_paper_aligned_gcn.py").read_text(encoding="utf-8")
    assert "PaperStyleRts79Gcn" in script
    assert "load_original_rts79_gcn_symbols" in script
    assert "LogisticRegression" not in script
    assert "GCN_smoke" not in script


def test_paper_aligned_eval_summary_contains_expected_methods() -> None:
    summary = pd.read_csv(ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_eval" / "ieee118_paper_aligned_search_summary.csv")
    methods = set(summary["method"])
    assert {
        "random",
        "line_order",
        "PFW",
        "LODF_yP",
        "RTS79_GCN_path_prob_reused_on_IEEE118_earlystop",
        "RTS79_GCN_second_only_reused_on_IEEE118_earlystop",
    }.issubset(methods)
    config = json.loads((ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_paper_aligned_eval" / "ieee118_paper_aligned_config.json").read_text(encoding="utf-8"))
    assert config["feature_normalizer_json"]


def test_missing_dataset_error_is_clear(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "train_ieee118_paper_aligned_gcn.py"),
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
