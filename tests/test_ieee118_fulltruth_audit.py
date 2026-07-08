import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "analyze_ieee118_fulltruth.py"
SMOKE_DIR = ROOT / "results" / "gcn_search" / "ieee118_fulltruth_smoke"
STRESS_SMOKE_DIR = ROOT / "results" / "gcn_search" / "ieee118_thermal_limit_calibration" / "flow_scaled_1_30_max500"


def test_ieee118_fulltruth_audit_reads_smoke_artifact(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-dir",
            str(SMOKE_DIR),
            "--output-dir",
            str(tmp_path),
            "--top-k",
            "20",
            "50",
            "100",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    summary_path = tmp_path / "ieee118_fulltruth_audit_summary.json"
    top_path = tmp_path / "ieee118_top_load_shed_paths.csv"
    frequency_path = tmp_path / "ieee118_line_critical_frequency.csv"
    error_path = tmp_path / "ieee118_error_paths.csv"
    readme_path = tmp_path / "ieee118_fulltruth_readme.md"
    for path in [summary_path, top_path, frequency_path, error_path, readme_path]:
        assert path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["total_paths"] == 100
    assert summary["converged_paths"] == 100
    assert summary["error_paths"] == 0
    assert "critical_paths" in summary
    assert "critical_ratio" in summary
    assert "max_load_shed_path" in summary
    assert "total_load_shed_mw_describe" in summary
    assert "final_max_loading_ratio_describe" in summary
    assert set(["top_20", "top_50", "top_100"]).issubset(summary["top_load_shed_counts"])

    top_table = pd.read_csv(top_path)
    assert len(top_table) == 100
    assert {"top_rank", "top_bucket", "path", "total_load_shed_mw"}.issubset(top_table.columns)

    frequency_table = pd.read_csv(frequency_path)
    assert {"line_label", "as_first_critical_count", "as_second_critical_count"}.issubset(frequency_table.columns)

    error_table = pd.read_csv(error_path)
    assert {"path", "error"}.issubset(error_table.columns)


def test_ieee118_fulltruth_audit_reports_relay_cascade_statistics(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input-dir",
            str(STRESS_SMOKE_DIR),
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((tmp_path / "ieee118_fulltruth_audit_summary.json").read_text(encoding="utf-8"))
    assert summary["relay_cascade_paths"] > 0
    assert summary["relay_cascade_ratio"] > 0.0
    assert "island_only_paths" in summary
    assert "mixed_paths" in summary
    assert "num_relay_trips_describe" in summary
    assert "max_event_loading_ratio_describe" in summary
    assert "max_pre_redispatch_loading_ratio_describe" in summary

    relay_frequency = pd.read_csv(tmp_path / "ieee118_line_relay_trip_frequency.csv")
    relay_samples = pd.read_csv(tmp_path / "ieee118_relay_cascade_top_paths.csv")
    top_relay = pd.read_csv(tmp_path / "ieee118_top_relay_trip_paths.csv")
    assert {"line_label", "relay_trip_count"}.issubset(relay_frequency.columns)
    assert {"path", "critical_mechanism", "num_relay_trips"}.issubset(relay_samples.columns)
    assert top_relay["num_relay_trips"].max() > 0
