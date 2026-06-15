import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export"
)
REVIEW_DIR = EXPORT_DIR / "no_training_composition_review"
DOC_PATH = ROOT / "docs/ieee39_v2_plus_b39_b26_no_training_composition_review.md"


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def test_v2_plus_b39_b26_composition_review_artifacts_exist():
    for name in [
        "ieee39_v2_plus_b39_b26_composition_review.json",
        "ieee39_v2_plus_b39_b26_composition_review.md",
        "ieee39_v2_plus_b39_b26_label_family_counts.csv",
        "ieee39_v2_plus_b39_b26_fault_type_counts.csv",
        "ieee39_v2_plus_b39_b26_bus_fault_comparison.csv",
    ]:
        path = REVIEW_DIR / name
        assert path.exists(), name
        assert path.stat().st_size > 0, name
    assert DOC_PATH.exists()
    assert DOC_PATH.stat().st_size > 0


def test_v2_plus_b39_b26_review_boundaries_and_counts():
    review = json.loads((REVIEW_DIR / "ieee39_v2_plus_b39_b26_composition_review.json").read_text())
    assert review["review_scope"] == "no_training_composition_comparison"
    assert review["simulink_run"] is False
    assert review["labels_exported"] is False
    assert review["gcn_trained"] is False
    assert review["reranker_retrained"] is False
    assert review["preview_training_run"] is False
    assert review["gcn_usefulness_audit_run"] is False
    assert review["previous_v2_plus_b39_count"] == 41
    assert review["v2_plus_b39_b26_candidate_count"] == 42
    assert review["num_new_b26_bus_fault_candidates"] == 1
    assert review["num_bus_fault_candidates"] == 2
    assert review["b39_candidate_present"] is True
    assert review["b26_candidate_present"] is True
    assert set(review["bus_fault_targets"]) == {"B39", "B26"}
    assert review["old_formal_gate"] == "35 / 33 / 33"
    assert review["l12_excluded"] is True
    assert review["nf06_provenance_warning_preserved"] is True
    assert review["should_train_now"] is False


def test_v2_plus_b39_b26_schema_duplicate_and_leakage_checks_pass():
    review = json.loads((REVIEW_DIR / "ieee39_v2_plus_b39_b26_composition_review.json").read_text())
    assert review["bus_fault_target_bus_complete"] is True
    assert review["bus_fault_target_bus_or_component_complete"] is True
    assert review["bus_fault_line_id_no_line"] is True
    assert review["b39_b26_schema_consistency_passed"] is True
    assert review["count_consistency_passed"] is True
    assert review["export_boundary_passed"] is True
    assert review["b39_exact_duplicate"] is False
    assert review["b26_exact_duplicate"] is False
    assert review["b39_b26_duplicate_measurement_group"] is False
    assert review["scenario_id_duplicates"] == []
    assert review["label_id_v2_duplicates"] == []
    assert review["leakage_risk_reviewed"] is True
    assert review["compact_dynamic_measurement_features_are_post_fault"] is True
    assert review["target_feature_leakage_risk_if_used_as_inputs"] is True
    assert review["all_no_training_composition_checks_passed"] is True


def test_v2_plus_b39_b26_count_tables_and_bus_fault_comparison():
    family = pd.read_csv(REVIEW_DIR / "ieee39_v2_plus_b39_b26_label_family_counts.csv")
    fault_type = pd.read_csv(REVIEW_DIR / "ieee39_v2_plus_b39_b26_fault_type_counts.csv")
    comparison = pd.read_csv(REVIEW_DIR / "ieee39_v2_plus_b39_b26_bus_fault_comparison.csv")
    family_counts = dict(zip(family["label_family"], family["count"]))
    fault_counts = dict(zip(fault_type["fault_type"], fault_type["count"]))
    assert family_counts["existing_formal_dynamic"] == 35
    assert family_counts["non_line_trip"] == 7
    assert fault_counts["three_phase_bus_fault_temp_smoke"] == 2
    assert len(comparison) == 2
    assert set(comparison["scenario_id"]) == {"BF_B39_TEMP_SMOKE", "BF_B26_TEMP_SMOKE"}
    for _, row in comparison.iterrows():
        assert row["target_bus"] in {"B39", "B26"}
        assert row["target_bus_or_component"] == row["target_bus"]
        assert row["line_id"] == "NO_LINE"
        assert row["fault_type"] == "three_phase_bus_fault_temp_smoke"
        assert _as_bool(row["candidate_not_formal_label"])
        assert not _as_bool(row["exact_duplicate"])
        assert not _as_bool(row["provenance_risk"])


def test_v2_plus_b39_b26_docs_do_not_overstate_boundaries():
    doc_paths = [
        DOC_PATH,
        ROOT / "docs/gcn_pio_validation_log.md",
        ROOT / "docs/ieee39_b26_bus_fault_candidate_label_export.md",
        ROOT / "docs/ieee39_v2_plus_b39_no_training_composition_review.md",
        ROOT / "docs/ieee39_v2_plus_b39_preview_interpretation.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in doc_paths)
    for required in [
        "no-training composition review",
        "does not run simulink",
        "does not export new labels",
        "does not train gcn",
        "does not retrain",
        "does not run a gcn usefulness audit",
        "candidate count: `42`",
        "b39",
        "b26",
        "candidate labels, not formal labels",
        "35 / 33 / 33",
        "l12",
        "nf06",
        "target-feature leakage risk",
        "no-dynamic-measurement",
        "not emt",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in text
    for forbidden in [
        "gcn trained: `true`",
        "reranker retrained: `true`",
        "gcn usefulness audit completed",
        "b39 and b26 are formal labels",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in text


def test_no_forbidden_result_artifacts_tracked_for_v2_plus_b39_b26_review():
    result = subprocess.run(
        [
            "git",
            "ls-files",
            "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b26_candidate_label_export",
        ],
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
    ]
    tracked = [line.strip().lower() for line in result.stdout.splitlines() if line.strip()]
    assert not [path for path in tracked if any(token in path for token in forbidden_tokens)]
