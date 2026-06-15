import json
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export"
)
REVIEW_DIR = EXPORT_DIR / "no_training_composition_review"
DOC_PATH = ROOT / "docs/ieee39_v2_plus_b39_no_training_composition_review.md"


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def test_v2_plus_b39_composition_review_artifacts_exist():
    for name in [
        "ieee39_v2_plus_b39_composition_review.json",
        "ieee39_v2_plus_b39_composition_review.md",
        "ieee39_v2_plus_b39_label_family_counts.csv",
        "ieee39_v2_plus_b39_fault_type_counts.csv",
        "ieee39_v2_plus_b39_bus_fault_comparison.csv",
    ]:
        path = REVIEW_DIR / name
        assert path.exists(), name
        assert path.stat().st_size > 0, name
    assert DOC_PATH.exists()


def test_v2_plus_b39_candidate_schema_has_complete_b39_target_bus():
    candidate_csv = pd.read_csv(EXPORT_DIR / "ieee39_b39_bus_fault_dynamic_label_candidate.csv")
    candidate_json = json.loads(
        (EXPORT_DIR / "ieee39_b39_bus_fault_dynamic_label_candidate.json").read_text()
    )
    combined = pd.read_csv(EXPORT_DIR / "ieee39_dynamic_label_schema_v2_plus_b39_candidate.csv")
    csv_row = candidate_csv.iloc[0]
    combined_row = combined.loc[combined["scenario_id"].astype(str) == "BF_B39_TEMP_SMOKE"].iloc[0]
    assert csv_row["target_bus"] == "B39"
    assert candidate_json["target_bus"] == "B39"
    assert candidate_json["target_bus_or_component"] == "B39"
    assert combined_row["target_bus"] == "B39"
    assert combined_row["target_bus_or_component"] == "B39"
    assert combined_row["line_id"] == "NO_LINE"
    assert combined_row["fault_type"] == "three_phase_bus_fault_temp_smoke"
    assert _as_bool(combined_row["bus_fault_label"])
    assert _as_bool(combined_row["candidate_not_formal_label"])


def test_v2_plus_b39_review_counts_and_gates():
    review = json.loads((REVIEW_DIR / "ieee39_v2_plus_b39_composition_review.json").read_text())
    assert review["previous_v2_candidate_count"] == 40
    assert review["v2_plus_b39_candidate_count"] == 41
    assert review["num_new_b39_bus_fault_candidates"] == 1
    assert review["old_formal_gate"] == "35 / 33 / 33"
    assert review["num_formal_v1_existing"] == 35
    assert review["num_handwired_line_trip"] == 33
    assert review["num_non_line_trip_candidates"] == 6
    assert review["num_bus_fault_candidates"] == 1
    assert review["num_temporary_smoke_candidates"] == 1
    assert review["num_candidate_not_formal_label"] == 1
    assert review["num_training_ready_label_candidate"] == 41
    assert review["l12_excluded"] is True
    assert review["nf06_provenance_warning_preserved"] is True
    assert review["b39_exact_duplicate"] is False
    assert review["b39_provenance_risk"] is False
    assert review["b39_target_bus_complete"] is True
    assert review["b39_target_bus_or_component_complete"] is True
    assert review["b39_schema_consistency_passed"] is True
    assert review["count_consistency_passed"] is True
    assert review["export_boundary_passed"] is True
    assert review["should_train_now"] is False


def test_v2_plus_b39_count_tables_capture_bus_fault_candidate():
    family = pd.read_csv(REVIEW_DIR / "ieee39_v2_plus_b39_label_family_counts.csv")
    fault_type = pd.read_csv(REVIEW_DIR / "ieee39_v2_plus_b39_fault_type_counts.csv")
    comparison = pd.read_csv(REVIEW_DIR / "ieee39_v2_plus_b39_bus_fault_comparison.csv")
    family_counts = dict(zip(family["label_family"], family["count"]))
    fault_counts = dict(zip(fault_type["fault_type"], fault_type["count"]))
    assert family_counts["existing_formal_dynamic"] == 35
    assert family_counts["non_line_trip"] == 6
    assert fault_counts["three_phase_bus_fault_temp_smoke"] == 1
    assert len(comparison) == 1
    row = comparison.iloc[0]
    assert row["scenario_id"] == "BF_B39_TEMP_SMOKE"
    assert row["target_bus"] == "B39"
    assert row["target_bus_or_component"] == "B39"
    assert not _as_bool(row["exact_duplicate"])
    assert not _as_bool(row["provenance_risk"])


def test_v2_plus_b39_docs_do_not_overstate_boundaries():
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for required in [
        "does not run simulink",
        "does not submit `.slx`",
        "does not train gcn",
        "does not retrain",
        "candidate label, not a formal label",
        "target_bus`: `b39`",
        "target_bus_or_component`: `b39`",
        "should_train_now = false",
        "phasor_rms`, not emt",
        "generator_speed_proxy` is not direct frequency",
        "not engineering-grade protection",
        "label-family holdout",
        "no-leakage comparison",
    ]:
        assert required in text
    for forbidden in [
        "gcn trained: `true`",
        "reranker retrained: `true`",
        "is a final performance conclusion",
        "final performance conclusion = true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in text


def test_no_forbidden_result_artifacts_tracked_for_v2_plus_b39_review():
    result = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/b39_candidate_label_export"],
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
