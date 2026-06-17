import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_paper_aligned_branch_gcn_redesign_dry_run"
DOC = ROOT / "docs/ieee39_paper_aligned_branch_gcn_redesign_dry_run.md"


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


def test_paper_aligned_branch_gcn_dry_run_generator_runs() -> None:
    subprocess.run(
        [
            sys.executable,
            "scripts/gcn_search/prepare_ieee39_paper_aligned_branch_gcn_redesign_dry_run.py",
            "--strict",
            "--write-report",
        ],
        cwd=ROOT,
        check=True,
        text=True,
    )


def test_paper_aligned_branch_gcn_dry_run_artifacts_exist() -> None:
    expected = [
        "paper_method_mapping_summary.json",
        "paper_method_mapping_summary.md",
        "ieee39_branch_topology_source_inventory.json",
        "ieee39_branch_topology_source_inventory.md",
        "ieee39_branch_as_node_graph_manifest.json",
        "ieee39_branch_as_node_graph_manifest.md",
        "paper_aligned_feature_manifest.json",
        "paper_aligned_feature_manifest.md",
        "paper_aligned_label_plan.json",
        "paper_aligned_label_plan.md",
        "hybrid_search_policy_plan.json",
        "hybrid_search_policy_plan.md",
        "paper_aligned_branch_gcn_dry_run_validator_summary.json",
        "paper_aligned_branch_gcn_dry_run_validator_summary.md",
        "paper_aligned_branch_gcn_dry_run_validator_summary.csv",
    ]
    for filename in expected:
        assert os.path.exists(_long(OUT_DIR / filename)), filename
    assert os.path.exists(_long(DOC))


def test_paper_aligned_branch_gcn_dry_run_summary_fields() -> None:
    summary = _read_json(OUT_DIR / "paper_aligned_branch_gcn_dry_run_validator_summary.json")
    graph = _read_json(OUT_DIR / "ieee39_branch_as_node_graph_manifest.json")
    inventory = _read_json(OUT_DIR / "ieee39_branch_topology_source_inventory.json")
    features = _read_json(OUT_DIR / "paper_aligned_feature_manifest.json")
    labels = _read_json(OUT_DIR / "paper_aligned_label_plan.json")

    assert summary["dry_run_scope"] == "paper_aligned_branch_gcn_redesign_dry_run"
    assert summary["gcn_training_run"] is False
    assert summary["formal_gcn_audit_rerun"] is False
    assert summary["simulink_run"] is False
    assert summary["labels_exported"] is False
    assert summary["reranker_retrained"] is False
    assert summary["production_model_saved"] is False
    assert summary["paper_graph_node_type"] == "branch"
    assert summary["paper_graph_edge_rule"] == "shared_endpoint_bus"
    assert summary["previous_repo_graph_type"] == "candidate_similarity_graph"
    assert summary["previous_candidate_as_node_design_deprecated"] is True
    assert summary["proposed_graph_type"] == "branch_as_node_physical_line_graph"
    assert summary["bus_fault_labels_directly_paper_aligned"] is False
    assert summary["line_trip_labels_first_priority"] is True
    assert summary["forbidden_features_detected_in_inputs"] == []
    assert summary["final_engineering_conclusion"] is False
    assert summary["should_train_gcn_now"] is False
    assert summary["should_rerun_formal_audit_now"] is False
    assert summary["should_retrain_reranker_now"] is False
    assert summary["should_deploy_model"] is False

    assert inventory["detected_num_buses"] == 39
    assert "B1" in inventory["detected_bus_ids"]
    assert "B39" in inventory["detected_bus_ids"]
    assert inventory["detected_num_branches"] == 34
    assert inventory["l12_mapping_status"]["mapping_found"] is True
    assert inventory["old_formal_gate_35_33_33_unchanged"] is True

    assert graph["graph_type"] == "paper_aligned_branch_as_node_line_graph"
    assert graph["graph_is_candidate_similarity_graph"] is False
    assert graph["graph_uses_physical_branch_connectivity"] is True
    assert graph["graph_construction_ready"] is True
    assert graph["num_branch_nodes"] == 34
    assert graph["num_graph_edges"] > 0

    assert features["forbidden_features_detected_in_inputs"] == []
    assert features["dynamic_measurements_forbidden"] is True
    assert features["dynamic_targets_only_used_as_labels"] is True
    assert features["no_leakage_feature_policy_passed"] is True
    assert features["feature_readiness_for_prototype"] is False
    assert labels["bus_fault_labels_directly_paper_aligned"] is False
    assert labels["line_trip_labels_first_priority"] is True


def test_paper_aligned_branch_gcn_dry_run_docs_are_conservative() -> None:
    text = "\n".join(
        [
            _read_text(DOC),
            _read_text(OUT_DIR / "paper_method_mapping_summary.md"),
            _read_text(OUT_DIR / "paper_aligned_feature_manifest.md"),
            _read_text(OUT_DIR / "paper_aligned_label_plan.md"),
            _read_text(ROOT / "docs/gcn_pio_validation_log.md"),
        ]
    ).lower()
    normalized = " ".join(text.replace("`", "").split())
    for required in [
        "paper-aligned branch gcn redesign dry-run",
        "does not train gcn",
        "does not rerun the formal audit",
        "does not run simulink",
        "does not export labels",
        "does not retrain the reranker",
        "not a candidate-row graph",
        "branch",
        "shared",
        "topology status",
        "relay ratio",
        "branch flow",
        "endpoint load",
        "branch vulnerability vector",
        "bus-fault labels are not directly equivalent",
        "line-trip labels should be the first priority",
        "post-fault dynamic measurements cannot be used as gcn inputs",
        "dynamic_stress_score and unstable_flag can only be labels",
        "phasor_rms is not emt",
        "generator_speed_proxy is not direct frequency",
        "temporary bus-fault injection is not engineering-grade protection",
    ]:
        assert required in normalized
    for forbidden in [
        "gcn is useful",
        "gcn is useless",
        "formal audit rerun completed",
        "final engineering conclusion: true",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "production_model_saved = true",
    ]:
        assert forbidden not in normalized


def test_paper_aligned_branch_gcn_dry_run_no_forbidden_large_artifacts_tracked() -> None:
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
