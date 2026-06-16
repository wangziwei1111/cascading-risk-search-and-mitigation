import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair_consistency_check"
SUMMARY_JSON = OUT_DIR / "dependency_repair_consistency_check.json"
SUMMARY_MD = OUT_DIR / "dependency_repair_consistency_check.md"
DOC = ROOT / "docs/ieee39_gcn_dependency_repair_consistency_check.md"
EXECUTION_DOC = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"
EXECUTION_SUMMARY = (
    ROOT
    / "results/gcn_search/ieee39_gcn_usefulness_audit_execution/"
    "gcn_usefulness_audit_execution_summary.json"
)


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


def test_consistency_check_artifacts_exist() -> None:
    for path in [SUMMARY_JSON, SUMMARY_MD, DOC]:
        assert os.path.exists(_long(path)), path.name


def test_consistency_check_summary_fields() -> None:
    payload = _read_json(SUMMARY_JSON)
    assert payload["check_scope"] == "dependency_repair_consistency_check"
    assert payload["gcn_training_run"] is False
    assert payload["formal_gcn_audit_run"] is False
    assert payload["simulink_run"] is False
    assert payload["labels_exported"] is False
    assert payload["reranker_retrained"] is False
    assert payload["dependency_blocker_resolved"] is True
    assert payload["formal_audit_rerun_after_repair"] is False
    assert payload["execution_summary_still_baseline_only"] is True
    assert payload["execution_doc_matches_execution_summary"] is True
    assert payload["premature_gcn_conclusion_removed"] is True
    assert payload["final_engineering_conclusion"] is False
    assert payload["should_rerun_strict_no_leakage_audit_next"] is True
    assert payload["should_deploy_model"] is False
    assert payload["should_retrain_reranker_now"] is False
    assert payload["failed_checks"] == []


def test_execution_doc_matches_existing_baseline_only_summary() -> None:
    summary = _read_json(EXECUTION_SUMMARY)
    execution_doc = _read_text(EXECUTION_DOC).lower()
    assert summary["gcn_trained_for_audit"] is False
    assert summary["gcn_dependency_status"] == "blocked_by_missing_gcn_dependency"
    assert summary["audit_level_conclusion"] == (
        "formal GCN audit blocked by missing dependency; baseline-only audit completed"
    )
    assert summary["final_engineering_conclusion"] is False
    assert summary["should_retrain_reranker_now"] is False
    assert summary["should_deploy_model"] is False
    assert "gcn_trained_for_audit: `false`" in execution_doc
    assert "blocked_by_missing_gcn_dependency" in execution_doc
    assert "gcn metrics: unavailable / `null`" in execution_doc
    assert "baseline-only audit completed" in execution_doc


def test_consistency_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
            _read_text(EXECUTION_DOC),
            _read_text(ROOT / "docs/ieee39_gcn_dependency_repair.md"),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "dependency repair consistency check",
        "dependency_blocker_resolved = true",
        "formal_audit_rerun_after_repair = false",
        "execution_summary_still_baseline_only = true",
        "premature_gcn_conclusion_removed = true",
        "no gcn usefulness conclusion",
        "phasor_rms",
        "not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn_trained_for_audit: true",
        "gcn_trained_for_audit = true",
        "torch_and_torch_geometric_available",
        "audit evidence does not support gcn usefulness",
        "gcn is useful",
        "gcn is not useful",
        "final gcn conclusion",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in normalized


def test_no_forbidden_large_artifacts_are_tracked() -> None:
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
        "venv/",
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
