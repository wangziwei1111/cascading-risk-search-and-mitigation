from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
PROTOCOL_RESULTS = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_rts79_protocol_eval"
sys.path.insert(0, str(IEEE118))

from build_ieee118_base_state_for_rts79_gcn import build_base_state
from convert_ieee118_step2_to_rts79_gcn_format import PAPER_FEATURE_NAMES


def test_protocol_audit_document_contains_key_methods() -> None:
    doc = ROOT / "docs" / "rts79_to_ieee118_protocol_alignment.md"
    assert doc.exists()
    text = doc.read_text(encoding="utf-8")
    for needle in [
        "PaperStyleRts79Gcn",
        "GCN_path_prob",
        "RTS79_GCN_path_prob_reused_on_IEEE118",
        "RTS79_GCN_second_only_reused_on_IEEE118",
        "full_cascade_path",
        "LODF_yP",
    ]:
        assert needle in text


def test_base_state_tensor_can_be_generated(tmp_path: Path) -> None:
    normalizer = {name: {"mean": 0.0, "std": 1.0} for name in PAPER_FEATURE_NAMES}
    normalizer_path = tmp_path / "normalizer.json"
    normalizer_path.write_text(json.dumps(normalizer), encoding="utf-8")
    out = tmp_path / "base"
    meta = build_base_state(
        argparse.Namespace(
            seed=20260708,
            load_scale=1.0,
            limit_mode="flow_scaled",
            flow_limit_scale=8.0,
            min_rate_a=1.0,
            beta=1.2,
            normalizer_json=normalizer_path,
            model_path=None,
            output_dir=out,
        )
    )
    assert meta["num_base_states"] == 1
    data = np.load(out / "ieee118_rts79_gcn_base_state.npz", allow_pickle=True)
    assert data["x_gcn"].shape == (1, 186, 4)
    assert list(data["feature_names"]) == PAPER_FEATURE_NAMES


def test_committed_protocol_dataset_metadata_uses_paper_features() -> None:
    meta = json.loads((PROTOCOL_RESULTS / "ieee118_rts79_gcn_dataset_metadata.json").read_text(encoding="utf-8"))
    assert meta["feature_mode"] == "paper"
    assert meta["feature_names"] == PAPER_FEATURE_NAMES
    assert meta["num_path_samples"] == 34410
    assert meta["num_critical_path_labels"] == 1859
    assert meta["num_relay_cascade_path_labels"] == 1659
    leakage = set(meta["feature_names"]) & set(meta["excluded_leakage_columns"])
    assert not leakage


def test_gcn_path_prob_score_is_product() -> None:
    top = pd.read_csv(PROTOCOL_RESULTS / "ieee118_rts79_protocol_topk_paths.csv")
    path_prob = top.loc[top["method"] == "RTS79_GCN_path_prob_reused_on_IEEE118"].head(100)
    product = path_prob["p_shed_first"] * path_prob["p_shed_second"]
    assert np.allclose(product, path_prob["path_product_score"])


def test_gcn_path_prob_order_differs_from_second_only() -> None:
    top = pd.read_csv(PROTOCOL_RESULTS / "ieee118_rts79_protocol_topk_paths.csv")
    path_prob = top.loc[top["method"] == "RTS79_GCN_path_prob_reused_on_IEEE118", "path"].head(100).tolist()
    second_only = top.loc[top["method"] == "RTS79_GCN_second_only_reused_on_IEEE118", "path"].head(100).tolist()
    assert path_prob != second_only


def test_lodf_yp_is_documented_as_two_layer_not_product() -> None:
    script = (IEEE118 / "evaluate_ieee118_rts79_protocol_search.py").read_text(encoding="utf-8")
    assert "first_order = sorted(first_lines, key=lambda line: (-float(y_p_first.get(line" in script
    assert "second_y_p" in script
    assert "first_yP * second_yP" not in script


def test_search_summary_contains_required_methods() -> None:
    summary = pd.read_csv(PROTOCOL_RESULTS / "ieee118_rts79_protocol_search_summary.csv")
    methods = set(summary["method"])
    required = {
        "RTS79_GCN_prob_reused_on_IEEE118",
        "RTS79_GCN_prob_yP_reused_on_IEEE118",
        "RTS79_GCN_path_prob_reused_on_IEEE118",
        "RTS79_GCN_second_only_reused_on_IEEE118",
        "LODF_yP",
        "line_order",
        "random",
    }
    assert required.issubset(methods)


def test_curve_points_are_sparse_and_plot_ready() -> None:
    curve = pd.read_csv(PROTOCOL_RESULTS / "ieee118_rts79_protocol_curve_points_sparse.csv")
    assert len(curve) < 1000
    assert {
        "candidate_evaluations",
        "found_critical_count_full_cascade_dedup",
        "critical_hit_count_path_level",
        "relay_cascade_hit_count_path_level",
        "captured_load_shed_mw",
        "method",
    }.issubset(curve.columns)


def test_full_cascade_path_rule_is_documented() -> None:
    config = json.loads((PROTOCOL_RESULTS / "ieee118_rts79_protocol_config.json").read_text(encoding="utf-8"))
    assert "relay_trip_labels" in config["full_cascade_path_rule"]
    readme = (PROTOCOL_RESULTS / "ieee118_rts79_protocol_readme.md").read_text(encoding="utf-8")
    assert "full-cascade-path" in readme


def test_missing_local_large_file_error_is_clear(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "evaluate_ieee118_rts79_protocol_search.py"),
            "--dataset-npz",
            str(tmp_path / "missing.npz"),
            "--path-index-csv",
            str(tmp_path / "missing.csv"),
            "--fulltruth-csv",
            str(tmp_path / "missing_fulltruth.csv"),
            "--model-path",
            str(tmp_path / "missing.pt"),
            "--first-step-probabilities-csv",
            str(tmp_path / "missing_first.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "Missing IEEE118 full-truth CSV" in proc.stderr
