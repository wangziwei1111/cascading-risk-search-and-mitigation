import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"
TEMPLATE_DIR = BASE / "manual_review_templates"
TARGETS_JSON = BASE / "ieee39_bus_fault_all_remaining_targets.json"
TARGETS_MD = BASE / "ieee39_bus_fault_all_remaining_targets.md"
COMMANDS_MD = BASE / "all_remaining_manual_gui_wiring_commands.md"
SCHEMA_JSON = BASE / "batch_manual_connection_evidence_schema.json"
GATE_MD = BASE / "batch_gate_sequence.md"
DOC = ROOT / "docs/ieee39_all_remaining_bus_fault_manual_wiring_plan.md"


NORMAL_BUSES = [*(f"B{i}" for i in range(1, 16)), *(f"B{i}" for i in range(17, 26)), *(f"B{i}" for i in range(27, 39))]
ALL_NEW_BUSES = NORMAL_BUSES + ["B16"]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def test_all_remaining_target_plan_counts() -> None:
    assert TARGETS_JSON.exists()
    assert TARGETS_MD.exists()
    payload = _read_json(TARGETS_JSON)
    assert payload["batch_id"] == "bus_fault_all_remaining_manual_wiring"
    assert payload["existing_bus_fault_candidates"] == ["B39", "B26"]
    assert payload["current_candidate_count"] == 42
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["normal_target_buses"] == NORMAL_BUSES
    assert payload["special_target_buses"] == ["B16"]
    assert payload["all_new_target_buses"] == ALL_NEW_BUSES
    assert payload["num_normal_targets"] == 36
    assert payload["num_special_targets"] == 1
    assert payload["num_all_new_targets"] == 37
    assert set(payload["excluded_from_wiring"]) == {"B39", "B26"}
    assert "B26" not in payload["all_new_target_buses"]
    assert "B39" not in payload["all_new_target_buses"]
    assert payload["should_run_smoke_now"] is False
    assert payload["should_export_labels_now"] is False
    assert payload["should_train_now"] is False
    assert payload["gcn_usefulness_audit_now"] is False


def test_each_target_has_initial_manual_template() -> None:
    for bus in ALL_NEW_BUSES:
        path = TEMPLATE_DIR / f"manual_bus_fault_injection_review_template_{bus}.json"
        assert os.path.exists(_long(path)), bus
        payload = _read_json(path)
        assert payload["target_bus"] == bus
        assert payload["batch_id"] == "bus_fault_all_remaining_manual_wiring"
        assert payload["suggested_fault_block_name"] == f"Grid/Fault_{bus}_TEMP"
        assert payload["temp_model_path"].endswith(f"IEEE39BusSystem_dynamic_experiment_wrapper_bus_fault_{bus}_TEMP_LOCAL_ONLY.slx")
        assert payload["human_verified_injection_point"] is False
        assert payload["safe_to_run_smoke_recommendation"] is False
        assert payload["simulink_smoke_run"] is False
        assert payload["smoke_success"] is False
        assert payload["candidate_label_exported"] is False
        assert payload["labels_exported"] is False
        assert payload["gcn_trained"] is False
        assert payload["reranker_retrained"] is False
        assert payload["temporary_model_committed"] is False
        assert payload["source_slx_modified"] is False
        if bus == "B16":
            assert payload["special_handling"] is True
            assert payload["special_handling_reason"]
        else:
            assert payload["special_handling"] is False
            assert payload["special_handling_reason"] == ""


def test_batch_command_schema_gate_and_docs_exist() -> None:
    assert COMMANDS_MD.exists()
    assert SCHEMA_JSON.exists()
    assert GATE_MD.exists()
    assert DOC.exists()
    schema = _read_json(SCHEMA_JSON)
    for required in [
        "batch_id",
        "target_bus",
        "special_handling",
        "temp_model_path",
        "human_verified_injection_point",
        "safe_to_run_smoke_recommendation",
        "simulink_smoke_run",
        "smoke_success",
        "candidate_label_exported",
        "labels_exported",
        "gcn_trained",
        "reranker_retrained",
        "failed_checks",
        "next_action",
    ]:
        assert required in schema["required"]
    commands = _read_text(COMMANDS_MD)
    assert "B16 Special Warning" in commands
    assert "Grid/Fault_B16_TEMP" in commands
    assert "SimulationCommand', 'update'" in commands
    assert "Do not press Run" in commands


def test_docs_keep_preparation_only_language() -> None:
    text = "\n".join(
        [
            _read_text(TARGETS_MD),
            _read_text(COMMANDS_MD),
            _read_text(GATE_MD),
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "does not run simulink",
        "does not export labels",
        "does not train gcn",
        "does not run a gcn usefulness audit",
        "candidate labels, not formal labels",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "this round ran simulink",
        "labels_exported=true",
        "labels exported=true",
        "gcn_trained=true",
        "gcn trained=true",
        "gcn usefulness audit was run",
        "human verified=true",
        "smoke success=true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in normalized


def test_no_forbidden_large_artifacts_are_tracked_for_batch_package() -> None:
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden = [".slx", ".slxc", ".mat", "slprj", "raw_trajector", "full_timeseries", "local_lab_copies"]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden)]
    assert bad == []
