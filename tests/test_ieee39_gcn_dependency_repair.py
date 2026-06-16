import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_dependency_repair"
SUMMARY_JSON = OUT_DIR / "gcn_dependency_repair_summary.json"
SUMMARY_MD = OUT_DIR / "gcn_dependency_repair_summary.md"
SUMMARY_CSV = OUT_DIR / "gcn_dependency_repair_summary.csv"
BEFORE_JSON = OUT_DIR / "python_launcher_probe_before_repair.json"
BEFORE_MD = OUT_DIR / "python_launcher_probe_before_repair.md"
VENV_JSON = OUT_DIR / "venv_creation_report.json"
VENV_MD = OUT_DIR / "venv_creation_report.md"
TORCH_JSON = OUT_DIR / "torch_install_verify_report.json"
TORCH_MD = OUT_DIR / "torch_install_verify_report.md"
PYG_JSON = OUT_DIR / "torch_geometric_install_verify_report.json"
PYG_MD = OUT_DIR / "torch_geometric_install_verify_report.md"
POST_JSON = OUT_DIR / "post_repair_dependency_diagnosis_report.json"
POST_MD = OUT_DIR / "post_repair_dependency_diagnosis_report.md"
DOC = ROOT / "docs/ieee39_gcn_dependency_repair.md"


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


def test_repair_artifacts_exist() -> None:
    for path in [
        SUMMARY_JSON,
        SUMMARY_MD,
        SUMMARY_CSV,
        BEFORE_JSON,
        BEFORE_MD,
        VENV_JSON,
        VENV_MD,
        TORCH_JSON,
        TORCH_MD,
        PYG_JSON,
        PYG_MD,
        POST_JSON,
        POST_MD,
        DOC,
    ]:
        assert os.path.exists(_long(path)), path.name


def test_repair_summary_fields() -> None:
    summary = _read_json(SUMMARY_JSON)
    post = _read_json(POST_JSON)
    assert summary["repair_scope"] == "local_dependency_environment_repair"
    assert summary["gcn_training_run"] is False
    assert summary["formal_gcn_audit_run"] is False
    assert summary["simulink_run"] is False
    assert summary["labels_exported"] is False
    assert summary["reranker_retrained"] is False
    assert summary["production_model_saved"] is False
    assert summary["new_venv_path"]
    assert summary["new_python_executable"]
    assert summary["new_sys_prefix"]
    assert "new_python_prefix_is_not_bare_drive" in summary
    assert summary["torch_install_attempted"] is True
    assert "torch_import_ok" in summary
    assert "torch_geometric_install_attempted" in summary
    assert "torch_geometric_import_ok" in summary
    assert "dependency_blocker_resolved" in summary
    assert summary["should_train_gcn_now"] is False
    assert summary["should_rerun_formal_gcn_audit_now"] is False
    assert summary["new_python_prefix_is_absolute"] is True
    assert summary["new_python_prefix_is_not_bare_drive"] is True
    assert summary["torch_import_ok"] == post["torch_import_ok"]
    assert summary["torch_geometric_import_ok"] == post["torch_geometric_import_ok"]


def test_gitignore_covers_repair_venv() -> None:
    gitignore = _read_text(ROOT / ".gitignore").lower()
    assert ".venv-gcn-audit/" in gitignore or ".venv-*/" in gitignore


def test_repair_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(SUMMARY_MD),
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "local dependency environment repair",
        "did not train gcn",
        "did not run the formal gcn audit",
        "did not run simulink",
        "did not export labels",
        "did not retrain the reranker",
        "sys.prefix = e:",
        "e:bin",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal gcn audit rerun completed",
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
