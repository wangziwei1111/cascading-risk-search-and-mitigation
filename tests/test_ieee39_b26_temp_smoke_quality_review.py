from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs"
QUALITY_JSON = BASE / "ieee39_b26_temp_smoke_quality_review.json"
QUALITY_MD = BASE / "ieee39_b26_temp_smoke_quality_review.md"
DOCS = [
    "docs/ieee39_b26_temp_smoke_quality_review.md",
    "docs/ieee39_b26_temporary_bus_fault_smoke.md",
    "docs/ieee39_b26_temp_smoke_readiness.md",
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_gui_manual_checklist.md",
    "docs/gcn_pio_validation_log.md",
]


def _payload() -> dict:
    return json.loads(QUALITY_JSON.read_text(encoding="utf-8"))


def test_b26_quality_review_artifacts_exist() -> None:
    for path in [QUALITY_JSON, QUALITY_MD, ROOT / "docs/ieee39_b26_temp_smoke_quality_review.md"]:
        assert path.exists()
        assert path.stat().st_size > 0


def test_b26_quality_review_passes_for_candidate_export_round() -> None:
    payload = _payload()
    assert payload["target_bus"] == "B26"
    assert payload["scenario_id"] == "BF_B26_TEMP_SMOKE"
    assert payload["simulation_success"] is True
    assert payload["physical_fault_or_breaker_action_executed"] is True
    assert payload["measurement_extraction_status"] == "voltage_speed_angle"
    assert payload["training_ready_candidate_smoke"] is True
    assert payload["signal_source_has_frequency_proxy"] is True
    assert payload["dynamic_measurement_available"] is True
    assert payload["metrics_all_finite"] is True
    assert payload["quality_review_passed_for_candidate_export"] is True


def test_b26_quality_review_numeric_fields_are_finite() -> None:
    payload = _payload()
    for key in [
        "min_voltage_pu",
        "max_voltage_pu",
        "min_frequency_hz",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
    ]:
        value = float(payload[key])
        assert math.isfinite(value), key


def test_b26_quality_review_preserves_boundaries() -> None:
    payload = _payload()
    assert payload["labels_exported"] is False
    assert payload["gcn_trained"] is False
    assert payload["reranker_retrained"] is False
    assert payload["source_slx_modified"] is False
    assert payload["temporary_slx_committed"] is False
    assert payload["l12_touched"] is False
    assert payload["old_formal_gate_preserved"] is True
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["v2_plus_b39_count_preserved"] is True
    assert payload["v2_plus_b39_count"] == 41
    assert payload["b39_status"] == "candidate_label_not_formal"


def test_b26_quality_review_docs_are_conservative() -> None:
    text = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for required in [
        "quality review",
        "quality_review_passed_for_candidate_export",
        "bf_b26_temp_smoke",
        "0.525205016184139",
        "86.3888369812931",
        "labels_exported",
        "false",
        "gcn_trained",
        "reranker_retrained",
        "35 / 33 / 33",
        "v2-plus-b39 count",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in text
    for forbidden in [
        "b26 formal label exported",
        "b26 candidate label exported = true",
        "labels_exported: `true`",
        "gcn_trained: `true`",
        "reranker_retrained: `true`",
        "trained gcn model",
        "reranker was retrained",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade protection completed",
    ]:
        assert forbidden not in text


def test_no_forbidden_b26_quality_review_artifacts_are_tracked() -> None:
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
