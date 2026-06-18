from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_controlled_execution_backend_repair"
DOC = ROOT / "docs/ieee39_controlled_execution_backend_repair.md"


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path):
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8", errors="ignore") as handle:
        return handle.read()


def test_backend_repair_runner_runs_in_dry_run_mode() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--max-pairs",
            "32",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_backend_repair_runner_rejects_batch_execute_after_entrypoint_repair() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--max-pairs",
            "32",
            "--execute",
            "--write-report",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "batch mode" in (result.stderr + result.stdout).lower()


def test_backend_repair_runner_rejects_more_than_32() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--max-pairs",
            "33",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "cannot exceed 32" in (result.stderr + result.stdout)


def test_backend_repair_artifacts_exist() -> None:
    expected = [
        "backend_repair_summary.json",
        "backend_repair_summary.md",
        "backend_repair_summary.csv",
        "backend_execution_contract.json",
        "backend_execution_contract.md",
        "manual_execution_instruction_pack.md",
        "selected_pair_backend_readiness_matrix.json",
        "selected_pair_backend_readiness_matrix.md",
        "selected_pair_backend_readiness_matrix.csv",
        "no_leakage_backend_repair_audit.json",
        "no_leakage_backend_repair_audit.md",
        "large_file_safety_backend_repair.json",
        "large_file_safety_backend_repair.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))
    assert os.path.exists(_long(ROOT / "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py"))
    assert os.path.exists(_long(ROOT / "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m"))
    assert os.path.exists(_long(ROOT / "scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py"))


def test_backend_repair_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "backend_repair_summary.json")
    expected = {
        "repair_scope": "controlled_execution_backend_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_pairs_executed": False,
        "simulink_run": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_backend_diagnosis_commit": "0d96b0c258e23f4fe5c2ec01cac2a63b5d85c06f",
        "selected_pair_count": 32,
        "python_runner_added": True,
        "matlab_entrypoint_added": True,
        "result_parser_contract_added": True,
        "evidence_writer_added": True,
        "manual_instruction_pack_added": True,
        "selected_32_only_guard_added": True,
        "full_1056_guard_added": True,
        "no_formal_label_export_guard_added": True,
        "no_training_guard_added": True,
        "no_raw_artifact_policy_added": True,
        "graceful_blocked_mode_available": True,
        "can_execute_selected_32_pairs_after_manual_approval": True,
        "can_execute_selected_32_pairs_now": False,
        "recommended_next_step": "approve execution of selected 32 pairs using the repaired backend in a separate round",
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert "manual approval" in summary["blocker_if_any"]


def test_backend_contract_manual_pack_and_readiness_matrix() -> None:
    contract = _read_json(OUT_DIR / "backend_execution_contract.json")
    matrix = _read_json(OUT_DIR / "selected_pair_backend_readiness_matrix.json")
    manual = _read_text(OUT_DIR / "manual_execution_instruction_pack.md").lower()
    assert contract["contract_scope"] == "selected_pair_execution_contract"
    assert contract["allowed_pair_count"] == 32
    assert contract["full_1056_generation_allowed"] is False
    assert contract["requires_approved_selected_pairs_only"] is True
    assert contract["requires_explicit_execute_flag"] is True
    assert contract["default_mode"] == "dry_run_or_blocked"
    assert contract["formal_label_export_policy"] is False
    assert "raw trajectories" in " ".join(contract["forbidden_outputs"])
    assert "timeout remains timeout/unknown" in contract["timeout_policy"]

    assert len(matrix) == 32
    assert all(row["mapping_ready"] is True for row in matrix)
    assert all(row["l12_special_case_flag"] is False for row in matrix)
    assert all(row["selected_32_guard_passed"] is True for row in matrix)
    assert all(row["execution_contract_ready"] is True for row in matrix)
    assert all(row["matlab_entrypoint_ready"] is True for row in matrix)
    assert all(row["parser_contract_ready"] is True for row in matrix)
    assert all(row["future_execution_ready"] is True for row in matrix)
    assert all(row["current_status"] == "ready_for_manual_approval" for row in matrix)
    with open(_long(OUT_DIR / "selected_pair_backend_readiness_matrix.csv"), newline="", encoding="utf-8") as handle:
        assert len(list(csv.DictReader(handle))) == 32

    for phrase in [
        "do not use it to train gcn",
        "do not substitute the 1056-pair plan",
        "--approved-selected-pairs-only",
        "--execute",
        "do not write raw trajectory",
        "timeout remains timeout/unknown",
        "do not export formal labels",
        "manual approval is required",
    ]:
        assert phrase in manual


def test_backend_repair_no_leakage_and_safety() -> None:
    no_leakage = _read_json(OUT_DIR / "no_leakage_backend_repair_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_backend_repair.json")
    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_future_labels_or_targets"] is True
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["proxy_relay_threshold_used_only_in_feature_generation"] is True
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["no_leakage_policy_passed"] is True
    for key in [
        "raw_trajectories_committed",
        "full_timeseries_committed",
        "mat_files_committed",
        "slx_files_committed",
        "slxc_files_committed",
        "slprj_committed",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_selected_pair_evidence_parser_keeps_unknown_null(tmp_path: Path) -> None:
    compact = tmp_path / "compact.json"
    compact.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "pair_id": "SPP001",
                        "execution_status": "timeout",
                        "pilot_label_value": 1,
                        "pilot_label_status": "timeout",
                        "timeout_or_failure_reason": "timeout",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/parse_ieee39_selected_pair_execution_evidence.py",
            "--input-json",
            str(compact),
            "--output-dir",
            str(out),
            "--strict",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )
    parsed = json.loads((out / "parsed_selected_pair_compact_evidence.json").read_text(encoding="utf-8"))
    assert parsed[0]["pilot_label_value"] is None
    assert parsed[0]["raw_trajectory_committed"] is False
    assert parsed[0]["full_timeseries_committed"] is False
    assert parsed[0]["mat_file_committed"] is False


def test_backend_repair_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_controlled_execution_backend_diagnosis.md"),
            _read_text(ROOT / "docs/ieee39_selected_single_outage_pilot_pair_execution.md"),
            _read_text(OUT_DIR / "backend_repair_summary.md"),
            _read_text(OUT_DIR / "backend_execution_contract.md"),
            _read_text(OUT_DIR / "manual_execution_instruction_pack.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "controlled execution backend repair",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute selected 32 pairs",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "selected-32-only python runner",
        "matlab two-step line-trip entrypoint skeleton",
        "result parser contract",
        "manual instruction pack",
        "execution of selected 32 pairs still requires the next round of manual approval",
        "raw trajectory, full timeseries, or .mat",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "nf06 warning is preserved",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "selected 32 pairs executed",
        "full 1056 generation completed",
        "formal labels exported",
        "proxy is a real relay setting",
        "emt simulation",
        "generator_speed_proxy is direct frequency",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_backend_repair_no_forbidden_large_artifacts_tracked() -> None:
    result = subprocess.run(
        ["git", "diff", "--name-only", "main...HEAD"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
        encoding="utf-8",
        errors="replace",
    )
    changed = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    forbidden_tokens = [
        ".venv-gcn-audit/",
        ".venv/",
        "site-packages",
        ".whl",
        ".dll",
        ".pt",
        ".pth",
        ".ckpt",
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajector",
        "full_timeseries",
        "local_lab_copies",
    ]
    for path in changed:
        assert not any(token in path for token in forbidden_tokens), path
