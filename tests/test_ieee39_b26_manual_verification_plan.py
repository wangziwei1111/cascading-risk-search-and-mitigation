import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_DOC = ROOT / "docs/ieee39_b26_manual_bus_fault_verification_plan.md"
COMMANDS = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/b26_manual_gui_check_commands.md"
)
TEMPLATE = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans/manual_bus_fault_injection_review_template_B26.json"
)


def test_b26_manual_plan_doc_exists_and_keeps_b26_unverified():
    text = PLAN_DOC.read_text(encoding="utf-8").lower()
    assert PLAN_DOC.exists()
    assert "b26 is the next priority bus-fault sample" in text
    assert "b26 has a human-verified injection point" in text
    assert "b26 is not smoke success" in text
    assert "b26 is not a candidate label" in text
    assert "grid/fault_b26_temp" in text
    assert "update diagram passed" in text
    for required in [
        "grid/bus26_1",
        "grid/bus26_2",
        "grid/b25 to b26",
        "grid/b26 to b28",
        "grid/b26 to b29",
        "grid/b27 to b26",
        "update diagram only",
        "does not run simulink",
        "does not submit `.slx`",
        "does not train gcn",
        "does not retrain the reranker",
    ]:
        assert required in text


def test_b26_review_template_remains_unverified():
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert payload["target_bus"] == "B26"
    assert payload["human_verified_injection_point"] is True
    assert payload["safe_to_run_smoke_recommendation"] is True
    assert payload["update_diagram_success"] is True
    assert payload["human_verified"] is True
    assert payload["suggested_fault_block_name"] == "Grid/Fault_B26_TEMP"
    assert payload["suggested_fault_start_s"] == 0.5
    assert payload["suggested_duration_s"] == 0.08
    assert "Grid/Bus26_1" in payload["candidate_busbar_paths"]
    assert "Grid/Bus26_2" in payload["candidate_busbar_paths"]
    assert payload["expected_fault_block_found"] is True
    assert payload["observed_parallel_fault_connected_to_b26"] is True
    assert payload["observed_parallel_fault_block_path"] == "Grid/Fault_B26_TEMP"
    assert "readiness" in payload["next_action"].lower()


def test_b26_manual_commands_exist_and_do_not_run_simulation():
    text = COMMANDS.read_text(encoding="utf-8").lower()
    assert COMMANDS.exists()
    assert "grid/bus26_1" in text
    assert "grid/bus26_2" in text
    assert "get_param" in text
    assert "portconnectivity" in text
    assert "fault_b26_temp" in text
    assert "simulationcommand', 'update" in text
    assert "do not run simulation" in text
    assert "simulationcommand', 'start" not in text


def test_b26_docs_do_not_overstate_status():
    combined = "\n".join(
        [
            PLAN_DOC.read_text(encoding="utf-8").lower(),
            COMMANDS.read_text(encoding="utf-8").lower(),
        ]
    )
    for forbidden in [
        "b26 smoke success = true",
        "b26 candidate label exported = true",
        "gcn trained",
        "reranker retrained",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in combined


def test_no_forbidden_artifacts_tracked_for_b26_manual_prep():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/temp_lab_plans"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden = [".slx", ".slxc", "slprj", ".mat", "raw_trajectories", "full_timeseries", "local_lab_copies"]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden)]
