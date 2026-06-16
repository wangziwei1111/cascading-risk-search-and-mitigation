import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_dependency_diagnosis"
SUMMARY_JSON = OUT_DIR / "gcn_dependency_diagnosis_summary.json"
SUMMARY_MD = OUT_DIR / "gcn_dependency_diagnosis_summary.md"
SUMMARY_CSV = OUT_DIR / "gcn_dependency_diagnosis_summary.csv"
ENV_JSON = OUT_DIR / "python_environment_probe.json"
ENV_MD = OUT_DIR / "python_environment_probe.md"
TORCH_JSON = OUT_DIR / "torch_import_probe.json"
TORCH_MD = OUT_DIR / "torch_import_probe.md"
PYG_JSON = OUT_DIR / "torch_geometric_import_probe.json"
PYG_MD = OUT_DIR / "torch_geometric_import_probe.md"
PATH_JSON = OUT_DIR / "windows_path_dll_probe.json"
PATH_MD = OUT_DIR / "windows_path_dll_probe.md"
PLAN_JSON = OUT_DIR / "gcn_dependency_repair_plan.json"
PLAN_MD = OUT_DIR / "gcn_dependency_repair_plan.md"
DOC = ROOT / "docs/ieee39_gcn_dependency_blocker_diagnosis.md"


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


def test_dependency_diagnosis_executes_and_writes_artifacts() -> None:
    subprocess.run(
        [
            "python",
            "scripts/gcn_search/diagnose_ieee39_gcn_dependency_blocker.py",
            "--strict",
            "--write-report",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        check=True,
    )
    for path in [
        SUMMARY_JSON,
        SUMMARY_MD,
        SUMMARY_CSV,
        ENV_JSON,
        ENV_MD,
        TORCH_JSON,
        TORCH_MD,
        PYG_JSON,
        PYG_MD,
        PATH_JSON,
        PATH_MD,
        PLAN_JSON,
        PLAN_MD,
        DOC,
    ]:
        assert os.path.exists(_long(path)), path.name


def test_dependency_diagnosis_summary_fields() -> None:
    summary = _read_json(SUMMARY_JSON)
    env_probe = _read_json(ENV_JSON)
    path_probe = _read_json(PATH_JSON)
    repair_plan = _read_json(PLAN_JSON)

    assert summary["diagnosis_scope"] == "dependency_diagnosis_only"
    assert summary["gcn_training_run"] is False
    assert summary["formal_gcn_audit_run"] is False
    assert summary["simulink_run"] is False
    assert summary["labels_exported"] is False
    assert summary["reranker_retrained"] is False
    assert summary["production_model_saved"] is False
    assert summary["source_commit"] == "6c89098a2f4a127102b16d1ef990ec66e4b9d16c"
    assert summary["previous_gcn_dependency_status"] == "blocked_by_missing_gcn_dependency"
    assert "torch_spec_present" in summary
    assert "torch_import_ok" in summary
    assert "torch_geometric_spec_present" in summary
    assert "torch_geometric_import_ok" in summary
    assert "suspicious_path_entries" in summary
    assert "drive_relative_path_entries" in summary
    assert "gcn_dependency_blocker_still_present" in summary
    assert "recommended_next_step" in summary
    assert summary["dependency_repair_plan_generated"] is True
    assert summary["should_train_gcn_now"] is False
    assert summary["should_rerun_formal_gcn_audit_now"] is False
    assert summary["current_sys_prefix"] == env_probe["sys_prefix"]
    assert summary["current_sys_base_prefix"] == env_probe["sys_base_prefix"]
    assert summary["current_sys_exec_prefix"] == env_probe["sys_exec_prefix"]
    assert path_probe["probe_scope"] == "windows_path_dll_diagnosis_only"
    assert "recommended_path_fix" in path_probe
    assert "route_a_path_dll_cleanup_first" in repair_plan
    assert "route_b_clean_virtualenv" in repair_plan
    assert "route_c_conda_optional" in repair_plan
    verify_commands = "\n".join(repair_plan["verification_commands"])
    assert "import torch" in verify_commands
    assert "import torch_geometric" in verify_commands
    assert "run_ieee39_strict_no_leakage_gcn_usefulness_audit.py" in verify_commands
    assert "official matching wheel index" in json.dumps(repair_plan, ensure_ascii=False).lower()


def test_dependency_diagnosis_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(SUMMARY_MD),
            _read_text(DOC),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
            _read_text(ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"),
            _read_text(ROOT / "docs/ieee39_gcn_usefulness_audit_dry_run_validator.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    current_round_text = "\n".join([_read_text(SUMMARY_MD), _read_text(DOC)]).lower()
    current_normalized = " ".join(current_round_text.replace("`", "").split())
    for required in [
        "dependency diagnosis only",
        "did not train gcn",
        "did not rerun the formal gcn usefulness audit",
        "did not run simulink",
        "did not export labels",
        "did not retrain the reranker",
        "baseline-only audit",
        "blocked by the local dependency environment",
        "winerror 87",
        "e:bin",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn was trained in this round",
        "formal gcn audit rerun completed",
        "gcn is useful",
        "gcn is useless",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_normalized


def test_dependency_diagnosis_branch_does_not_track_forbidden_large_artifacts() -> None:
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
        ".venv",
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
