import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan"
PLAN_JSON = PLAN_DIR / "gcn_usefulness_audit_plan.json"
PLAN_MD = PLAN_DIR / "gcn_usefulness_audit_plan.md"
POLICY_JSON = PLAN_DIR / "no_leakage_feature_policy.json"
POLICY_MD = PLAN_DIR / "no_leakage_feature_policy.md"
SPLIT_JSON = PLAN_DIR / "strict_holdout_split_manifest.json"
SPLIT_MD = PLAN_DIR / "strict_holdout_split_manifest.md"
BASELINE_JSON = PLAN_DIR / "baseline_comparison_plan.json"
BASELINE_MD = PLAN_DIR / "baseline_comparison_plan.md"
CHECKLIST_JSON = PLAN_DIR / "gcn_audit_execution_checklist.json"
CHECKLIST_MD = PLAN_DIR / "gcn_audit_execution_checklist.md"
DOC = ROOT / "docs/ieee39_gcn_usefulness_audit_plan.md"


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


def test_plan_artifacts_exist() -> None:
    for path in [
        PLAN_JSON,
        PLAN_MD,
        POLICY_JSON,
        POLICY_MD,
        SPLIT_JSON,
        SPLIT_MD,
        BASELINE_JSON,
        BASELINE_MD,
        CHECKLIST_JSON,
        CHECKLIST_MD,
        DOC,
    ]:
        assert os.path.exists(_long(path)), path.name


def test_plan_summary_fields() -> None:
    payload = _read_json(PLAN_JSON)
    assert payload["audit_scope"] == "plan_only"
    assert payload["audit_execution_this_round"] is False
    assert payload["gcn_trained_this_round"] is False
    assert payload["formal_gcn_training"] is False
    assert payload["reranker_retrained"] is False
    assert payload["simulink_run"] is False
    assert payload["labels_exported"] is False
    assert payload["total_candidate_rows"] == 79
    assert payload["num_total_bus_fault_candidates"] == 39
    assert payload["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert payload["include_all_is_forbidden_for_gcn_audit"] is True
    assert payload["no_dynamic_measurement_features_required"] is True
    assert payload["unstable_flag_false_buses"] == ["B1"]
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["should_run_audit_now"] is False
    assert payload["should_train_now"] is False


def test_feature_policy_and_split_manifest() -> None:
    policy = _read_json(POLICY_JSON)
    split = _read_json(SPLIT_JSON)
    checklist = _read_json(CHECKLIST_JSON)
    for feature in [
        "min_voltage_pu",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
        "dynamic_stress_score",
        "unstable_flag",
    ]:
        assert feature in policy["forbidden_post_fault_dynamic_measurement_features"] or feature in policy["forbidden_label_derived_features"]
    assert policy["feature_policy_passed"] is True
    assert split["required_strict_holdouts"] == [
        "random_candidate_split_baseline",
        "label_family_holdout",
        "bus_fault_holdout",
        "leave_one_bus_fault_out",
        "no_dynamic_measurement_leave_one_bus_fault_out",
        "existing_vs_new_bus_fault_holdout",
        "nf06_provenance_sensitivity",
        "l12_exclusion_check",
    ]
    for name in [
        "bus_fault_holdout",
        "leave_one_bus_fault_out",
        "no_dynamic_measurement_leave_one_bus_fault_out",
        "nf06_provenance_sensitivity",
    ]:
        assert name in split["splits"]
    assert checklist["should_train_now"] is False
    assert checklist["failed_checks"] == []


def test_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(PLAN_MD),
            _read_text(POLICY_MD),
            _read_text(SPLIT_MD),
            _read_text(BASELINE_MD),
            _read_text(CHECKLIST_MD),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    current_text = "\n".join(
        [
            _read_text(DOC),
            _read_text(PLAN_MD),
            _read_text(POLICY_MD),
            _read_text(SPLIT_MD),
            _read_text(BASELINE_MD),
            _read_text(CHECKLIST_MD),
        ]
    ).lower()
    current_normalized = " ".join(current_text.replace("`", "").split())
    for required in [
        "only prepares the gcn usefulness audit plan",
        "it did not train gcn",
        "it did not run the gcn usefulness audit",
        "it did not run simulink",
        "it did not export labels",
        "it did not retrain the reranker",
        "leaky upper-bound",
        "no-dynamic-measurement feature set",
        "bus_fault_holdout",
        "leave_one_bus_fault_out",
        "b1",
        "nf06",
        "l12 stays excluded",
        "candidate_not_formal_label",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn usefulness audit was run",
        "gcn was trained",
        "final gcn conclusion",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_normalized


def test_no_forbidden_large_artifacts_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_gcn_usefulness_audit_plan"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden = [".slx", ".slxc", "slprj", ".mat", "raw_trajector", "full_timeseries", "local_lab_copies"]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden)]
    assert bad == []
