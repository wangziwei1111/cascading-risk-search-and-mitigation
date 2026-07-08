import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EVAL_SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "evaluate_ieee118_search_efficiency.py"
TRAIN_SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "train_ieee118_gcn_smoke.py"
sys.path.insert(0, str(EVAL_SCRIPT.parent))

from evaluate_ieee118_search_efficiency import budget_table, evaluate_order, line_order_paths, random_order_paths
from train_ieee118_gcn_smoke import LABEL_COLUMNS, input_feature_columns


def make_truth_csv(path: Path) -> pd.DataFrame:
    table = pd.DataFrame(
        [
            {"path": "L001->L002", "critical": True, "critical_mechanism": "relay_cascade", "total_load_shed_mw": 10.0},
            {"path": "L001->L003", "critical": False, "critical_mechanism": "non_critical", "total_load_shed_mw": 0.0},
            {"path": "L002->L001", "critical": True, "critical_mechanism": "island_only", "total_load_shed_mw": 5.0},
            {"path": "L002->L003", "critical": False, "critical_mechanism": "non_critical", "total_load_shed_mw": 0.0},
        ]
    )
    table.to_csv(path, index=False, encoding="utf-8-sig")
    return table


def make_step2_csv(path: Path) -> pd.DataFrame:
    rows = []
    for idx in range(40):
        rows.append(
            {
                "path": f"L{idx % 10 + 1:03d}->L{(idx + 1) % 10 + 1:03d}",
                "first_line": f"L{idx % 10 + 1:03d}",
                "second_line": f"L{(idx + 1) % 10 + 1:03d}",
                "first_line_loading_ratio": float(idx % 5) / 10.0,
                "candidate_second_line_loading_ratio": float(idx % 7) / 10.0,
                "candidate_second_line_rate_a": 100.0 + idx,
                "candidate_second_line_pf": float(idx),
                "label_critical": int(idx % 6 == 0),
                "label_relay_cascade": int(idx % 8 == 0),
            }
        )
    table = pd.DataFrame(rows)
    table.to_csv(path, index=False, encoding="utf-8-sig")
    return table


def test_search_metrics_compute_recall_precision_and_captured_shed(tmp_path):
    truth = make_truth_csv(tmp_path / "truth.csv")
    budgets = pd.DataFrame([{"budget_type": "fixed", "budget_label": "2", "K": 2}])
    order = ["L001->L002", "L001->L003", "L002->L001", "L002->L003"]

    metrics = evaluate_order("test", order, truth.assign(relay_cascade=truth["critical_mechanism"].eq("relay_cascade")), budgets)
    row = metrics.iloc[0]
    assert row["critical_hit_count"] == 1
    assert row["relay_cascade_hit_count"] == 1
    assert row["recall_critical"] == 0.5
    assert row["recall_relay_cascade"] == 1.0
    assert row["precision_at_k"] == 0.5
    assert row["captured_total_load_shed_mw"] == 10.0


def test_random_baseline_reproducible_and_seeded():
    paths = [f"path_{idx}" for idx in range(20)]
    assert random_order_paths(paths, 7) == random_order_paths(paths, 7)
    assert random_order_paths(paths, 7) != random_order_paths(paths, 8)


def test_line_order_ranking_length_matches_ieee118_space():
    labels = [f"L{idx:03d}" for idx in range(1, 187)]
    truth = pd.DataFrame({"path": [f"{first}->{second}" for first in labels for second in labels if first != second]})
    assert len(line_order_paths(truth)) == 34410


def test_gcn_smoke_feature_list_excludes_labels():
    assert not (set(input_feature_columns()) & LABEL_COLUMNS)


def test_evaluation_missing_fulltruth_has_clear_error(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--fulltruth-csv",
            str(tmp_path / "missing.csv"),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "Missing IEEE118 full-truth CSV" in completed.stderr
    assert "will not regenerate" in completed.stderr


def test_train_and_evaluate_smoke_on_small_samples(tmp_path):
    step2_csv = tmp_path / "step2.csv"
    truth_csv = tmp_path / "truth.csv"
    make_step2_csv(step2_csv)
    make_truth_csv(truth_csv)
    train_dir = tmp_path / "train"
    train = subprocess.run(
        [
            sys.executable,
            str(TRAIN_SCRIPT),
            "--step2-csv",
            str(step2_csv),
            "--max-samples",
            "30",
            "--epochs",
            "1",
            "--output-dir",
            str(train_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert train.returncode == 0, train.stderr
    assert (train_dir / "gcn_smoke_metrics.json").exists()
    assert (train_dir / "gcn_smoke_predictions.csv").exists()

    eval_dir = tmp_path / "eval"
    evaluate = subprocess.run(
        [
            sys.executable,
            str(EVAL_SCRIPT),
            "--fulltruth-csv",
            str(truth_csv),
            "--gcn-predictions-csv",
            str(train_dir / "gcn_smoke_predictions.csv"),
            "--random-seeds",
            "1",
            "2",
            "--output-dir",
            str(eval_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert evaluate.returncode == 0, evaluate.stderr
    summary = pd.read_csv(eval_dir / "search_efficiency_summary.csv")
    assert {"line_order", "random", "GCN_smoke"}.issubset(set(summary["method"]))
    config = json.loads((eval_dir / "search_efficiency_config.json").read_text(encoding="utf-8"))
    assert config["total_paths"] == 4
