import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREVIEW_DIR = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview"
DOC_PATH = ROOT / "docs/ieee39_v2_plus_b39_preview_training.md"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v2_plus_b39_preview_artifacts_exist():
    assert (PREVIEW_DIR / "v2_plus_b39_preview_comparison.json").exists()
    assert (PREVIEW_DIR / "v2_plus_b39_preview_comparison.md").exists()
    for mode in [
        "include_all_41_candidates",
        "exclude_provenance_required",
        "no_dynamic_measurement_features",
        "label_family_holdout",
        "bus_fault_holdout",
    ]:
        path = PREVIEW_DIR / mode / "preview_training_metrics.json"
        assert path.exists(), mode
        assert path.stat().st_size > 0, mode


def test_v2_plus_b39_preview_comparison_boundaries_and_counts():
    payload = _read_json(PREVIEW_DIR / "v2_plus_b39_preview_comparison.json")
    assert payload["preview_only"] is True
    assert payload["final_performance_conclusion"] is False
    assert payload["previous_v2_candidate_count"] == 40
    assert payload["v2_plus_b39_candidate_count"] == 41
    assert payload["b39_candidate_count"] == 1
    assert payload["old_formal_gate"] == "35 / 33 / 33"
    assert payload["l12_excluded"] is True
    assert payload["nf06_provenance_warning_preserved"] is True
    assert payload["b39_schema_consistency_passed"] is True
    for key in [
        "include_all_41_metrics",
        "exclude_provenance_metrics",
        "no_dynamic_measurement_features_metrics",
        "label_family_holdout_metrics",
        "bus_fault_holdout_metrics",
    ]:
        assert key in payload


def test_v2_plus_b39_preview_modes_have_expected_metadata():
    include_all = _read_json(PREVIEW_DIR / "include_all_41_candidates" / "preview_training_metrics.json")
    exclude = _read_json(PREVIEW_DIR / "exclude_provenance_required" / "preview_training_metrics.json")
    no_dynamic = _read_json(PREVIEW_DIR / "no_dynamic_measurement_features" / "preview_training_metrics.json")
    label_holdout = _read_json(PREVIEW_DIR / "label_family_holdout" / "preview_training_metrics.json")
    bus_holdout = _read_json(PREVIEW_DIR / "bus_fault_holdout" / "preview_training_metrics.json")

    assert include_all["num_samples"] == 41
    assert include_all["contains_b39"] is True
    assert include_all["contains_nf06"] is True
    assert include_all["num_bus_fault_candidates"] == 1
    assert include_all["num_non_line_trip_candidates"] == 6
    assert include_all["num_formal_v1_rows"] == 35
    assert include_all["cv_strategy"] == "leave_one_out"

    assert exclude["num_samples"] == 40
    assert exclude["contains_b39"] is True
    assert exclude["contains_nf06"] is False
    assert exclude["excluded_provenance_required"] is True

    assert no_dynamic["feature_set"] == "no_dynamic_measurement_features"
    assert no_dynamic["num_samples"] == 41
    assert no_dynamic["leakage_reduced"] is True
    assert "min_voltage_pu" not in no_dynamic["feature_columns"]
    assert "dynamic_stress_score" not in no_dynamic["feature_columns"]
    assert "unstable_flag" not in no_dynamic["feature_columns"]

    assert label_holdout["split_strategy"] == "label_family_holdout"
    assert label_holdout["train_label_family"] == "existing_formal_dynamic"
    assert label_holdout["test_label_family"] == "non_line_trip"
    assert label_holdout["num_test_non_line_trip"] == 6
    assert label_holdout["num_test_bus_fault"] == 1
    assert label_holdout["classification_skipped_reason"]

    assert bus_holdout["split_strategy"] == "bus_fault_holdout"
    assert bus_holdout["num_test"] == 1
    assert bus_holdout["test_scenario_id"] == "BF_B39_TEMP_SMOKE"
    assert bus_holdout["target_bus"] == "B39"
    assert bus_holdout["regression_absolute_error"] >= 0.0
    assert bus_holdout["classification_probability_if_available"] is not None
    assert bus_holdout["skipped_metrics_reason"]


def test_v2_plus_b39_preview_docs_are_conservative():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for required in [
        "not gcn training",
        "does not run simulink",
        "does not submit `.slx`",
        "candidate label, not formal label",
        "v2-plus-b39 candidate count: `41`",
        "phasor_rms`, not emt",
        "generator_speed_proxy` is not direct frequency",
        "not engineering-grade protection",
        "preview-only",
    ]:
        assert required in text
    for forbidden in [
        "gcn trained",
        "is a final performance conclusion",
        "final performance conclusion = true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in text


def test_no_forbidden_result_artifacts_tracked_for_preview_training():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_aware_reranker_v2_plus_b39_preview"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden_tokens = [
        ".slx",
        ".slxc",
        "slprj",
        ".mat",
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
        ".pt",
        ".npz",
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden_tokens)]
