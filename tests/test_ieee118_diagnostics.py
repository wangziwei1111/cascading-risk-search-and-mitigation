import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ERROR_SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "diagnose_ieee118_fulltruth_errors.py"
LIMIT_SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "audit_ieee118_branch_limits.py"
FULL_DIR = ROOT / "results" / "gcn_search" / "ieee118_fulltruth_seed20260708"


def test_ieee118_error_diagnosis_summarizes_clustered_first_lines(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    first_lines = ["L007", "L009", "L113", "L133", "L134", "L176", "L177", "L183", "L184"]
    rows = [
        {
            "path": f"{first_line}->L{second_idx:03d}",
            "first_line": first_line,
            "second_line": f"L{second_idx:03d}",
            "error": "index 13 is out of bounds for axis 1 with size 13",
        }
        for first_line in first_lines
        for second_idx in range(1, 187)
        if f"L{second_idx:03d}" != first_line
    ]
    pd.DataFrame(rows).to_csv(input_dir / "ieee118_error_paths.csv", index=False)

    completed = subprocess.run(
        [sys.executable, str(ERROR_SCRIPT), "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output_dir / "ieee118_fulltruth_error_diagnosis.json").read_text(encoding="utf-8"))
    assert summary["total_error_paths"] == 1665
    assert summary["num_error_first_lines"] == 9
    assert summary["max_errors_per_first_line"] == 185
    assert "L007" in summary["error_first_lines"]

    first_table = pd.read_csv(output_dir / "ieee118_error_by_first_line.csv")
    assert {"first_line", "error_count", "s1_reproduces_error", "s1_branch_cols"}.issubset(first_table.columns)
    assert first_table["error_count"].max() == 185


def test_ieee118_branch_limit_audit_writes_summary(tmp_path):
    completed = subprocess.run(
        [sys.executable, str(LIMIT_SCRIPT), "--output-dir", str(tmp_path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "ieee118_branch_limit_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["num_branches"] == 186
    assert summary["num_rate_a_nonpositive"] == 0
    assert summary["rate_a"]["min"] == 9900.0
    assert summary["initial_dcopf_branch_has_pf"]
    assert summary["initial_loading_ratio"]["max"] < 0.1
    assert "recommendation" in summary

    branch_table = pd.read_csv(tmp_path / "ieee118_initial_branch_loading.csv")
    assert {"line_label", "F_MW", "F_max_MW", "loading_ratio"}.issubset(branch_table.columns)


def test_ieee118_error_diagnosis_handles_empty_error_file(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    pd.DataFrame(columns=["first_line", "second_line", "path", "error"]).to_csv(
        input_dir / "ieee118_error_paths.csv",
        index=False,
    )

    completed = subprocess.run(
        [sys.executable, str(ERROR_SCRIPT), "--input-dir", str(input_dir), "--output-dir", str(output_dir)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((output_dir / "ieee118_fulltruth_error_diagnosis.json").read_text(encoding="utf-8"))
    assert summary["total_error_paths"] == 0
    assert summary["num_error_first_lines"] == 0
