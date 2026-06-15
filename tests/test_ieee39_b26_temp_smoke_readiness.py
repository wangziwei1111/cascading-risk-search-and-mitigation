import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans"
)
SMOKE_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_smoke_outputs"
)
HUMAN_JSON = PLAN_DIR / "ieee39_bus_fault_b26_human_verified_readiness.json"
HUMAN_MD = PLAN_DIR / "ieee39_bus_fault_b26_human_verified_readiness.md"
DRY_JSON = SMOKE_DIR / "ieee39_b26_temp_smoke_dry_run_readiness.json"
DRY_MD = SMOKE_DIR / "ieee39_b26_temp_smoke_dry_run_readiness.md"
DOCS = [
    ROOT / "docs/ieee39_b26_temp_smoke_readiness.md",
    ROOT / "docs/ieee39_b26_manual_bus_fault_review_result.md",
    ROOT / "docs/ieee39_b26_manual_bus_fault_verification_plan.md",
    ROOT / "docs/ieee39_bus_fault_temp_lab_injection.md",
    ROOT / "docs/ieee39_bus_fault_gui_manual_checklist.md",
]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_b26_human_readiness_artifacts_exist():
    for path in [HUMAN_JSON, HUMAN_MD, *DOCS]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path


def test_b26_human_readiness_is_ready_but_not_smoke_success():
    payload = _load(HUMAN_JSON)
    assert payload["target_bus"] == "B26"
    assert payload["human_verified_injection_point"] is True
    assert payload["safe_to_run_smoke_recommendation"] is True
    assert payload["manual_review_recommendation"] == "manual_review_supports_next_round_inventory_update"
    assert payload["selected_fault_block_path"] == "Grid/Fault_B26_TEMP"
    assert payload["selected_injection_block_path"] == "Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node"
    assert payload["fault_start_s"] == 0.5
    assert payload["fault_clear_s"] == 0.58
    assert payload["duration_s"] == 0.08
    assert payload["R_pn_fault"] == "1e-3 Ohm"
    assert payload["R_ng_fault"] == "1e-3 Ohm"
    assert payload["enable_temporal_fault"] is True
    assert payload["update_diagram_success"] is True
    assert payload["old_fault_still_near_b16"] is True
    assert payload["formal_label_gate"] == "35 / 33 / 33"
    assert payload["v2_plus_b39_count"] == 41
    assert payload["b39_status"] == "candidate_label_not_formal"
    assert payload["recommended_next_step"] == "run B26 temporary smoke in a separate round"
    for key in [
        "source_model_saved",
        "temporary_model_committed",
        "source_slx_modified",
        "temporary_slx_committed",
        "simulink_smoke_run",
        "smoke_success",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "l12_touched",
    ]:
        assert payload[key] is False, key


def test_b26_dry_run_readiness_is_ready_without_actual_simulation():
    for path in [DRY_JSON, DRY_MD]:
        assert path.exists(), path
        assert path.stat().st_size > 0, path
    payload = _load(DRY_JSON)
    assert payload["target_bus"] == "B26"
    assert payload["dry_run"] is True
    assert payload["would_run_smoke_next_round"] is True
    assert payload["actual_simulink_run"] is False
    assert payload["readiness_status"] == "ready_for_next_round_temp_smoke"
    assert payload["selected_fault_block_path"] == "Grid/Fault_B26_TEMP"
    assert payload["selected_injection_block_path"] == "Grid/Bus26_1 and Grid/Bus26_2 shared physical B26 node"
    assert payload["formal_label_gate"] == "35 / 33 / 33"
    assert payload["v2_plus_b39_count"] == 41
    assert payload["recommended_next_step"] == "run actual B26 temporary smoke in a separate round"
    for key in [
        "source_slx_modified",
        "temporary_slx_committed",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "simulink_smoke_run",
        "smoke_success",
        "source_model_saved",
        "temporary_model_committed",
    ]:
        assert payload[key] is False, key


def test_b26_readiness_docs_do_not_overstate_status():
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in DOCS)
    required = [
        "ready_for_next_round_temp_smoke",
        "b26 is still not smoke success",
        "b26 is still not a candidate label",
        "does not train gcn",
        "does not retrain",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]
    for phrase in required:
        assert phrase in text
    forbidden = [
        "b26 smoke success = true",
        "b26 candidate label exported = true",
        "labels_exported = true",
        "gcn_trained = true",
        "reranker_retrained = true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]
    for phrase in forbidden:
        assert phrase not in text


def test_no_forbidden_artifacts_tracked_for_b26_readiness():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden = [".slx", ".slxc", "slprj", ".mat", "raw_trajectories", "full_timeseries", "local_lab_copies"]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden)]
