from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_relay_threshold_proxy_approval"
DOC = ROOT / "docs/ieee39_relay_threshold_proxy_approval.md"


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


def test_relay_threshold_proxy_approval_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/approve_ieee39_relay_threshold_proxy.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_relay_threshold_proxy_approval_artifacts_exist() -> None:
    expected = [
        "relay_threshold_proxy_approval_summary.json",
        "relay_threshold_proxy_approval_summary.md",
        "relay_threshold_proxy_approval_summary.csv",
        "l01_l34_approved_paper_feature_source_matrix.json",
        "l01_l34_approved_paper_feature_source_matrix.md",
        "l01_l34_approved_paper_feature_source_matrix.csv",
        "no_leakage_proxy_feature_audit.json",
        "no_leakage_proxy_feature_audit.md",
        "relay_threshold_proxy_limitations.md",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_relay_threshold_proxy_approval_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "relay_threshold_proxy_approval_summary.json")
    no_leakage = _read_json(OUT_DIR / "no_leakage_proxy_feature_audit.json")

    expected = {
        "approval_scope": "relay_threshold_proxy_approval",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_static_feature_commit": "a29bc6e209afe764aa8bf57613d66dd53114fba9",
        "relay_threshold_source_ready": False,
        "relay_threshold_proxy_approved": True,
        "relay_threshold_proxy_allowed_for_audit_only_prototype": True,
        "relay_threshold_proxy_allowed_for_production": False,
        "proxy_formula": "beta * RATE_A",
        "beta_value": 1.2,
        "beta_value_source": "project default beta = 1.2",
        "line_limit_source": "pypower.case39 branch RATE_A",
        "branch_flow_source_ready": True,
        "line_limit_source_ready": True,
        "bus_load_source_ready": True,
        "can_build_required_paper_features_without_proxy": False,
        "can_build_required_paper_features_with_approved_proxy": True,
        "can_build_l01_l34_paper_feature_matrix_with_proxy": True,
        "forbidden_features_detected_in_inputs": [],
        "no_leakage_policy_passed": True,
        "l12_special_case_preserved": True,
        "final_engineering_conclusion": False,
        "should_train_gcn_now": False,
        "should_rerun_formal_audit_now": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
    }
    for key, value in expected.items():
        assert summary.get(key) == value, key
    assert summary["recommended_next_step"] == "prepare paper-style branch vulnerability label generator dry-run for line-trip labels"

    assert no_leakage["forbidden_features_detected_in_inputs"] == []
    assert no_leakage["post_fault_dynamic_measurements_used_as_inputs"] is False
    assert no_leakage["static_or_prefault_sources_only"] is True
    assert no_leakage["dynamic_targets_only_used_as_labels"] is True
    assert no_leakage["proxy_not_engineering_relay_setting"] is True
    assert no_leakage["no_leakage_policy_passed"] is True


def test_relay_threshold_proxy_approval_matrix() -> None:
    matrix = _read_json(OUT_DIR / "l01_l34_approved_paper_feature_source_matrix.json")
    assert len(matrix) == 34
    assert matrix[0]["line_id"] == "L01"
    assert matrix[-1]["line_id"] == "L34"
    assert all(row["ready_for_x_t"] for row in matrix)
    assert all(row["ready_for_x_p_with_proxy"] for row in matrix)
    assert all(row["ready_for_x_b"] for row in matrix)
    assert all(row["ready_for_x_l"] for row in matrix)
    assert all(row["ready_for_lx4_feature_vector_with_proxy"] for row in matrix)
    assert all(row["relay_threshold_is_proxy"] for row in matrix)
    assert all(row["proxy_allowed_for_audit_only_prototype"] for row in matrix)
    assert not any(row["proxy_allowed_for_production"] for row in matrix)
    assert all(row["x_p_relay_threshold_proxy_formula"] == "beta * RATE_A" for row in matrix)
    assert all(row["x_p_relay_ratio_value"] is not None for row in matrix)
    assert [row for row in matrix if row["line_id"] == "L12"][0]["l12_special_case_flag"] is True

    with open(_long(OUT_DIR / "l01_l34_approved_paper_feature_source_matrix.csv"), newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 34
    assert rows[0]["x_b_branch_flow_unit"] == "MW"


def test_relay_threshold_proxy_approval_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(OUT_DIR / "relay_threshold_proxy_approval_summary.md"),
            _read_text(OUT_DIR / "relay_threshold_proxy_limitations.md"),
            _read_text(OUT_DIR / "no_leakage_proxy_feature_audit.md"),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_static_operating_point_feature_source_dry_run.md"),
            _read_text(ROOT / "docs/ieee39_paper_aligned_feature_source_dry_run.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "relay threshold proxy approval",
        "did not train gcn",
        "did not rerun formal audit",
        "did not run simulink",
        "did not export labels",
        "did not retrain the reranker",
        "audit-only paper-aligned prototype proxy",
        "beta * rate_a",
        "beta = 1.2",
        "pypower.case39",
        "not a real relay protection setting",
        "not an engineering-grade relay threshold",
        "not allowed for production",
        "post-fault dynamic measurements are not used as inputs",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "final engineering conclusion: true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade relay threshold = true",
        "relay_threshold_proxy_allowed_for_production = true",
        "production_model_saved = true",
    ]:
        assert forbidden not in normalized


def test_relay_threshold_proxy_approval_no_forbidden_large_artifacts_tracked() -> None:
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
