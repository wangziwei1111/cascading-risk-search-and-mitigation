import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_consistency_check"
SUMMARY_JSON = OUT_DIR / "paper_aligned_redesign_consistency_check.json"
SUMMARY_MD = OUT_DIR / "paper_aligned_redesign_consistency_check.md"
DOC = ROOT / "docs/ieee39_paper_aligned_branch_gcn_redesign_consistency_check.md"
EXEC_DOC = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"


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


def test_paper_aligned_redesign_consistency_artifacts_exist() -> None:
    for path in [SUMMARY_JSON, SUMMARY_MD, DOC]:
        assert os.path.exists(_long(path)), path


def test_paper_aligned_redesign_consistency_summary_fields() -> None:
    payload = _read_json(SUMMARY_JSON)
    for key, expected in [
        ("check_scope", "paper_aligned_branch_gcn_redesign_consistency_check"),
        ("gcn_training_run", False),
        ("formal_gcn_audit_rerun", False),
        ("simulink_run", False),
        ("labels_exported", False),
        ("reranker_retrained", False),
        ("production_model_saved", False),
        ("source_dry_run_commit", "3230109b27c3b9af54801b61835b9a491490b2c1"),
        ("execution_summary_post_repair_audit", True),
        ("execution_doc_matches_execution_summary", True),
        ("stale_baseline_only_text_removed", True),
        ("paper_aligned_dry_run_preserved", True),
        ("can_build_branch_line_graph", True),
        ("can_build_required_paper_features", False),
        ("can_build_paper_labels_from_existing_data", False),
        ("bus_fault_labels_directly_paper_aligned", False),
        ("line_trip_labels_first_priority", True),
        ("final_engineering_conclusion", False),
        ("should_deploy_model", False),
        ("should_retrain_reranker_now", False),
    ]:
        assert payload.get(key) == expected, key
    assert payload["failed_checks"] == []


def test_strict_audit_execution_doc_matches_post_repair_summary() -> None:
    text = " ".join(_read_text(EXEC_DOC).replace("`", "").split()).lower()
    for required in [
        "post-repair strict no-leakage audit",
        "gcn_trained_for_audit: true",
        "gcn_dependency_available: true",
        "gcn_dependency_status: torch_and_torch_geometric_available",
        "0.7032927445152551",
        "0.12218041951744846",
        "audit evidence does not support gcn usefulness over simpler baselines yet",
        "final_engineering_conclusion: false",
        "should_retrain_reranker_now: false",
        "should_deploy_model: false",
    ]:
        assert required in text
    for stale in [
        "execution summary is still a baseline-only audit",
        "gcn_trained_for_audit: false",
        "gcn_dependency_status: blocked_by_missing_gcn_dependency",
        "gcn metrics: unavailable",
        "formal gcn audit blocked by missing dependency",
        "baseline-only audit completed",
    ]:
        assert stale not in text


def test_consistency_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md"),
            _read_text(ROOT / "docs/ieee39_gcn_audit_evidence_diagnosis.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "documentation consistency",
        "does not train gcn",
        "does not rerun the formal audit",
        "does not run simulink",
        "does not export labels",
        "does not retrain the reranker",
        "current audit evidence does not support gcn usefulness over simpler baselines yet",
        "paper-aligned",
        "branch-as-node",
        "can_build_required_paper_features = false",
        "can_build_paper_labels_from_existing_data = false",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useless",
        "final engineering conclusion: true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "production_model_saved = true",
        "production ready",
    ]:
        assert forbidden not in normalized


def test_paper_aligned_redesign_consistency_no_forbidden_large_artifacts_tracked() -> None:
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
