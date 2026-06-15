from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"
PLANS = BASE / "temp_lab_plans"
SMOKE = BASE / "temp_lab_smoke_outputs"
DOCS = [
    "docs/ieee39_b39_temp_smoke_readiness.md",
    "docs/ieee39_bus_fault_b39_manual_review_result.md",
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/gcn_pio_validation_log.md",
]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_b39_human_readiness_artifacts_exist_and_preserve_boundaries() -> None:
    json_path = PLANS / "ieee39_bus_fault_b39_human_verified_readiness.json"
    md_path = PLANS / "ieee39_bus_fault_b39_human_verified_readiness.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = _load_json(json_path)
    assert payload["target_bus"] == "B39"
    assert payload["human_verified_injection_point"] is True
    assert payload["safe_to_run_smoke_recommendation"] is True
    assert payload["manual_review_recommendation"] == "manual_review_supports_next_round_inventory_update"
    assert payload["selected_injection_block_path"] == "Grid/Bus39"
    assert payload["selected_fault_block_path"] == "Grid/Fault_B39_TEMP"
    assert payload["fault_start_s"] == 0.5
    assert payload["fault_clear_s"] == 0.58
    assert payload["duration_s"] == 0.08
    assert payload["update_diagram_success"] is True
    assert payload["source_model_saved"] is False
    assert payload["temporary_model_committed"] is False
    assert payload["source_slx_modified"] is False
    assert payload["temporary_slx_committed"] is False
    assert payload["simulink_smoke_run"] is False
    assert payload["smoke_success"] is False
    assert payload["labels_exported"] is False
    assert payload["gcn_trained"] is False
    assert payload["reranker_retrained"] is False
    assert payload["formal_label_gate"] == "35 / 33 / 33"
    assert payload["v2_candidate_count"] == 40
    assert payload["b26_status"] == "unverified"
    assert payload["l12_touched"] is False


def test_b39_dry_run_readiness_artifacts_exist_and_are_not_smoke_results() -> None:
    json_path = SMOKE / "ieee39_b39_temp_smoke_dry_run_readiness.json"
    md_path = SMOKE / "ieee39_b39_temp_smoke_dry_run_readiness.md"
    assert json_path.exists()
    assert md_path.exists()
    payload = _load_json(json_path)
    assert payload["target_bus"] == "B39"
    assert payload["dry_run"] is True
    assert payload["actual_simulink_run"] is False
    assert payload["would_run_smoke_next_round"] is True
    assert payload["readiness_status"] == "ready_for_next_round_temp_smoke"
    assert payload["simulink_smoke_run"] is False
    assert payload["smoke_success"] is False
    assert payload["labels_exported"] is False
    assert payload["gcn_trained"] is False
    assert payload["reranker_retrained"] is False
    assert payload["formal_label_gate"] == "35 / 33 / 33"
    assert payload["v2_candidate_count"] == 40
    assert payload["selected_fault_block_path"] == "Grid/Fault_B39_TEMP"
    assert payload["selected_injection_block_path"] == "Grid/Bus39"


def test_docs_record_readiness_without_overclaiming() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for required in [
        "readiness",
        "ready_for_next_round_temp_smoke",
        "actual_simulink_run = false",
        "smoke_success = false",
        "labels_exported = false",
        "gcn_trained = false",
        "reranker_retrained = false",
        "35 / 33 / 33",
        "v2 candidate count",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in joined
    for forbidden in [
        "b39 smoke success",
        "smoke success completed",
        "exported bus-fault labels",
        "trained gcn model",
        "reranker was retrained",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade protection completed",
    ]:
        assert forbidden not in joined


def test_no_forbidden_b39_readiness_artifacts_are_tracked() -> None:
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
