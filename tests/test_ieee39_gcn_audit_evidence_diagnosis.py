import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis"
DOC = ROOT / "docs/ieee39_gcn_audit_evidence_diagnosis.md"
SUMMARY_JSON = OUT_DIR / "gcn_audit_evidence_diagnosis_summary.json"
SUMMARY_MD = OUT_DIR / "gcn_audit_evidence_diagnosis_summary.md"
SUMMARY_CSV = OUT_DIR / "gcn_audit_evidence_diagnosis_summary.csv"
GAP_JSON = OUT_DIR / "gcn_vs_baseline_gap_analysis.json"
GAP_MD = OUT_DIR / "gcn_vs_baseline_gap_analysis.md"
B1_JSON = OUT_DIR / "b1_and_classification_diagnosis.json"
B1_MD = OUT_DIR / "b1_and_classification_diagnosis.md"
NF06_JSON = OUT_DIR / "nf06_sensitivity_diagnosis.json"
NF06_MD = OUT_DIR / "nf06_sensitivity_diagnosis.md"
GRAPH_JSON = OUT_DIR / "graph_construction_diagnosis.json"
GRAPH_MD = OUT_DIR / "graph_construction_diagnosis.md"
PLAN_JSON = OUT_DIR / "next_gcn_improvement_plan.json"
PLAN_MD = OUT_DIR / "next_gcn_improvement_plan.md"


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


def test_gcn_audit_evidence_diagnosis_generator_runs() -> None:
    subprocess.run(
        [sys.executable, "scripts/gcn_search/diagnose_ieee39_gcn_audit_evidence_gap.py"],
        cwd=ROOT,
        text=True,
        check=True,
    )


def test_gcn_audit_evidence_diagnosis_artifacts_exist() -> None:
    for path in [
        SUMMARY_JSON,
        SUMMARY_MD,
        SUMMARY_CSV,
        GAP_JSON,
        GAP_MD,
        B1_JSON,
        B1_MD,
        NF06_JSON,
        NF06_MD,
        GRAPH_JSON,
        GRAPH_MD,
        PLAN_JSON,
        PLAN_MD,
        DOC,
    ]:
        assert os.path.exists(_long(path)), path.name


def test_gcn_audit_evidence_diagnosis_summary_fields() -> None:
    summary = _read_json(SUMMARY_JSON)
    gap = _read_json(GAP_JSON)
    b1 = _read_json(B1_JSON)
    nf06 = _read_json(NF06_JSON)
    graph = _read_json(GRAPH_JSON)
    plan = _read_json(PLAN_JSON)

    assert summary["diagnosis_scope"] == "gcn_audit_evidence_diagnosis"
    assert summary["gcn_training_run"] is False
    assert summary["formal_gcn_audit_rerun"] is False
    assert summary["simulink_run"] is False
    assert summary["labels_exported"] is False
    assert summary["reranker_retrained"] is False
    assert summary["production_model_saved"] is False
    assert summary["final_engineering_conclusion"] is False
    assert summary["should_retrain_reranker_now"] is False
    assert summary["should_deploy_model"] is False
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["audit_level_conclusion_preserved"] is True

    assert gap["bus_fault_holdout_gcn_rmse"] > gap["bus_fault_holdout_best_baseline_rmse"]
    assert gap["lobo_gcn_rmse"] > gap["lobo_best_baseline_rmse"]
    assert gap["no_dynamic_lobo_gcn_rmse"] > gap["no_dynamic_lobo_best_baseline_rmse"]

    assert b1["gcn_unstable_probability"] == 1.0
    assert b1["b1_overconfident"] is True
    assert nf06["nf06_changes_gcn_rmse"] is True
    assert nf06["nf06_changes_audit_conclusion"] is False
    assert "message passing" in graph["message_passing_usage"].lower()
    assert "physical bus-branch electrical topology" in graph["topology_message_passing_check"].lower()
    assert graph["nominal_gcn_but_tabular_risk"] is True
    assert plan["training_triggered"] is False
    assert plan["reranker_retraining_triggered"] is False


def test_gcn_audit_evidence_diagnosis_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(SUMMARY_MD),
            _read_text(GAP_MD),
            _read_text(B1_MD),
            _read_text(NF06_MD),
            _read_text(GRAPH_MD),
            _read_text(PLAN_MD),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "evidence diagnosis only",
        "does not train gcn",
        "does not rerun the formal audit",
        "does not run simulink",
        "does not export labels",
        "does not retrain the reranker",
        "current audit evidence does not support gcn usefulness over simpler baselines yet",
        "not a final proof against gcn",
        "b1",
        "overconfident",
        "nf06",
        "does not change the conclusion",
        "candidate rows as graph nodes",
        "not physical bus-branch electrical topology",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useless",
        "final engineering conclusion: true",
        "production_model_saved = true",
        "production model saved: true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in normalized


def test_gcn_audit_evidence_diagnosis_no_forbidden_large_artifacts_tracked() -> None:
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
