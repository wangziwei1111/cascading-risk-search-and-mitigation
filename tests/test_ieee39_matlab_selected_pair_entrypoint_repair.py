from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_matlab_selected_pair_entrypoint_repair"
DOC = ROOT / "docs/ieee39_matlab_selected_pair_entrypoint_repair.md"
MATLAB_ENTRYPOINT = ROOT / "matlab/simulink_ieee39/run_ieee39_selected_pair_line_trip_sequence.m"


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


def test_entrypoint_repair_runner_writes_artifacts() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--single-pair-smoke-only",
            "--pair-id",
            "SPP001",
            "--max-pairs",
            "32",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_entrypoint_repair_artifacts_exist() -> None:
    expected = [
        "matlab_entrypoint_repair_summary.json",
        "matlab_entrypoint_repair_summary.md",
        "matlab_entrypoint_repair_summary.csv",
        "single_pair_smoke_execution_contract.json",
        "single_pair_smoke_execution_contract.md",
        "entrypoint_component_reuse_report.json",
        "entrypoint_component_reuse_report.md",
        "single_pair_smoke_candidate.json",
        "single_pair_smoke_candidate.md",
        "no_leakage_entrypoint_repair_audit.json",
        "no_leakage_entrypoint_repair_audit.md",
        "large_file_safety_entrypoint_repair.json",
        "large_file_safety_entrypoint_repair.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_entrypoint_repair_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "matlab_entrypoint_repair_summary.json")
    expected = {
        "repair_scope": "matlab_selected_pair_entrypoint_repair",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "selected_32_pairs_executed": False,
        "full_1056_generation_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_selected_32_evidence_commit": "12f07cbc4d3b35883b1dd11078c87029d5df8aac",
        "matlab_entrypoint_updated": True,
        "python_runner_updated": True,
        "parser_contract_updated": True,
        "selected_32_guard_preserved": True,
        "single_pair_smoke_mode_added": True,
        "batch_32_execution_allowed_now": False,
        "full_1056_execution_allowed_now": False,
        "can_attempt_single_pair_smoke_after_manual_approval": True,
        "can_attempt_selected_32_after_single_pair_smoke": False,
        "raw_trajectory_policy_preserved": True,
        "formal_label_export_guard_preserved": True,
        "no_training_guard_preserved": True,
        "recommended_next_step": "approve one selected pair smoke execution in a separate round",
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert "separate manual approval" in summary["blocker_if_any"]


def test_single_pair_contract_candidate_reuse_no_leakage_and_safety() -> None:
    contract = _read_json(OUT_DIR / "single_pair_smoke_execution_contract.json")
    candidate = _read_json(OUT_DIR / "single_pair_smoke_candidate.json")
    reuse = _read_json(OUT_DIR / "entrypoint_component_reuse_report.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_entrypoint_repair_audit.json")
    safety = _read_json(OUT_DIR / "large_file_safety_entrypoint_repair.json")

    assert contract["contract_scope"] == "single_pair_smoke_execution_contract"
    assert contract["allowed_pair_count"] == 1
    assert contract["selected_32_batch_execution_allowed"] is False
    assert contract["full_1056_generation_allowed"] is False
    assert contract["requires_manual_approval"] is True
    assert contract["requires_explicit_execute"] is True
    assert contract["compact_evidence_only"] is True
    assert "raw trajectories" in contract["raw_artifact_policy"]

    assert candidate["pair_id"] == "SPP001"
    assert candidate["l12_special_case_flag"] is False
    assert candidate["approved_for_execution_now"] is False
    assert candidate["requires_next_round_approval"] is True
    assert candidate["selection_bucket"] == "high_relay_ratio_pairs"

    assert "run_ieee39_multi_handwired_line_trip_suite.m" in "\n".join(reuse["reused_matlab_components"])
    assert "run_ieee39_selected_single_outage_pilot_pairs_controlled.py" in "\n".join(reuse["reused_python_components"])
    assert reuse["source_slx_modified"] is False
    assert "full 1056 batch generation" in reuse["unsafe_components_rejected"]

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
        "source_slx_modified",
        "venv_committed",
        "wheel_or_dll_committed",
        "model_files_committed",
    ]:
        assert safety[key] is False, key
    assert safety["safety_check_passed"] is True


def test_matlab_entrypoint_contains_single_pair_guards() -> None:
    text = _read_text(MATLAB_ENTRYPOINT).lower()
    for required in [
        "execute_single_pair",
        "dry_run_only",
        "pair_id",
        "selected-pair entrypoint refuses more than 32 pairs",
        "batch execution is refused",
        "execute_single_pair requires pair_id",
        "raw trajectory",
        "full timeseries",
        "mat files",
        "source slx",
        "timeout remains timeout/unknown",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "audit-only proxy",
    ]:
        assert required in text


def test_python_runner_rejects_batch_execute_without_single_pair() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/run_ieee39_selected_single_outage_pilot_pairs_controlled.py",
            "--approved-selected-pairs-only",
            "--execute",
            "--max-pairs",
            "32",
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "batch mode" in (result.stderr + result.stdout).lower()


def test_entrypoint_repair_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_selected_32_pair_controlled_execution_evidence.md"),
            _read_text(ROOT / "docs/ieee39_controlled_execution_backend_repair.md"),
            _read_text(OUT_DIR / "matlab_entrypoint_repair_summary.md"),
            _read_text(OUT_DIR / "single_pair_smoke_execution_contract.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "matlab selected-pair entrypoint repair",
        "does not train gcn",
        "does not rerun formal audit",
        "does not execute selected 32 pairs",
        "does not run full 1056 generation",
        "does not export formal labels",
        "does not retrain the reranker",
        "single-pair smoke",
        "at most one selected pair",
        "raw trajectory",
        "full timeseries",
        "source .slx",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are not used",
        "l12 remains special/excluded",
        "nf06 warning is preserved",
        "pilot labels are not formal training labels",
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
        "final engineering conclusion",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_entrypoint_repair_no_forbidden_large_artifacts_tracked() -> None:
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
