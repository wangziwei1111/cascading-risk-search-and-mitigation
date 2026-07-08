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
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(IEEE118))

from convert_ieee118_step2_to_rts79_gcn_format import LEAKAGE_COLUMNS, convert_step2_to_rts79_gcn_format


def _write_step2_fixture(path: Path) -> None:
    nodes = [
        {"bus_id": 1, "Pd": 10.0},
        {"bus_id": 2, "Pd": 20.0},
        {"bus_id": 3, "Pd": 30.0},
    ]

    def edges(first: str, candidate: str) -> str:
        records = []
        for label, f_bus, t_bus, flow, rate in [
            ("L001", 1, 2, 0.0 if first == "L001" else 11.0, 100.0),
            ("L002", 2, 3, 22.0 if first != "L002" else 0.0, 100.0),
            ("L003", 1, 3, 33.0 if first != "L003" else 0.0, 100.0),
        ]:
            records.append(
                {
                    "line_label": label,
                    "from_bus": f_bus,
                    "to_bus": t_bus,
                    "rate_a": rate,
                    "abs_pf_after_first_outage": abs(flow),
                    "loading_ratio_after_first_outage": abs(flow) / rate,
                    "is_first_outage": label == first,
                    "is_candidate_second_outage": label == candidate,
                }
            )
        return json.dumps(records)

    rows = []
    for first in ["L001", "L002"]:
        for second in ["L001", "L002", "L003"]:
            if first == second:
                continue
            path_label = f"{first}->{second}"
            rows.append(
                {
                    "scenario_id": 1,
                    "seed": 20260708,
                    "path": path_label,
                    "first_line": first,
                    "second_line": second,
                    "label_critical": int(path_label == "L001->L003"),
                    "label_relay_cascade": int(path_label == "L002->L003"),
                    "edge_features_json": edges(first, second),
                    "node_features_json": json.dumps(nodes),
                }
            )
    pd.DataFrame(rows).to_csv(path, index=False)


def test_original_rts79_gcn_files_are_located() -> None:
    paper = LEGACY / "train_rts79_paper_gcn.py"
    pio = LEGACY / "train_rts79_physics_gcn.py"
    topk = LEGACY / "evaluate_rts79_pio_gcn_topk.py"
    assert paper.exists()
    assert pio.exists()
    assert topk.exists()
    text = paper.read_text(encoding="utf-8")
    assert "class PaperGraphConvolution" in text
    assert "class PaperStyleRts79Gcn" in text
    assert "CrossEntropyLoss" in text


def test_ieee118_adapter_outputs_original_gcn_contract(tmp_path: Path) -> None:
    step2 = tmp_path / "step2.csv"
    _write_step2_fixture(step2)
    out = tmp_path / "out"
    metadata = convert_step2_to_rts79_gcn_format(
        argparse.Namespace(
            step2_csv=step2,
            output_dir=out,
            beta=1.2,
            security_limit=1.0,
            max_first_lines=None,
            max_samples=None,
        )
    )
    assert metadata["num_state_samples"] == 2
    assert metadata["num_line_labels"] == 3
    assert metadata["num_path_samples"] == 4
    data = np.load(out / "ieee118_rts79_gcn_dataset.npz", allow_pickle=True)
    assert data["x_gcn"].shape == (2, 3, 9)
    assert data["y_critical"].shape == (2, 3)
    assert data["loss_mask"].sum() == 4
    path_index = pd.read_csv(out / "ieee118_rts79_gcn_path_index.csv")
    assert set(["path", "sample_index", "line_index", "label_critical", "label_relay_cascade"]).issubset(path_index.columns)


def test_ieee118_adapter_excludes_label_leakage_fields(tmp_path: Path) -> None:
    step2 = tmp_path / "step2.csv"
    _write_step2_fixture(step2)
    out = tmp_path / "out"
    convert_step2_to_rts79_gcn_format(
        argparse.Namespace(
            step2_csv=step2,
            output_dir=out,
            beta=1.2,
            security_limit=1.0,
            max_first_lines=None,
            max_samples=None,
        )
    )
    meta = json.loads((out / "ieee118_rts79_gcn_dataset_metadata.json").read_text(encoding="utf-8"))
    assert not (set(meta["feature_names"]) & LEAKAGE_COLUMNS)
    assert "label_critical" in set(meta["excluded_leakage_columns"])


def test_wrapper_references_original_model_and_defines_no_new_gcn_class() -> None:
    wrapper = IEEE118 / "train_ieee118_with_original_rts79_gcn.py"
    text = wrapper.read_text(encoding="utf-8")
    assert "PaperStyleRts79Gcn" in text
    assert "train_rts79_paper_gcn" in text
    assert "class Paper" not in text
    assert "class IEEE" not in text


def test_missing_step2_csv_error_is_clear(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "convert_ieee118_step2_to_rts79_gcn_format.py"),
            "--step2-csv",
            str(missing),
            "--output-dir",
            str(tmp_path / "out"),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert "Missing IEEE118 Step2-State CSV" in proc.stderr


def test_wrapper_blocked_torch_import_is_explicit(tmp_path: Path) -> None:
    step2 = tmp_path / "step2.csv"
    _write_step2_fixture(step2)
    out = tmp_path / "out"
    convert_step2_to_rts79_gcn_format(
        argparse.Namespace(
            step2_csv=step2,
            output_dir=out,
            beta=1.2,
            security_limit=1.0,
            max_first_lines=None,
            max_samples=None,
        )
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(IEEE118 / "train_ieee118_with_original_rts79_gcn.py"),
            "--dataset-npz",
            str(out / "ieee118_rts79_gcn_dataset.npz"),
            "--path-index-csv",
            str(out / "ieee118_rts79_gcn_path_index.csv"),
            "--output-dir",
            str(out),
            "--epochs",
            "1",
            "--allow-torch-blocked",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    metrics = json.loads((out / "original_rts79_gcn_ieee118_metrics.json").read_text(encoding="utf-8"))
    assert metrics["status"] in {"blocked_torch_import", "complete"}
    assert "PaperStyleRts79Gcn" in metrics.get("model", metrics.get("model_class", ""))
