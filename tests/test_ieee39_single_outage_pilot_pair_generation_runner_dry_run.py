from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_single_outage_pilot_pair_generation_runner_dry_run"
DOC = ROOT / "docs/ieee39_single_outage_pilot_pair_generation_runner_dry_run.md"


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


def test_single_outage_pilot_pair_runner_dry_run_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/prepare_ieee39_single_outage_pilot_pair_generation_runner_dry_run.py",
            "--strict",
            "--write-report",
            "--max-pairs",
            "32",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_single_outage_pilot_pair_runner_dry_run_artifacts_exist() -> None:
    expected = [
        "pilot_pair_selection_summary.json",
        "pilot_pair_selection_summary.md",
        "pilot_pair_selection_summary.csv",
        "selected_single_outage_pilot_pairs.json",
        "selected_single_outage_pilot_pairs.md",
        "selected_single_outage_pilot_pairs.csv",
        "future_controlled_generation_run_plan.json",
        "future_controlled_generation_run_plan.md",
        "no_leakage_pilot_pair_runner_audit.json",
        "no_leakage_pilot_pair_runner_audit.md",
        "single_outage_pilot_pair_runner_dry_run_summary.json",
        "single_outage_pilot_pair_runner_dry_run_summary.md",
        "single_outage_pilot_pair_runner_dry_run_summary.csv",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_single_outage_pilot_pair_runner_dry_run_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "single_outage_pilot_pair_runner_dry_run_summary.json")
    expected = {
        "dry_run_scope": "single_outage_pilot_pair_runner_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "new_simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_single_outage_loop_commit": "b5e98d4fd27f438b2d46e6ec0ec60b46e21bcda9",
        "feature_matrix_with_proxy_ready": True,
        "relay_threshold_is_proxy": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
        "base_state_should_not_be_used_alone_for_training": True,
        "num_candidate_pairs_available": 1056,
        "label_values_fabricated": False,
        "selected_pairs_label_status": "planned",
        "can_execute_future_generation_runner_after_approval": True,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_run_simulink_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "blocker_if_any": None,
        "recommended_next_step": (
            "approve and execute selected single-outage pilot pair generation in a separate round"
        ),
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert summary["num_pilot_pairs_selected"] == 32
    assert summary["num_high_relay_ratio_pairs"] > 0
    assert summary["num_shared_bus_neighbor_pairs"] > 0
    assert summary["num_non_neighbor_control_pairs"] > 0


def test_pilot_pair_selection_summary_and_selected_pairs_schema() -> None:
    selection = _read_json(OUT_DIR / "pilot_pair_selection_summary.json")
    pairs = _read_json(OUT_DIR / "selected_single_outage_pilot_pairs.json")
    assert selection["selection_scope"] == "single_outage_pilot_pair_selection"
    assert selection["source_single_outage_loop_commit"] == "b5e98d4fd27f438b2d46e6ec0ec60b46e21bcda9"
    assert selection["max_pairs_requested"] == 32
    assert selection["num_pairs_selected"] == 32
    assert selection["num_high_relay_ratio_pairs"] > 0
    assert selection["num_shared_bus_neighbor_pairs"] > 0
    assert selection["num_non_neighbor_control_pairs"] > 0
    assert selection["num_l12_pairs_excluded"] == 66
    assert selection["bus_fault_labels_used"] is False
    assert selection["label_values_fabricated"] is False
    assert selection["ready_for_future_controlled_generation"] is True

    assert len(pairs) == 32
    pair_ids = {row["pair_id"] for row in pairs}
    assert len(pair_ids) == len(pairs)
    buckets = {row["selection_bucket"] for row in pairs}
    assert "high_relay_ratio_pairs" in buckets
    assert "shared_bus_neighbor_pairs" in buckets
    assert "non_neighbor_control_pairs" in buckets
    assert all(row["label_value"] is None for row in pairs)
    assert all(row["label_status"] == "planned" for row in pairs)
    assert all(row["future_generation_required"] is True for row in pairs)
    assert all(row["bus_fault_label_used"] is False for row in pairs)
    assert all(row["l12_special_case_flag"] is False for row in pairs)
    assert all("L12" not in {row["prior_outaged_branch"], row["candidate_next_branch"]} for row in pairs)
    assert all(row["feature_matrix_with_proxy_ready"] is True for row in pairs)
    assert all(row["relay_threshold_is_proxy"] is True for row in pairs)
    assert all(row["proxy_allowed_for_audit_only_prototype"] is True for row in pairs)
    neighbor = [row for row in pairs if row["selection_bucket"] == "shared_bus_neighbor_pairs"]
    assert neighbor and all(row["shares_bus_with_prior"] is True for row in neighbor)
    controls = [row for row in pairs if row["selection_bucket"] == "non_neighbor_control_pairs"]
    assert controls and all(row["shares_bus_with_prior"] is False for row in controls)

    with open(_long(OUT_DIR / "selected_single_outage_pilot_pairs.csv"), newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 32


def test_future_run_plan_and_no_leakage_audit() -> None:
    plan = _read_json(OUT_DIR / "future_controlled_generation_run_plan.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_pilot_pair_runner_audit.json")
    assert plan["run_plan_scope"] == "future_controlled_single_outage_pilot_generation"
    assert plan["dry_run_only_this_round"] is True
    assert plan["new_simulink_run_this_round"] is False
    assert plan["selected_pair_count"] == 32
    assert plan["no_raw_trajectory_commit_policy"] is True
    assert plan["no_formal_label_export_this_round"] is True
    assert plan["required_manual_approval_before_execution"] is True
    assert "L12" in plan["l12_exclusion_policy"]
    assert "null" in plan["unknown_policy"]

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_future_labels_or_targets"] is True
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["proxy_relay_threshold_used_only_in_feature_generation"] is True
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["no_leakage_policy_passed"] is True


def test_single_outage_pilot_pair_runner_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_single_outage_label_loop_dry_run.md"),
            _read_text(ROOT / "docs/ieee39_base_state_branch_vulnerability_label_pilot.md"),
            _read_text(OUT_DIR / "pilot_pair_selection_summary.md"),
            _read_text(OUT_DIR / "future_controlled_generation_run_plan.md"),
            _read_text(OUT_DIR / "no_leakage_pilot_pair_runner_audit.md"),
            _read_text(OUT_DIR / "single_outage_pilot_pair_runner_dry_run_summary.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "selected single-outage pilot pair generation runner dry-run",
        "does not train gcn",
        "does not rerun formal audit",
        "does not run new simulink",
        "does not export formal labels",
        "does not retrain the reranker",
        "base-state labels are all negative",
        "cannot be used alone",
        "does not run all 1056",
        "high_relay_ratio_pairs",
        "shared_bus_neighbor_pairs",
        "non_neighbor_control_pairs",
        "l12 remains special/excluded",
        "nf06 warning is preserved",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are not used",
        "label_values_fabricated: false",
        "manual approval is required",
        "no deployment",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "formal labels exported",
        "ran new simulink",
        "proxy is a real relay setting",
        "final engineering conclusion: true",
        "emt simulation",
        "generator_speed_proxy is direct frequency",
        "production_model_saved = true",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_single_outage_pilot_pair_runner_no_forbidden_large_artifacts_tracked() -> None:
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
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    bad = [path for path in changed if any(token in path for token in forbidden_tokens)]
    assert not bad, bad
