import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "generate_ieee118_ordered_n2_fulltruth.py"


def test_ieee118_fulltruth_generator_writes_max_paths_outputs(tmp_path):
    output_dir = tmp_path / "ieee118_fulltruth"

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seeds",
            "20260708",
            "--max-paths",
            "5",
            "--checkpoint-every",
            "2",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    summary_path = output_dir / "ieee118_fulltruth_summary.csv"
    critical_path = output_dir / "ieee118_critical_paths.csv"
    config_path = output_dir / "ieee118_fulltruth_config.json"
    assert summary_path.exists()
    assert critical_path.exists()
    assert config_path.exists()

    table = pd.read_csv(summary_path)
    expected_columns = {
        "scenario_id",
        "seed",
        "path",
        "first_line",
        "second_line",
        "converged",
        "critical",
        "total_load_shed_mw",
        "island_load_shed_mw",
        "redispatch_load_shed_mw",
        "final_max_loading_ratio",
        "final_outage_labels",
        "num_final_outages",
        "error",
    }
    assert expected_columns.issubset(table.columns)
    assert len(table) == 5
    assert table["path"].tolist() == [
        "L001->L002",
        "L001->L003",
        "L001->L004",
        "L001->L005",
        "L001->L006",
    ]
    assert table["converged"].dtype == bool
    assert table["critical"].dtype == bool

    critical_table = pd.read_csv(critical_path)
    assert expected_columns.issubset(critical_table.columns)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["case_name"] == "ieee118"
    assert config["seeds"] == [20260708]
    assert config["max_paths"] == 5
    assert config["total_candidate_paths_per_scenario"] == 186 * 185


def test_ieee118_fulltruth_generator_resume_skips_existing_rows(tmp_path):
    output_dir = tmp_path / "ieee118_fulltruth"

    base_cmd = [
        sys.executable,
        str(SCRIPT),
        "--seeds",
        "20260708",
        "--max-paths",
        "5",
        "--output-dir",
        str(output_dir),
    ]
    first = subprocess.run(base_cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    assert first.returncode == 0, first.stderr
    second = subprocess.run(base_cmd + ["--resume"], cwd=ROOT, text=True, capture_output=True, check=False)
    assert second.returncode == 0, second.stderr

    table = pd.read_csv(output_dir / "ieee118_fulltruth_summary.csv")
    assert len(table) == 5
