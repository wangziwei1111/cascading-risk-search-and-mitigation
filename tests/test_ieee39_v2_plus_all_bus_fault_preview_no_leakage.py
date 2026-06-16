import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview"
COMPARISON_JSON = PREVIEW_DIR / "v2_plus_all_bus_fault_preview_comparison.json"
COMPARISON_MD = PREVIEW_DIR / "v2_plus_all_bus_fault_preview_comparison.md"
COMPARISON_CSV = PREVIEW_DIR / "v2_plus_all_bus_fault_preview_comparison.csv"
DOC_PATH = ROOT / "docs/ieee39_v2_plus_all_bus_fault_preview_no_leakage_comparison.md"

EXPECTED_MODES = [
    "include_all_79_candidates",
    "no_dynamic_measurement_features",
    "label_family_holdout",
    "bus_fault_holdout",
    "leave_one_bus_fault_out",
    "no_dynamic_measurement_leave_one_bus_fault_out",
    "existing_vs_new_bus_fault_check",
]


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8") as handle:
        return handle.read()


def test_preview_artifacts_exist() -> None:
    assert os.path.exists(_long(COMPARISON_JSON))
    assert os.path.exists(_long(COMPARISON_MD))
    assert os.path.exists(_long(COMPARISON_CSV))
    assert os.path.exists(_long(DOC_PATH))
    for mode in EXPECTED_MODES:
        metrics = PREVIEW_DIR / mode / "preview_training_metrics.json"
        assert os.path.exists(_long(metrics)), mode


def test_preview_summary_boundaries_and_counts() -> None:
    payload = _read_json(COMPARISON_JSON)
    assert payload["preview_only"] is True
    assert payload["final_performance_conclusion"] is False
    assert payload["total_candidate_rows"] == 79
    assert payload["num_total_bus_fault_candidates"] == 39
    assert payload["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert payload["unstable_flag_false_buses"] == ["B1"]
    assert payload["include_all_is_leaky_upper_bound"] is True
    assert payload["target_feature_leakage_risk_if_used_as_inputs"] is True
    assert payload["no_dynamic_measurement_feature_set_required_for_future_audit"] is True
    assert payload["simulink_run"] is False
    assert payload["actual_smoke_run"] is False
    assert payload["labels_exported"] is False
    assert payload["gcn_trained"] is False
    assert payload["formal_reranker_retrained"] is False
    assert payload["gcn_usefulness_audit_run"] is False
    assert payload["should_train_now"] is False
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["l12_excluded"] is True
    assert payload["nf06_provenance_warning_preserved"] is True


def test_preview_summary_metrics_present() -> None:
    payload = _read_json(COMPARISON_JSON)
    for key in [
        "include_all_79_rmse",
        "no_dynamic_measurement_rmse",
        "label_family_holdout_rmse",
        "bus_fault_holdout_rmse",
        "leave_one_bus_fault_out_rmse",
        "leave_one_bus_fault_out_mae",
        "no_dynamic_measurement_leave_one_bus_fault_out_rmse",
        "no_dynamic_measurement_leave_one_bus_fault_out_mae",
        "b1_true_dynamic_stress_score",
        "b1_predicted_dynamic_stress_score",
        "b1_absolute_error",
        "b1_true_unstable_flag",
        "b1_unstable_probability",
        "worst_10_lobo_buses_by_abs_error",
        "recommended_next_step",
    ]:
        assert key in payload
        assert payload[key] is not None
    assert payload["include_all_79_rmse"] > 0.0
    assert payload["no_dynamic_measurement_rmse"] > 0.0
    assert payload["bus_fault_holdout_rmse"] > 0.0
    assert payload["leave_one_bus_fault_out_rmse"] > 0.0
    assert payload["no_dynamic_measurement_leave_one_bus_fault_out_rmse"] > 0.0
    assert 0.0 <= payload["b1_unstable_probability"] <= 1.0
    assert len(payload["worst_10_lobo_buses_by_abs_error"]) == 10


def test_mode_metrics_have_expected_shapes() -> None:
    leave_one = _read_json(PREVIEW_DIR / "leave_one_bus_fault_out" / "preview_training_metrics.json")
    no_dynamic_leave_one = _read_json(PREVIEW_DIR / "no_dynamic_measurement_leave_one_bus_fault_out" / "preview_training_metrics.json")
    bus_holdout = _read_json(PREVIEW_DIR / "bus_fault_holdout" / "preview_training_metrics.json")
    existing_vs_new = _read_json(PREVIEW_DIR / "existing_vs_new_bus_fault_check" / "preview_training_metrics.json")
    assert leave_one["lobo_rmse"] > 0.0
    assert leave_one["lobo_mae"] > 0.0
    assert len(leave_one["per_bus_predictions"]) == 39
    assert len(leave_one["worst_10_buses_by_abs_error"]) == 10
    assert no_dynamic_leave_one["lobo_rmse"] > 0.0
    assert no_dynamic_leave_one["lobo_mae"] > 0.0
    assert len(no_dynamic_leave_one["per_bus_predictions"]) == 39
    assert len(bus_holdout["per_bus_predictions"]) == 39
    assert existing_vs_new["num_existing_bus_fault_candidates"] == 2
    assert existing_vs_new["num_new_bus_fault_candidates"] == 37


def test_preview_docs_keep_conservative_language() -> None:
    text = "\n".join(
        [
            _read_text(COMPARISON_MD),
            _read_text(DOC_PATH),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    current_text = "\n".join([_read_text(COMPARISON_MD), _read_text(DOC_PATH)]).lower()
    current_normalized = " ".join(current_text.replace("`", "").split())
    for required in [
        "preview/no-leakage comparison",
        "did not run simulink",
        "did not run actual smoke",
        "did not export labels",
        "did not train gcn",
        "did not retrain the formal reranker",
        "did not run a gcn usefulness audit",
        "leaky upper-bound",
        "candidate labels, not formal labels",
        "temporary smoke candidates",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
        "cannot directly prove gcn useful or not useful",
    ]:
        assert required in normalized
    for forbidden in [
        "this round ran simulink",
        "this round export labels",
        "gcn was trained",
        "gcn usefulness audit was run",
        "final performance conclusion is true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_normalized


def test_no_forbidden_preview_artifacts_are_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_all_bus_fault_preview"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden_tokens = [".slx", ".slxc", "slprj", ".mat", "raw_trajector", "full_timeseries", "local_lab_copies"]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden_tokens)]
    assert bad == []
