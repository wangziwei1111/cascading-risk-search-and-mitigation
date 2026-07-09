from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
SCALEUP = ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup"
sys.path.insert(0, str(IEEE118))

from summarize_ieee118_experiment_narrative import (
    build_claims,
    build_method_taxonomy,
    build_search_keyk_comparison,
    run_synthesis,
)


def test_method_taxonomy_contains_pr11_to_pr18() -> None:
    taxonomy = build_method_taxonomy({f"pr{i}" for i in range(11, 19)})
    labels = set(taxonomy["method_or_pr"])
    assert "PR #11 early-stop" in labels
    assert "PR #18 strict fragility" in labels
    assert len(taxonomy) == 8


def test_smoke_pilot_formal_diagnostic_and_improvement_categories() -> None:
    taxonomy = build_method_taxonomy({f"pr{i}" for i in range(11, 19)}).set_index("method_or_pr")
    assert bool(taxonomy.loc["PR #11 early-stop", "is_formal_result"])
    assert bool(taxonomy.loc["PR #14 pilot-2000", "is_pilot_result"])
    assert taxonomy.loc["PR #13 12-state smoke", "category"] == "pipeline_smoke"
    assert bool(taxonomy.loc["PR #15 S0 bottleneck", "is_diagnostic"])
    assert bool(taxonomy.loc["PR #16 alpha path-prob", "is_improvement"])
    assert bool(taxonomy.loc["PR #18 strict fragility", "is_improvement"])


def test_paper_ready_claims_are_split_and_include_forbidden_phrases() -> None:
    claims = build_claims()
    assert {"main_text_claims", "diagnostic_or_ablation_claims", "forbidden_claims"}.issubset(claims)
    forbidden = " ".join(item["claim"] for item in claims["forbidden_claims"])
    assert "pilot-2000 is equivalent to paper-8000" in forbidden
    assert "Algorithm1 is currently the best IEEE118 method" in forbidden


def test_keyk_comparison_contains_core_methods() -> None:
    comparison = build_search_keyk_comparison(SCALEUP)
    methods = set(comparison["method"])
    assert {
        "strict_path_prob",
        "second_only",
        "best_alpha_path_prob",
        "any_critical_fragility_path_prob",
        "best_strict_fragility_path_prob",
        "Algorithm1",
    }.issubset(methods)
    assert {100, 500, 1000, 5000}.issubset(set(comparison["K"].astype(int)))
    row = comparison.loc[(comparison["method"].eq("best_strict_fragility_path_prob")) & (comparison["K"].eq(1000))].iloc[0]
    assert row["critical_hits"] == 676


def test_pr17_and_pr18_positioning_is_not_overstated() -> None:
    taxonomy = build_method_taxonomy({f"pr{i}" for i in range(11, 19)}).set_index("method_or_pr")
    assert taxonomy.loc["PR #17 any-critical fragility", "category"] == "diagnostic_failed_label"
    assert bool(taxonomy.loc["PR #17 any-critical fragility", "should_be_appendix"])
    assert taxonomy.loc["PR #18 strict fragility", "category"] == "strict_fragility_refinement"
    assert "not a decisive breakthrough" in taxonomy.loc["PR #18 strict fragility", "caveat"]


def test_run_synthesis_writes_expected_outputs(tmp_path: Path) -> None:
    args = argparse.Namespace(
        results_root=SCALEUP,
        output_dir=tmp_path / "synthesis",
        include_pr11=True,
        include_pr12=True,
        include_pr13=True,
        include_pr14=True,
        include_pr15=True,
        include_pr16=True,
        include_pr17=True,
        include_pr18=True,
    )
    outputs = run_synthesis(args)
    expected = {
        "timeline",
        "taxonomy",
        "key_results",
        "search",
        "classification",
        "bottleneck",
        "improvements",
        "claims",
        "readme",
    }
    assert expected.issubset(outputs)
    for path in outputs.values():
        assert Path(path).exists()
    claims = json.loads(Path(outputs["claims"]).read_text(encoding="utf-8"))
    assert claims["main_text_claims"]
    readme = Path(outputs["readme"]).read_text(encoding="utf-8")
    assert "does not rerun OPA" in readme


def test_output_files_are_compact_and_no_large_artifacts_are_tracked(tmp_path: Path) -> None:
    args = argparse.Namespace(
        results_root=SCALEUP,
        output_dir=tmp_path / "synthesis",
        include_pr11=False,
        include_pr12=False,
        include_pr13=False,
        include_pr14=False,
        include_pr15=False,
        include_pr16=False,
        include_pr17=False,
        include_pr18=False,
    )
    outputs = run_synthesis(args)
    assert all(Path(path).stat().st_size < 200_000 for path in outputs.values())
    tracked = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    forbidden_suffixes = (
        ".npz",
        ".pt",
        "ieee118_step2_state_samples.csv",
        "s0_bottleneck_full_score_table_local_only.csv",
        "original_rts79_gcn_ieee118_predictions.csv",
    )
    tracked_synthesis = [path for path in tracked if "ieee118_experiment_synthesis" in path]
    assert not [path for path in tracked_synthesis if path.endswith(forbidden_suffixes)]

