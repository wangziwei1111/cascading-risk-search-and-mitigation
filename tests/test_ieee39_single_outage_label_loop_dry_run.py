from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_single_outage_label_loop_dry_run"
DOC = ROOT / "docs/ieee39_single_outage_label_loop_dry_run.md"


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


def test_single_outage_label_loop_dry_run_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/prepare_ieee39_single_outage_label_loop_dry_run.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_single_outage_label_loop_dry_run_artifacts_exist() -> None:
    expected = [
        "single_outage_state_manifest.json",
        "single_outage_state_manifest.md",
        "single_outage_state_manifest.csv",
        "single_outage_state_branch_label_loop_plan.json",
        "single_outage_state_branch_label_loop_plan.md",
        "single_outage_state_branch_label_loop_plan.csv",
        "base_state_label_distribution_review.json",
        "base_state_label_distribution_review.md",
        "existing_artifact_reuse_for_single_outage_audit.json",
        "existing_artifact_reuse_for_single_outage_audit.md",
        "no_leakage_single_outage_label_loop_audit.json",
        "no_leakage_single_outage_label_loop_audit.md",
        "single_outage_label_loop_dry_run_summary.json",
        "single_outage_label_loop_dry_run_summary.md",
        "single_outage_label_loop_dry_run_summary.csv",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_single_outage_label_loop_dry_run_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "single_outage_label_loop_dry_run_summary.json")
    expected = {
        "dry_run_scope": "single_outage_label_loop_dry_run",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "new_simulink_run": False,
        "labels_exported": False,
        "formal_labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_base_state_pilot_commit": "449f8d1e625672bb6e01fbffd59c6bb97d3d0fe0",
        "paper_graph_node_type": "branch",
        "paper_graph_edge_rule": "shared_endpoint_bus",
        "feature_matrix_with_proxy_ready": True,
        "relay_threshold_is_proxy": True,
        "proxy_allowed_for_audit_only_prototype": True,
        "proxy_allowed_for_production": False,
        "base_state_all_available_labels_negative": True,
        "base_state_should_not_be_used_alone_for_training": True,
        "num_single_outage_states_planned": 34,
        "num_state_branch_pairs_planned": 1122,
        "num_pairs_excluded_due_to_same_branch": 34,
        "num_pairs_excluded_due_to_l12_special": 66,
        "num_pairs_planned_for_future_generation": 1056,
        "num_pairs_available_from_existing_artifacts": 0,
        "can_generate_single_outage_labels_now": False,
        "can_export_formal_single_outage_labels_now": False,
        "bus_fault_labels_used": False,
        "line_trip_labels_first_priority": True,
        "l12_special_case_preserved": True,
        "nf06_warning_preserved": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_export_formal_labels_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "recommended_next_step": (
            "implement controlled generation runner for selected single-outage pilot pairs in a separate round"
        ),
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert "no approved reusable single_outage_state x next_branch" in summary["blocker_if_any"]


def test_single_outage_state_manifest_schema_and_l12() -> None:
    states = _read_json(OUT_DIR / "single_outage_state_manifest.json")
    assert len(states) == 34
    assert {row["state_type"] for row in states} == {"single_outage_state"}
    assert all(row["x_t_vector_ready"] is True for row in states)
    assert all(row["num_candidate_next_branches"] == 33 for row in states)
    assert all(row["prior_outaged_branch"] not in row["candidate_next_branches"] for row in states)
    l12 = [row for row in states if row["prior_outaged_branch"] == "L12"][0]
    assert l12["eligible_for_label_generation"] is False
    assert l12["l12_in_prior_state"] is True
    assert "special" in l12["exclusion_reason_if_any"].lower()
    non_l12 = [row for row in states if row["prior_outaged_branch"] != "L12"]
    assert len(non_l12) == 33
    assert all(row["eligible_for_label_generation"] is True for row in non_l12)


def test_single_outage_pair_plan_schema_and_l12_exclusions() -> None:
    plan = _read_json(OUT_DIR / "single_outage_state_branch_label_loop_plan.json")
    assert len(plan) == 1122
    assert all(row["prior_outaged_branch"] != row["candidate_next_branch"] for row in plan)
    assert all(row["label_value"] is None for row in plan)
    assert all(row["label_source_available"] is False for row in plan)
    assert all(row["bus_fault_label_used"] is False for row in plan)
    assert all(row["proxy_relay_threshold_used"] is True for row in plan)
    excluded = [row for row in plan if row["label_status"] == "excluded"]
    planned = [row for row in plan if row["label_status"] == "planned"]
    assert len(excluded) == 66
    assert len(planned) == 1056
    assert all(row["l12_special_case_flag"] is True for row in excluded)
    assert all("L12" in {row["prior_outaged_branch"], row["candidate_next_branch"]} for row in excluded)
    assert all(row["requires_new_simulink_run"] is False for row in excluded)
    assert all(row["requires_new_simulink_run"] is True for row in planned)
    assert all(row["requires_existing_artifact_lookup"] is False for row in plan)

    with open(_long(OUT_DIR / "single_outage_state_branch_label_loop_plan.csv"), newline="", encoding="utf-8") as handle:
        csv_rows = list(csv.DictReader(handle))
    assert len(csv_rows) == 1122


def test_single_outage_reviews_and_no_leakage() -> None:
    base = _read_json(OUT_DIR / "base_state_label_distribution_review.json")
    reuse = _read_json(OUT_DIR / "existing_artifact_reuse_for_single_outage_audit.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_single_outage_label_loop_audit.json")

    assert base["base_state_num_label_slots"] == 34
    assert base["base_state_num_labels_available"] == 33
    assert base["base_state_num_positive_labels"] == 0
    assert base["base_state_num_negative_labels"] == 33
    assert base["base_state_num_excluded_labels"] == 1
    assert base["base_state_all_available_labels_negative"] is True
    assert base["training_risk_if_using_base_state_only"] is True
    assert "do not train on base-state labels only" in base["recommendation"]

    assert reuse["existing_multi_line_or_path_labels_found"] is False
    assert reuse["reusable_for_single_outage_count"] == 0
    assert reuse["reusable_sequences"] == []
    assert reuse["bus_fault_labels_used"] is False
    assert reuse["l12_excluded_or_special"] is True

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["dynamic_outputs_used_only_as_labels_or_targets"] is True
    assert no_leakage["label_derived_flags_used_as_inputs"] is False
    assert no_leakage["proxy_relay_threshold_used_only_in_feature_generation"] is True
    assert no_leakage["bus_fault_labels_used"] is False
    assert no_leakage["no_leakage_policy_passed"] is True


def test_single_outage_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_base_state_branch_vulnerability_label_pilot.md"),
            _read_text(ROOT / "docs/ieee39_paper_style_branch_vulnerability_label_generator_dry_run.md"),
            _read_text(ROOT / "docs/ieee39_relay_threshold_proxy_approval.md"),
            _read_text(OUT_DIR / "single_outage_label_loop_dry_run_summary.md"),
            _read_text(OUT_DIR / "base_state_label_distribution_review.md"),
            _read_text(OUT_DIR / "existing_artifact_reuse_for_single_outage_audit.md"),
            _read_text(OUT_DIR / "no_leakage_single_outage_label_loop_audit.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "controlled single-outage state label loop dry-run",
        "does not train gcn",
        "does not rerun formal audit",
        "does not run new simulink",
        "does not export formal labels",
        "does not retrain the reranker",
        "all 33 available non-l12 labels were negative",
        "cannot train",
        "single_outage_state x next_branch",
        "does not fabricate 0/1 labels",
        "beta * rate_a",
        "audit-only proxy",
        "not a real relay setting",
        "bus-fault labels are unused",
        "l12 stays special/excluded",
        "nf06 warning is preserved",
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
        "production_model_saved = true",
        "real relay setting = true",
        "deployment ready",
    ]:
        assert forbidden not in normalized


def test_single_outage_no_forbidden_large_artifacts_tracked() -> None:
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
