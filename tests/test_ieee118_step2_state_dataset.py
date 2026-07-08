import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "build_ieee118_step2_state_dataset.py"


def make_fulltruth_csv(path: Path) -> pd.DataFrame:
    table = pd.DataFrame(
        [
            {
                "scenario_id": 1,
                "seed": 20260708,
                "path": "L001->L002",
                "first_line": "L001",
                "second_line": "L002",
                "critical": True,
                "critical_mechanism": "relay_cascade",
                "has_overload_cascade": True,
                "total_load_shed_mw": 12.5,
                "num_relay_trips": 3,
                "max_event_loading_ratio": 2.0,
            },
            {
                "scenario_id": 1,
                "seed": 20260708,
                "path": "L001->L003",
                "first_line": "L001",
                "second_line": "L003",
                "critical": False,
                "critical_mechanism": "non_critical",
                "has_overload_cascade": False,
                "total_load_shed_mw": 0.0,
                "num_relay_trips": 0,
                "max_event_loading_ratio": 0.5,
            },
            {
                "scenario_id": 1,
                "seed": 20260708,
                "path": "L002->L001",
                "first_line": "L002",
                "second_line": "L001",
                "critical": True,
                "critical_mechanism": "island_only",
                "has_overload_cascade": False,
                "total_load_shed_mw": 4.0,
                "num_relay_trips": 0,
                "max_event_loading_ratio": 1.0,
            },
        ]
    )
    table.to_csv(path, index=False, encoding="utf-8-sig")
    return table


def run_builder(fulltruth_csv: Path, output_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--fulltruth-csv",
            str(fulltruth_csv),
            "--limit-mode",
            "flow_scaled",
            "--flow-limit-scale",
            "8.00",
            "--min-rate-a",
            "1.0",
            "--seed",
            "20260708",
            "--output-dir",
            str(output_dir),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_ieee118_step2_state_smoke_outputs_samples_and_schema(tmp_path):
    fulltruth = tmp_path / "fulltruth.csv"
    make_fulltruth_csv(fulltruth)
    output_dir = tmp_path / "step2"

    completed = run_builder(fulltruth, output_dir)
    assert completed.returncode == 0, completed.stderr

    sample_path = output_dir / "ieee118_step2_state_samples.csv"
    metadata_path = output_dir / "ieee118_step2_state_metadata.json"
    schema_path = output_dir / "ieee118_step2_state_feature_schema.json"
    readme_path = output_dir / "ieee118_step2_state_readme.md"
    for path in [sample_path, metadata_path, schema_path, readme_path]:
        assert path.exists()

    samples = pd.read_csv(sample_path)
    assert len(samples) == 3
    required = {
        "scenario_id",
        "seed",
        "path",
        "first_line",
        "second_line",
        "critical",
        "critical_mechanism",
        "has_overload_cascade",
        "relay_cascade",
        "total_load_shed_mw",
        "num_relay_trips",
        "max_event_loading_ratio",
        "label_critical",
        "label_relay_cascade",
        "label_load_shed_positive",
        "node_features_json",
        "edge_features_json",
        "path_features_json",
    }
    assert required.issubset(samples.columns)

    first_nodes = json.loads(samples.loc[0, "node_features_json"])
    first_edges = json.loads(samples.loc[0, "edge_features_json"])
    path_features = json.loads(samples.loc[0, "path_features_json"])
    assert {"bus_id", "Pd", "Pg", "net_injection", "component_id"}.issubset(first_nodes[0])
    assert {"line_label", "rate_a", "pf_after_first_outage", "is_candidate_second_outage"}.issubset(first_edges[0])
    assert "candidate_second_line_loading_ratio" in path_features


def test_ieee118_step2_state_labels_come_from_fulltruth(tmp_path):
    fulltruth = tmp_path / "fulltruth.csv"
    truth = make_fulltruth_csv(fulltruth)
    output_dir = tmp_path / "step2"
    completed = run_builder(fulltruth, output_dir)
    assert completed.returncode == 0, completed.stderr

    samples = pd.read_csv(output_dir / "ieee118_step2_state_samples.csv")
    merged = samples.merge(truth[["path", "critical", "critical_mechanism", "total_load_shed_mw"]], on="path")
    assert (merged["label_critical"] == merged["critical_y"].astype(int)).all()
    assert (merged["critical_mechanism_x"] == merged["critical_mechanism_y"]).all()
    assert (merged["total_load_shed_mw_x"] == merged["total_load_shed_mw_y"]).all()


def test_ieee118_step2_state_reuses_first_line_cache(tmp_path):
    fulltruth = tmp_path / "fulltruth.csv"
    make_fulltruth_csv(fulltruth)
    output_dir = tmp_path / "step2"
    completed = run_builder(fulltruth, output_dir)
    assert completed.returncode == 0, completed.stderr

    metadata = json.loads((output_dir / "ieee118_step2_state_metadata.json").read_text(encoding="utf-8"))
    assert metadata["num_samples"] == 3
    assert metadata["num_unique_first_lines"] == 2
    assert metadata["first_state_cache_misses"] == 2
    assert metadata["first_state_cache_hits"] == 1


def test_ieee118_step2_state_missing_fulltruth_has_clear_error(tmp_path):
    missing = tmp_path / "missing.csv"
    output_dir = tmp_path / "step2"
    completed = run_builder(missing, output_dir, "--max-samples", "1")

    assert completed.returncode != 0
    assert "Missing IEEE118 full-truth CSV" in completed.stderr
    assert "not tracked in git" in completed.stderr


def test_ieee118_step2_state_max_samples_smoke(tmp_path):
    fulltruth = tmp_path / "fulltruth.csv"
    make_fulltruth_csv(fulltruth)
    output_dir = tmp_path / "step2"
    completed = run_builder(fulltruth, output_dir, "--max-samples", "2")
    assert completed.returncode == 0, completed.stderr

    samples = pd.read_csv(output_dir / "ieee118_step2_state_samples.csv")
    metadata = json.loads((output_dir / "ieee118_step2_state_metadata.json").read_text(encoding="utf-8"))
    assert len(samples) == 2
    assert metadata["num_samples"] == 2
