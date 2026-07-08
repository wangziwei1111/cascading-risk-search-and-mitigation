from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from convert_ieee118_step2_to_rts79_gcn_format import convert_step2_to_rts79_gcn_format
from diagnose_torch_environment import diagnose_torch_environment
from evaluate_ieee118_search_efficiency import budget_table, evaluate_order, make_curve_points
from train_ieee118_with_original_rts79_gcn import load_original_rts79_gcn_symbols


def _write_step2_fixture(path: Path, *, num_lines: int = 4) -> None:
    nodes = [{"bus_id": idx + 1, "Pd": float(10 * (idx + 1))} for idx in range(num_lines)]

    def edge_json(first: str, second: str) -> str:
        rows = []
        for idx in range(1, num_lines + 1):
            label = f"L{idx:03d}"
            flow = 0.0 if label == first else float(5 * idx)
            rows.append(
                {
                    "line_label": label,
                    "from_bus": idx,
                    "to_bus": 1 if idx == num_lines else idx + 1,
                    "rate_a": 100.0,
                    "abs_pf_after_first_outage": abs(flow),
                    "loading_ratio_after_first_outage": abs(flow) / 100.0,
                    "is_first_outage": label == first,
                    "is_candidate_second_outage": label == second,
                }
            )
        return json.dumps(rows)

    records = []
    labels = [f"L{idx:03d}" for idx in range(1, num_lines + 1)]
    for first in labels:
        for second in labels:
            if first == second:
                continue
            path_label = f"{first}->{second}"
            records.append(
                {
                    "scenario_id": 1,
                    "seed": 20260708,
                    "path": path_label,
                    "first_line": first,
                    "second_line": second,
                    "label_critical": int(second.endswith("3")),
                    "label_relay_cascade": int(second.endswith("4")),
                    "edge_features_json": edge_json(first, second),
                    "node_features_json": json.dumps(nodes),
                }
            )
    pd.DataFrame(records).to_csv(path, index=False)


def test_torch_diagnosis_has_required_fields() -> None:
    diagnosis = diagnose_torch_environment()
    required = {
        "python_executable",
        "python_version",
        "platform",
        "sys_path",
        "path_contains_literal_E_colon_bin",
        "conda_prefix",
        "virtual_env",
        "torch_import_success",
        "torch_version",
        "torch_cuda_available",
        "torch_file",
        "torch_import_error",
    }
    assert required.issubset(diagnosis)


def test_wrapper_imports_original_model_when_torch_available() -> None:
    try:
        symbols = load_original_rts79_gcn_symbols()
    except RuntimeError:
        return
    assert symbols["PaperStyleRts79Gcn"].__name__ == "PaperStyleRts79Gcn"
    assert symbols["PaperStyleRts79Gcn"].__module__ == "train_rts79_paper_gcn"


def test_adapter_label_statistics_are_complete_for_fixture(tmp_path: Path) -> None:
    step2 = tmp_path / "step2.csv"
    _write_step2_fixture(step2, num_lines=4)
    out = tmp_path / "out"
    meta = convert_step2_to_rts79_gcn_format(
        argparse.Namespace(
            step2_csv=step2,
            output_dir=out,
            beta=1.2,
            security_limit=1.0,
            max_first_lines=None,
            max_samples=None,
        )
    )
    assert meta["num_state_samples"] == 4
    assert meta["num_line_labels"] == 4
    assert meta["num_path_samples"] == 12
    assert meta["num_critical_path_labels"] == 3
    assert meta["num_relay_cascade_path_labels"] == 3
    data = np.load(out / "ieee118_rts79_gcn_dataset.npz", allow_pickle=True)
    assert int(data["y_critical"].sum()) == 3
    assert int(data["y_relay_cascade"].sum()) == 3


def test_formal_method_name_is_not_gcn_smoke() -> None:
    truth = pd.DataFrame(
        {
            "path": ["L001->L002", "L001->L003", "L002->L001"],
            "critical": [True, False, True],
            "relay_cascade": [True, False, False],
            "total_load_shed_mw": [10.0, 0.0, 5.0],
        }
    )
    budgets = budget_table(len(truth))
    summary = evaluate_order("RTS79_GCN_reused_on_IEEE118", truth["path"].tolist(), truth, budgets)
    assert "GCN_smoke" not in set(summary["method"])
    assert set(summary["method"]) == {"RTS79_GCN_reused_on_IEEE118"}


def test_curve_points_have_plot_columns() -> None:
    truth = pd.DataFrame(
        {
            "path": ["a", "b", "c"],
            "critical": [True, False, True],
            "relay_cascade": [False, False, True],
            "total_load_shed_mw": [3.0, 0.0, 7.0],
        }
    )
    curve = make_curve_points("RTS79_GCN_reused_on_IEEE118", ["c", "a", "b"], truth)
    assert {
        "candidate_evaluations",
        "critical_paths_found",
        "relay_cascade_paths_found",
        "captured_load_shed_mw",
        "method",
    }.issubset(curve.columns)
    assert curve.iloc[-1]["critical_paths_found"] == 2
    assert curve.iloc[-1]["captured_load_shed_mw"] == 10.0


def test_large_local_csvs_are_not_tracked() -> None:
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        return
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    forbidden_suffixes = {
        "results/gcn_search/ieee118_flow_scaled_800_step2_state/ieee118_step2_state_samples.csv",
        "results/gcn_search/ieee118_flow_scaled_800_fulltruth_seed20260708/ieee118_fulltruth_summary.csv",
        "results/gcn_search/ieee118_flow_scaled_800_original_rts79_gcn_eval/original_rts79_gcn_ieee118_predictions.csv",
    }
    assert forbidden_suffixes.isdisjoint(set(tracked))
