import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from pypower.idx_brch import RATE_A


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "generate_ieee118_ordered_n2_fulltruth.py"
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(SCRIPT.parent))

from case_adapter import build_case_adapter
from generate_ieee118_ordered_n2_fulltruth import (
    apply_ieee118_load_scenario,
    apply_thermal_limit_mode,
    select_ordered_n2_paths,
)


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
        "max_event_loading_ratio",
        "max_pre_redispatch_loading_ratio",
        "num_relay_trips",
        "relay_trip_labels",
        "num_passive_outages",
        "has_overload_cascade",
        "critical_mechanism",
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
    assert config["limit_mode"] == "original_rate_a"


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


def test_ieee118_fulltruth_generator_retry_errors_recomputes_error_rows(tmp_path):
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

    summary_path = output_dir / "ieee118_fulltruth_summary.csv"
    table = pd.read_csv(summary_path)
    table["error"] = table["error"].astype(object)
    table.loc[0, "converged"] = False
    table.loc[0, "error"] = "forced retry"
    table.to_csv(summary_path, index=False, encoding="utf-8-sig")

    retry = subprocess.run(
        base_cmd + ["--resume", "--retry-errors"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert retry.returncode == 0, retry.stderr

    retried = pd.read_csv(summary_path)
    assert len(retried) == 5
    assert "forced retry" not in retried["error"].fillna("").tolist()


def test_flow_scaled_thermal_limits_modify_rate_a_and_original_keeps_rate_a():
    adapter = build_case_adapter("ieee118")
    scenario_case = apply_ieee118_load_scenario(adapter.case, seed=20260708, load_scale=1.0)

    original = apply_thermal_limit_mode(
        scenario_case,
        limit_mode="original_rate_a",
        flow_limit_scale=1.3,
        min_rate_a=25.0,
    )
    scaled = apply_thermal_limit_mode(
        scenario_case,
        limit_mode="flow_scaled",
        flow_limit_scale=1.3,
        min_rate_a=25.0,
    )

    assert (original["branch"][:, RATE_A] == scenario_case["branch"][:, RATE_A]).all()
    assert not (scaled["branch"][:, RATE_A] == scenario_case["branch"][:, RATE_A]).all()
    assert scaled["branch"][:, RATE_A].min() >= 25.0


def test_flow_scaled_generator_outputs_relay_mechanism_fields(tmp_path):
    output_dir = tmp_path / "ieee118_flow_scaled"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seeds",
            "20260708",
            "--max-paths",
            "5",
            "--limit-mode",
            "flow_scaled",
            "--flow-limit-scale",
            "1.30",
            "--min-rate-a",
            "25",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    table = pd.read_csv(output_dir / "ieee118_fulltruth_summary.csv")
    assert {
        "max_event_loading_ratio",
        "max_pre_redispatch_loading_ratio",
        "num_relay_trips",
        "relay_trip_labels",
        "num_passive_outages",
        "has_overload_cascade",
        "critical_mechanism",
    }.issubset(table.columns)
    config = json.loads((output_dir / "ieee118_fulltruth_config.json").read_text(encoding="utf-8"))
    assert config["limit_mode"] == "flow_scaled"
    assert config["flow_limit_scale"] == 1.3
    assert config["min_rate_a"] == 25.0


def test_ieee118_random_sample_generator_writes_unique_paths(tmp_path):
    output_dir = tmp_path / "ieee118_random_sample"
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--seeds",
            "20260708",
            "--sample-mode",
            "random",
            "--sample-size",
            "5",
            "--sample-seed",
            "20260708",
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    table = pd.read_csv(output_dir / "ieee118_fulltruth_summary.csv")
    assert len(table) == 5
    assert table["path"].nunique() == 5

    config = json.loads((output_dir / "ieee118_fulltruth_config.json").read_text(encoding="utf-8"))
    assert config["sample_mode"] == "random"
    assert config["sample_size"] == 5
    assert config["sample_seed"] == 20260708
    assert config["selected_paths_per_scenario"] == 5


def test_ieee118_random_path_sampling_is_reproducible_and_seeded():
    adapter = build_case_adapter("ieee118")
    first = select_ordered_n2_paths(
        adapter.line_labels,
        max_paths=None,
        sample_mode="random",
        sample_size=20,
        sample_seed=20260708,
    )
    repeat = select_ordered_n2_paths(
        adapter.line_labels,
        max_paths=None,
        sample_mode="random",
        sample_size=20,
        sample_seed=20260708,
    )
    different = select_ordered_n2_paths(
        adapter.line_labels,
        max_paths=None,
        sample_mode="random",
        sample_size=20,
        sample_seed=20260709,
    )

    assert first == repeat
    assert first != different
    assert len(first) == 20
    assert len(set(first)) == 20
