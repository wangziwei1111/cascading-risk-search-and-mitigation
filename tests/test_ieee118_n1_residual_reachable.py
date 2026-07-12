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
sys.path.insert(0, str(IEEE118))

from analyze_ieee118_n1_residual_n2 import (
    analyze,
    annotate_n1_residual,
    evaluate_ranking,
    load_first_step_summary,
    load_valid_truth,
    parse_args as parse_audit_args,
)
from build_ieee118_paper_gcn_training_dataset import append_sample
from build_ieee118_residual_reachable_dataset import build_residual_labels, convert
from evaluate_ieee118_n1_gated_search import apply_n1_gate, order_n1_gated, random_threshold_summary
from summarize_ieee118_n1_residual_gcn import summarize
from train_ieee118_residual_reachable_gcn import train
from train_ieee118_with_original_rts79_gcn import load_original_rts79_gcn_symbols


LINE_LABELS = np.asarray(["L001", "L002", "L003", "L004"], dtype=str)


def write_pilot_fixture(path: Path) -> None:
    rng = np.random.default_rng(7)
    x = rng.normal(size=(7, 4, 4)).astype(np.float32)
    y = np.asarray(
        [
            [0, 1, 0, 0],  # seed 1 S0: L002 is N-1 critical
            [0, 1, 1, 0],  # seed 1 S1(L001): residual L003 is critical
            [0, 1, 0, 1],  # ambiguous active outage; must not create an S0 label
            [0, 0, 1, 0],  # seed 2 S0: L003 is N-1 critical
            [1, 0, 1, 1],  # seed 2 S1(L002): residual L001/L004 are critical
            [1, 0, 0, 0],  # seed 3 S0: L001 is N-1 critical
            [1, 0, 0, 1],  # seed 3 S1(L002): residual L004 is critical
        ],
        dtype=np.int64,
    )
    mask = np.asarray(
        [
            [1, 1, 1, 1],
            [0, 1, 1, 1],
            [1, 1, 0, 0],
            [1, 1, 1, 1],
            [1, 0, 1, 1],
            [1, 1, 1, 1],
            [1, 0, 1, 1],
        ],
        dtype=bool,
    )
    np.savez(
        path,
        x_gcn=x,
        physics_raw_features=x.copy(),
        y_gcn=y,
        y_critical=y.copy(),
        loss_mask=mask,
        seed=np.asarray([1, 1, 1, 2, 2, 3, 3], dtype=np.int64),
        split=np.asarray(["train", "train", "train", "validation", "validation", "test", "test"]),
        sample_type=np.asarray(["S0", "S1", "S1", "S0", "S1", "S0", "S1"]),
        active_first_line=np.asarray(["", "L001", "", "", "L002", "", "L002"]),
        current_outage_labels=np.asarray(["", "L001", "L003,L004", "", "L002", "", "L002"]),
        line_labels=LINE_LABELS,
        branch_from_bus=np.asarray([1, 2, 3, 4], dtype=np.int64),
        branch_to_bus=np.asarray([2, 3, 4, 1], dtype=np.int64),
        feature_names=np.asarray(
            ["branch_status_offline", "relay_loading_ratio", "abs_flow", "max_terminal_load"],
            dtype=str,
        ),
    )


def write_truth_fixture(truth_path: Path, first_path: Path) -> None:
    pd.DataFrame(
        [
            {
                "scenario_id": 1,
                "seed": 9,
                "path": "L001->L002",
                "first_line": "L001",
                "second_line": "L002",
                "critical": True,
                "critical_mechanism": "relay_cascade",
                "total_load_shed_mw": 10.0,
                "valid_ordered_n2": True,
                "first_step_critical": False,
            },
            {
                "scenario_id": 1,
                "seed": 9,
                "path": "L001->L003",
                "first_line": "L001",
                "second_line": "L003",
                "critical": False,
                "critical_mechanism": "non_critical",
                "total_load_shed_mw": 0.0,
                "valid_ordered_n2": True,
                "first_step_critical": False,
            },
            {
                "scenario_id": 1,
                "seed": 9,
                "path": "L003->L002",
                "first_line": "L003",
                "second_line": "L002",
                "critical": True,
                "critical_mechanism": "island_only",
                "total_load_shed_mw": 4.0,
                "valid_ordered_n2": True,
                "first_step_critical": False,
            },
            {
                "scenario_id": 1,
                "seed": 9,
                "path": "L003->L001",
                "first_line": "L003",
                "second_line": "L001",
                "critical": True,
                "critical_mechanism": "relay_cascade",
                "total_load_shed_mw": 2.0,
                "valid_ordered_n2": True,
                "first_step_critical": False,
            },
        ]
    ).to_csv(truth_path, index=False)
    pd.DataFrame(
        [
            {
                "scenario_id": 1,
                "seed": 9,
                "first_line": "L001",
                "first_step_critical": False,
                "first_step_total_load_shed_mw": 0.0,
            },
            {
                "scenario_id": 1,
                "seed": 9,
                "first_line": "L002",
                "first_step_critical": True,
                "first_step_total_load_shed_mw": 10.0,
            },
            {
                "scenario_id": 1,
                "seed": 9,
                "first_line": "L003",
                "first_step_critical": False,
                "first_step_total_load_shed_mw": 0.0,
            },
        ]
    ).to_csv(first_path, index=False)


def test_n1_residual_annotation_preserves_critical_labels(tmp_path: Path) -> None:
    truth_path = tmp_path / "truth.csv"
    first_path = tmp_path / "first.csv"
    write_truth_fixture(truth_path, first_path)
    truth = load_valid_truth(truth_path)
    annotated = annotate_n1_residual(truth, load_first_step_summary(first_path))
    assert annotated["critical"].tolist() == truth["critical"].tolist()
    assert annotated.set_index("path").loc["L001->L002", "n1_second"]
    assert not annotated.set_index("path").loc["L003->L001", "n1_second"]
    assert int(annotated["residual_ordered_n2"].sum()) == 2


def test_audit_writes_structural_counts_without_score_table(tmp_path: Path) -> None:
    truth_path = tmp_path / "truth.csv"
    first_path = tmp_path / "first.csv"
    write_truth_fixture(truth_path, first_path)
    args = parse_audit_args(
        [
            "--fulltruth-csv",
            str(truth_path),
            "--first-step-summary-csv",
            str(first_path),
            "--score-table-csv",
            str(tmp_path / "missing_scores.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )
    result = analyze(args)
    assert result["num_valid_ordered_n2_paths"] == 4
    assert result["tier_a_paths"] == 2
    assert result["tier_a_critical_paths"] == 2
    assert result["residual_paths"] == 2
    assert result["residual_critical_paths"] == 1
    assert (args.output_dir / "ieee118_n1_residual_audit_summary.json").exists()


def test_residual_labels_mask_n1_lines_and_unknown_s0_targets(tmp_path: Path) -> None:
    source = tmp_path / "source.npz"
    write_pilot_fixture(source)
    data = np.load(source, allow_pickle=True)
    converted = build_residual_labels(data)
    y = converted["y_residual_reachable"]
    mask = converted["loss_mask"]

    assert not mask[1, 1]  # seed 1 N-1-critical L002 is never a residual second candidate
    assert mask[1, 2] and y[1, 2] == 1
    assert mask[0, 0] and y[0, 0] == 1  # S1(L001) proves residual reachability at S0
    assert not mask[0, 2]  # ambiguous L003,L004 active outage does not become a false S0 label
    assert converted["active_first_line_source"][2] == "unknown"


def test_converter_keeps_seed_splits_and_writes_schema(tmp_path: Path) -> None:
    source = tmp_path / "ieee118_paper_gcn_dataset.npz"
    write_pilot_fixture(source)
    normalizer = tmp_path / "ieee118_paper_gcn_feature_normalizer.json"
    normalizer.write_text(
        json.dumps(
            {
                name: {"mean": 0.0, "std": 1.0}
                for name in ["branch_status_offline", "relay_loading_ratio", "abs_flow", "max_terminal_load"]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "converted"
    metadata = convert(
        argparse.Namespace(
            source_dataset_npz=source,
            source_normalizer_json=normalizer,
            output_dir=out,
        )
    )
    assert metadata["train_seeds"] == [1]
    assert metadata["validation_seeds"] == [2]
    assert metadata["test_seeds"] == [3]
    assert metadata["num_s1_active_first_line_unknown"] == 1
    converted = np.load(out / "ieee118_residual_reachable_gcn_dataset.npz", allow_pickle=True)
    assert "y_residual_reachable" in converted.files
    assert "n1_critical_mask" in converted.files
    assert (out / "ieee118_residual_reachable_dataset_schema.md").exists()


def test_n1_gated_order_and_threshold_metrics() -> None:
    score = pd.DataFrame(
        {
            "path": ["A", "B", "C", "D"],
            "n1_second": [False, True, False, True],
            "p_shed_second": [0.99, 0.20, 0.80, 0.10],
            "critical": [True, True, False, True],
            "relay_cascade": [True, False, False, True],
            "island_only": [False, True, False, False],
            "total_load_shed_mw": [1.0, 2.0, 0.0, 3.0],
        }
    )
    ranked = order_n1_gated(score, "p_shed_second")
    assert ranked["path"].tolist()[:2] == ["B", "D"]
    rows, thresholds = evaluate_ranking("toy", ranked)
    assert thresholds["K100"] == 3
    assert {"recall_critical", "recall_relay_cascade", "recall_island_only"}.issubset(rows.columns)


def test_n1_gate_preserves_baseline_order_inside_each_tier() -> None:
    baseline = pd.DataFrame(
        {
            "path": ["A", "B", "C", "D", "E"],
            "n1_second": [False, True, False, True, False],
        }
    )
    assert apply_n1_gate(baseline)["path"].tolist() == ["B", "D", "A", "C", "E"]


def test_random_threshold_summary_reports_mean_and_std() -> None:
    truth = pd.DataFrame(
        {
            "path": [f"P{i}" for i in range(20)],
            "critical": [i in {0, 3, 7, 11} for i in range(20)],
            "relay_cascade": [False] * 20,
            "island_only": [False] * 20,
            "total_load_shed_mw": [0.0] * 20,
            "n1_second": [i in {0, 3} for i in range(20)],
        }
    )
    result = random_threshold_summary(truth, [1, 2, 3], n1_cost=4, gated=True)
    assert result["method"] == "N1_gate_plus_random"
    assert result["num_random_seeds"] == 3
    assert result["total_physical_K90"] == pytest.approx(result["K90"] + 4)
    assert result["K90_std"] >= 0.0


def test_future_paper_dataset_contract_records_active_first_line() -> None:
    rows: list[dict] = []
    append_sample(
        rows,
        np.zeros((4, 4), dtype=np.float32),
        np.zeros(4, dtype=np.int64),
        np.ones(4, dtype=bool),
        seed=1,
        sample_type="S1",
        split="train",
        current_outages={"L001", "L004"},
        line_labels=LINE_LABELS.tolist(),
        active_first_line="L001",
    )
    assert rows[0]["active_first_line"] == "L001"


def test_training_wrapper_uses_original_model_and_configurable_k(tmp_path: Path) -> None:
    try:
        symbols = load_original_rts79_gcn_symbols()
    except RuntimeError as exc:
        pytest.skip(f"torch unavailable in this Python environment: {exc}")
    assert symbols["PaperStyleRts79Gcn"].__name__ == "PaperStyleRts79Gcn"

    source = tmp_path / "source.npz"
    write_pilot_fixture(source)
    data = np.load(source, allow_pickle=True)
    converted = build_residual_labels(data)
    payload = {name: data[name] for name in data.files if name not in {"y_gcn", "loss_mask"}}
    payload["y_gcn"] = converted["y_residual_reachable"]
    payload["loss_mask"] = converted["loss_mask"]
    dataset = tmp_path / "residual.npz"
    np.savez(dataset, **payload)
    metrics = train(
        argparse.Namespace(
            dataset_npz=dataset,
            output_dir=tmp_path / "training",
            epochs=1,
            batch_size=2,
            learning_rate=0.005,
            positive_weight=2.0,
            k_gcn=2,
            first_layer_channels=4,
            second_layer_channels=2,
            random_seed=7,
            prediction_batch_size=16,
        )
    )
    assert metrics["model_class"] == "PaperStyleRts79Gcn"
    assert metrics["model_core_modified"] is False
    assert metrics["train_config"]["k_gcn"] == 2
    assert metrics["method_name"] != "GCN_smoke"
    assert metrics["checkpoint_selection_metric"] == "validation_average_precision"
    assert metrics["best_epoch"] == 1
    assert np.isfinite(metrics["best_validation_average_precision"])


def test_compact_summarizer_selects_k_by_validation_ap(tmp_path: Path) -> None:
    run_root = tmp_path / "runs"
    train_dir = run_root / "training_k6"
    eval_dir = run_root / "eval_k6"
    train_dir.mkdir(parents=True)
    eval_dir.mkdir(parents=True)
    (train_dir / "ieee118_residual_reachable_gcn_k6_metrics.json").write_text(
        json.dumps(
            {
                "effective_two_layer_max_hops": 12,
                "best_epoch": 4,
                "best_validation_average_precision": 0.4,
                "classification_metrics": {
                    "test": {"average_precision": 0.3},
                    "S0": {"average_precision": 0.8},
                    "S1": {"average_precision": 0.2},
                },
            }
        ),
        encoding="utf-8",
    )
    thresholds = []
    for method, offset in (
        ("N1_gate_plus_RTS79_residual_reachable_GCN_path_prob", 0),
        ("N1_gate_plus_RTS79_residual_reachable_GCN_second_only", -1),
    ):
        thresholds.append(
            {
                "method": method,
                "universe": "full",
                "total_paths": 20,
                "total_critical": 4,
                "n1_prescreen_evaluations": 4,
                "K90": 10 + offset,
                "K95": 12 + offset,
                "K99": 15 + offset,
                "K100": 18 + offset,
                "total_physical_K90": 14 + offset,
                "total_physical_K95": 16 + offset,
                "total_physical_K99": 19 + offset,
                "total_physical_K100": 22 + offset,
            }
        )
    (eval_dir / "ieee118_n1_gated_thresholds.json").write_text(json.dumps(thresholds), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "method": row["method"],
                "K": 100,
                "critical_hit_count": 4,
                "recall_critical": 1.0,
            }
            for row in thresholds
        ]
    ).to_csv(eval_dir / "ieee118_n1_gated_search_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "method": row["method"],
                "candidate_evaluations": 10,
                "critical_paths_found": 4,
            }
            for row in thresholds
        ]
    ).to_csv(eval_dir / "ieee118_n1_gated_curve_points.csv", index=False)

    result = summarize(
        argparse.Namespace(
            run_root=run_root,
            output_dir=tmp_path / "compact",
            k_values=[6],
            selected_k=None,
        )
    )
    assert result["selected_k_gcn"] == 6
    assert result["primary_protocol_method"].endswith("path_prob")
    assert result["diagnostic_ablation_method"].endswith("second_only")
    assert (tmp_path / "compact" / "ieee118_n1_residual_reachable_summary.json").exists()
