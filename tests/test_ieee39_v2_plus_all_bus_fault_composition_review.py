import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "batch_bus_fault_expansion_all_remaining/no_training_composition_review"
)
DOC = ROOT / "docs/ieee39_v2_plus_all_bus_fault_no_training_composition_review.md"


def _long(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _exists(path: Path) -> bool:
    return os.path.exists(_long(path))


def _read_json(path: Path) -> dict:
    with open(_long(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_text(path: Path) -> str:
    with open(_long(path), encoding="utf-8") as handle:
        return handle.read()


def test_composition_review_artifacts_exist() -> None:
    for name in [
        "v2_plus_all_bus_fault_composition_review.json",
        "v2_plus_all_bus_fault_composition_review.md",
        "v2_plus_all_bus_fault_composition_review.csv",
        "all_bus_fault_coverage_check.json",
        "schema_and_duplicate_check.json",
        "leakage_risk_and_training_boundary_check.json",
    ]:
        assert _exists(REVIEW_DIR / name), name
    assert _exists(DOC)


def test_composition_review_counts_and_coverage() -> None:
    review = _read_json(REVIEW_DIR / "v2_plus_all_bus_fault_composition_review.json")
    assert review["review_scope"] == "no_training_composition_review"
    assert review["total_candidate_rows"] == 79
    assert review["row_count_check_passed"] is True
    assert review["num_total_bus_fault_candidates"] == 39
    assert review["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert review["missing_bus_fault_buses"] == []
    assert review["every_bus_fault_row_has_line_id_NO_LINE"] is True
    assert review["every_bus_fault_row_has_target_bus_filled"] is True
    assert review["every_bus_fault_row_has_target_bus_or_component_filled"] is True
    assert review["every_bus_fault_row_candidate_not_formal_label_true"] is True
    assert review["every_bus_fault_row_formal_line_trip_label_false"] is True
    assert review["every_bus_fault_row_bus_fault_label_true"] is True
    assert review["every_bus_fault_row_temporary_smoke_candidate_true"] is True
    assert review["every_bus_fault_row_quality_review_passed_true"] is True
    assert review["scenario_id_duplicates"] == []
    assert review["label_id_v2_duplicates"] == []
    assert review["dynamic_stress_score_nonfinite_rows"] == []
    assert review["unstable_flag_false_buses"] == ["B1"]
    assert review["old_formal_gate"] == "35 / 33 / 33"
    assert review["formal_label_gate_changed"] is False
    assert review["l12_excluded"] is True
    assert review["nf06_provenance_warning_preserved"] is True
    assert review["composition_review_passed"] is True


def test_composition_subreports() -> None:
    coverage = _read_json(REVIEW_DIR / "all_bus_fault_coverage_check.json")
    schema = _read_json(REVIEW_DIR / "schema_and_duplicate_check.json")
    leakage = _read_json(REVIEW_DIR / "leakage_risk_and_training_boundary_check.json")
    assert coverage["missing_bus_fault_buses"] == []
    assert coverage["num_covered_buses"] == 39
    assert coverage["all_ieee39_buses_have_bus_fault_candidate"] is True
    assert schema["required_columns_present"] is True
    assert schema["scenario_id_duplicates"] == []
    assert schema["label_id_v2_duplicates"] == []
    assert schema["dynamic_stress_score_nonfinite_rows"] == []
    assert leakage["compact_dynamic_measurement_features_are_post_fault"] is True
    assert leakage["target_feature_leakage_risk_if_used_as_inputs"] is True
    assert leakage["no_dynamic_measurement_feature_set_required_for_future_audit"] is True
    assert leakage["label_family_holdout_required_for_future_audit"] is True
    assert leakage["bus_fault_holdout_required_for_future_audit"] is True
    assert leakage["leave_one_bus_fault_out_required_for_future_audit"] is True
    assert leakage["simulink_run"] is False
    assert leakage["actual_smoke_run"] is False
    assert leakage["labels_exported"] is False
    assert leakage["gcn_trained"] is False
    assert leakage["reranker_retrained"] is False
    assert leakage["gcn_usefulness_audit_run"] is False
    assert leakage["preview_training_run"] is False
    assert leakage["should_train_now"] is False


def test_composition_docs_are_conservative() -> None:
    doc_paths = [
        DOC,
        REVIEW_DIR / "v2_plus_all_bus_fault_composition_review.md",
        ROOT / "docs/gcn_pio_validation_log.md",
        ROOT / "docs/ieee39_all_remaining_bus_fault_candidate_label_export.md",
        ROOT / "docs/ieee39_all_remaining_bus_fault_batch_smoke_quality_review.md",
        ROOT / "docs/ieee39_v2_plus_b39_b26_preview_no_leakage_comparison.md",
        ROOT / "docs/ieee39_v2_plus_b39_b26_no_training_composition_review.md",
    ]
    text = "\n".join(_read_text(Path(path)).lower() for path in doc_paths if _exists(path))
    current_text = "\n".join(
        _read_text(Path(path)).lower()
        for path in [DOC, REVIEW_DIR / "v2_plus_all_bus_fault_composition_review.md"]
        if _exists(path)
    )
    for required in [
        "no-training composition review",
        "did not run simulink",
        "did not run actual smoke",
        "did not export labels",
        "did not train gcn",
        "did not retrain the reranker",
        "did not run a gcn usefulness audit",
        "candidate_not_formal_label",
        "not formal labels",
        "35 / 33 / 33",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
        "target-feature leakage",
        "preview/no-leakage comparison",
    ]:
        assert required in text
    for forbidden in [
        "this round ran simulink",
        "this round export labels",
        "gcn was trained",
        "gcn usefulness audit was run",
        "bus-fault labels are formal labels",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in current_text


def test_no_forbidden_result_artifacts_tracked_for_composition_review() -> None:
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/batch_bus_fault_expansion_all_remaining/no_training_composition_review",
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    forbidden_tokens = [
        ".pt",
        ".npz",
        ".slx",
        ".slxc",
        ".mat",
        "slprj",
        "raw_trajectories",
        "full_timeseries",
        "local_lab_copies",
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden_tokens)]
