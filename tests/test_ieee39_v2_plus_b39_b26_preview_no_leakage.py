import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview"
COMPARISON_JSON = PREVIEW_DIR / "v2_plus_b39_b26_preview_comparison.json"
COMPARISON_MD = PREVIEW_DIR / "v2_plus_b39_b26_preview_comparison.md"
DOC_PATH = ROOT / "docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md"


EXPECTED_MODES = [
    "include_all_42_candidates",
    "exclude_provenance_required",
    "no_dynamic_measurement_features",
    "label_family_holdout",
    "bus_fault_holdout",
    "b39_holdout",
    "b26_holdout",
]


def _load_comparison() -> dict:
    assert COMPARISON_JSON.exists()
    return json.loads(COMPARISON_JSON.read_text(encoding="utf-8"))


def test_preview_artifacts_exist() -> None:
    assert COMPARISON_JSON.exists()
    assert COMPARISON_MD.exists()
    assert DOC_PATH.exists()
    for mode in EXPECTED_MODES:
        metrics_path = PREVIEW_DIR / mode / "preview_training_metrics.json"
        assert metrics_path.exists(), mode
        payload = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert payload["preview_only"] is True
        assert payload["final_performance_conclusion"] is False
        assert payload["gcn_trained"] is False
        assert payload["gcn_usefulness_audit_run"] is False
        assert payload["formal_reranker_retrained"] is False
        assert payload["simulink_run"] is False
        assert payload["labels_exported"] is False


def test_preview_summary_boundaries_and_counts() -> None:
    payload = _load_comparison()
    assert payload["preview_only"] is True
    assert payload["final_performance_conclusion"] is False
    assert payload["gcn_trained"] is False
    assert payload["gcn_usefulness_audit_run"] is False
    assert payload["formal_reranker_retrained"] is False
    assert payload["simulink_run"] is False
    assert payload["labels_exported"] is False
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["v2_plus_b39_b26_candidate_count"] == 42
    assert payload["previous_v2_plus_b39_count"] == 41
    assert payload["num_bus_fault_candidates"] == 2
    assert payload["b39_status"] == "candidate_label_not_formal"
    assert payload["b26_status"] == "candidate_label_not_formal"
    assert payload["l12_excluded"] is True
    assert payload["nf06_provenance_warning_preserved"] is True
    assert payload["leakage_risk_reviewed"] is True
    assert payload["target_feature_leakage_risk_if_dynamic_measurements_used"] is True
    assert payload["can_directly_validate_gcn"] is False


def test_preview_summary_metrics_present() -> None:
    payload = _load_comparison()
    for key in [
        "include_all_42_rmse",
        "no_dynamic_measurement_rmse",
        "label_family_holdout_rmse",
        "bus_fault_holdout_rmse",
        "b39_holdout_absolute_error",
        "b26_holdout_absolute_error",
        "b39_true_dynamic_stress_score",
        "b39_predicted_dynamic_stress_score",
        "b26_true_dynamic_stress_score",
        "b26_predicted_dynamic_stress_score",
        "b39_unstable_probability",
        "b26_unstable_probability",
        "recommended_next_step",
    ]:
        assert key in payload
        assert payload[key] is not None
    assert payload["include_all_42_rmse"] > 0.0
    assert payload["no_dynamic_measurement_rmse"] > 0.0
    assert payload["bus_fault_holdout_rmse"] > 0.0
    assert 0.0 <= payload["b39_unstable_probability"] <= 1.0
    assert 0.0 <= payload["b26_unstable_probability"] <= 1.0


def test_preview_docs_keep_conservative_language() -> None:
    text = "\n".join(
        [
            COMPARISON_MD.read_text(encoding="utf-8"),
            DOC_PATH.read_text(encoding="utf-8"),
            (ROOT / "docs/gcn_pio_validation_log.md").read_text(encoding="utf-8"),
        ]
    ).lower()
    text = " ".join(text.replace("`", "").split())
    for required in [
        "preview/no-leakage comparison",
        "does not train gcn",
        "does not run a gcn usefulness audit",
        "candidate labels, not formal labels",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
        "collect more bus-fault candidates before gcn usefulness audit",
    ]:
        assert required in text
    for forbidden in [
        "gcn usefulness audit has been run",
        "gcn is useful",
        "gcn is not useful",
        "formal reranker has been retrained",
        "b39 and b26 are formal labels",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in text


def test_no_forbidden_preview_artifacts_are_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_b26_preview"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    forbidden_tokens = [".slx", ".slxc", "slprj", ".mat", "raw_trajector", "full_timeseries", "local_lab_copies"]
    bad = [path for path in result.stdout.splitlines() if any(token in path.lower() for token in forbidden_tokens)]
    assert bad == []
