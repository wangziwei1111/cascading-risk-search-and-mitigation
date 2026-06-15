from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"
SMOKE = BASE / "temp_lab_smoke_outputs"
DOCS = [
    "docs/ieee39_b39_temporary_bus_fault_smoke.md",
    "docs/ieee39_b39_temp_smoke_readiness.md",
    "docs/ieee39_bus_fault_b39_manual_review_result.md",
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/gcn_pio_validation_log.md",
]


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _summary_row() -> dict[str, str]:
    with (SMOKE / "ieee39_bus_fault_temp_lab_smoke_summary.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    return rows[0]


def _boolish(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def test_b39_smoke_summary_and_report_exist() -> None:
    for path in [
        SMOKE / "ieee39_bus_fault_temp_lab_smoke_summary.csv",
        SMOKE / "ieee39_bus_fault_temp_lab_smoke_report.json",
        SMOKE / "ieee39_bus_fault_temp_lab_smoke_report.md",
    ]:
        assert path.exists()
        assert path.stat().st_size > 0


def test_b39_smoke_report_preserves_boundaries() -> None:
    report = _json(SMOKE / "ieee39_bus_fault_temp_lab_smoke_report.json")
    assert report["preview_only"] is True
    assert report["target_bus"] == "B39"
    assert report["smoke_executed"] is True
    assert report["scenario_ids_requested"] == ["BF_B39_TEMP_SMOKE"]
    assert report["whether_source_slx_modified"] is False
    assert report["whether_temporary_slx_committed"] is False
    assert report["whether_formal_label_gate_changed"] is False
    assert report["whether_v2_candidate_count_changed"] is False
    assert report["whether_labels_exported"] is False
    assert report["whether_gcn_trained"] is False
    assert report["whether_reranker_retrained"] is False
    assert report["whether_l12_touched"] is False


def test_b39_smoke_success_or_failure_is_explicit() -> None:
    row = _summary_row()
    assert row["scenario_id"] == "BF_B39_TEMP_SMOKE"
    assert row["target_bus"] == "B39"
    assert row["source_slx_modified"] == "False"
    assert row["temporary_slx_committed"] == "False"
    if _boolish(row["simulation_success"]):
        assert row["measurement_extraction_status"] == "voltage_speed_angle"
        assert "frequency=generator_speed_proxy" in row["signal_source_summary"]
        assert _boolish(row["training_ready_candidate_smoke"])
    else:
        assert row["timeout_or_error_message"].strip()
        assert not _boolish(row["training_ready_candidate_smoke"])


def test_b39_smoke_docs_do_not_overclaim() -> None:
    text = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for required in [
        "actual b39 temporary smoke",
        "bf_b39_temp_smoke",
        "no labels were exported",
        "no gcn",
        "reranker",
        "35 / 33 / 33",
        "v2 candidate count",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in text
    for forbidden in [
        "is a final dynamic performance conclusion",
        "exported bus-fault labels",
        "trained gcn model",
        "reranker was retrained",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade protection completed",
    ]:
        assert forbidden not in text


def test_no_forbidden_b39_smoke_artifacts_are_tracked() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    forbidden_tokens = [
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    offenders = [path for path in tracked if any(token in path.lower() for token in forbidden_tokens)]
    assert offenders == []
