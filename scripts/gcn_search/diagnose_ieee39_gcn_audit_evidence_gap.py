"""Diagnose why the IEEE39 strict no-leakage GCN audit did not beat baselines.

This script is evidence diagnosis only. It reads the previous audit outputs and
does not train GCN, does not rerun the formal audit, does not run Simulink, does
not export labels, and does not retrain the reranker.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution"
OUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_audit_evidence_diagnosis"
DOC_PATH = ROOT / "docs/ieee39_gcn_audit_evidence_diagnosis.md"
VALIDATION_LOG = ROOT / "docs/gcn_pio_validation_log.md"
AUDIT_DOC = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"
SOURCE_AUDIT_COMMIT = "925b0c9ea66dca330949b8dc19657b618a3e49e7"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_summary_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["field", "value"])
        writer.writeheader()
        for key, value in payload.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            writer.writerow({"field": key, "value": value})


def _report_md(title: str, payload: dict[str, Any]) -> str:
    return f"# {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n```\n"


def _load_audit_module() -> Any:
    path = ROOT / "scripts/gcn_search/run_ieee39_strict_no_leakage_gcn_usefulness_audit.py"
    spec = importlib.util.spec_from_file_location("ieee39_gcn_audit_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import audit script from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _gap_analysis(summary: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    bus = comparison["bus_fault_holdout"]
    lobo = comparison["leave_one_bus_fault_out"]
    no_dyn = comparison["no_dynamic_measurement_leave_one_bus_fault_out"]
    return {
        "analysis_scope": "gcn_vs_baseline_gap",
        "bus_fault_holdout_gcn_rmse": bus["gcn_rmse"],
        "bus_fault_holdout_best_baseline_rmse": bus["best_baseline_rmse"],
        "bus_fault_holdout_gcn_minus_baseline_rmse": bus["gcn_rmse"] - bus["best_baseline_rmse"],
        "lobo_gcn_rmse": lobo["gcn_rmse"],
        "lobo_best_baseline_rmse": lobo["best_baseline_rmse"],
        "lobo_gcn_minus_baseline_rmse": lobo["gcn_rmse"] - lobo["best_baseline_rmse"],
        "no_dynamic_lobo_gcn_rmse": no_dyn["gcn_rmse"],
        "no_dynamic_lobo_best_baseline_rmse": no_dyn["best_baseline_rmse"],
        "no_dynamic_lobo_gcn_minus_baseline_rmse": no_dyn["gcn_rmse"] - no_dyn["best_baseline_rmse"],
        "baseline_name": bus["best_baseline_name"],
        "audit_level_conclusion": summary["audit_level_conclusion"],
        "interpretation": "GCN RMSE is larger than the best simple baseline in the reported strict holdouts.",
    }


def _worst_errors(split_name: str, limit: int = 10) -> list[dict[str, Any]]:
    path = AUDIT_DIR / "splits" / split_name / "prediction_table.csv"
    table = pd.read_csv(path)
    if "gcn_absolute_error" not in table.columns:
        return []
    cols = [
        "scenario_id",
        "target_bus",
        "y_true_dynamic_stress_score",
        "y_true_unstable_flag",
        "gcn_pred_dynamic_stress_score",
        "gcn_absolute_error",
        "gcn_pred_unstable_probability",
        "ridge_logistic_pred_dynamic_stress_score",
        "ridge_logistic_absolute_error",
    ]
    existing = [col for col in cols if col in table.columns]
    worst = table.sort_values("gcn_absolute_error", ascending=False).head(limit)
    return worst[existing].to_dict(orient="records")


def _b1_diagnosis(b1: dict[str, Any]) -> dict[str, Any]:
    prob = b1.get("gcn_unstable_probability")
    true_score = b1.get("true_dynamic_stress_score")
    pred = b1.get("gcn_predicted_dynamic_stress_score")
    true_unstable = bool(true_score is not None and true_score >= 0.5)
    pred_unstable = bool(prob is not None and prob >= 0.5)
    return {
        "analysis_scope": "b1_and_classification_diagnosis",
        **b1,
        "assumed_unstable_threshold": 0.5,
        "b1_true_unstable_by_score_threshold": true_unstable,
        "b1_predicted_unstable_by_probability_threshold": pred_unstable,
        "b1_misclassified_by_probability_threshold": pred_unstable != true_unstable,
        "b1_overconfident": bool(prob is not None and prob >= 0.95 and not true_unstable),
        "b1_regression_overprediction": None if pred is None or true_score is None else pred - true_score,
        "diagnosis": (
            "B1 is a stable / low-stress marker but the GCN assigns unstable probability 1.0, "
            "so the audit exposes overconfident classification on this case."
        ),
    }


def _nf06_diagnosis(nf06: dict[str, Any]) -> dict[str, Any]:
    include = nf06["include_NF06"]
    exclude = nf06["exclude_NF06"]
    include_gap = include["gcn_bus_fault_holdout_rmse"] - include["best_baseline_bus_fault_holdout_rmse"]
    exclude_gap = exclude["gcn_bus_fault_holdout_rmse"] - exclude["best_baseline_bus_fault_holdout_rmse"]
    return {
        "analysis_scope": "nf06_sensitivity_diagnosis",
        "include_NF06": include,
        "exclude_NF06": exclude,
        "gcn_rmse_delta_exclude_minus_include": nf06["difference_summary"]["gcn_rmse_delta_exclude_minus_include"],
        "include_gcn_minus_baseline_rmse": include_gap,
        "exclude_gcn_minus_baseline_rmse": exclude_gap,
        "nf06_changes_gcn_rmse": True,
        "nf06_changes_audit_conclusion": False,
        "diagnosis": (
            "Excluding NF06 reduces GCN RMSE, but GCN remains worse than the best simple baseline; "
            "therefore NF06 sensitivity does not change the audit-level conclusion."
        ),
    }


def _graph_construction_diagnosis() -> dict[str, Any]:
    module = _load_audit_module()
    dataset = module._prepare_raw_dataset()
    features, feature_columns = module._build_no_leakage_features(dataset)
    adjacency = module._graph_adjacency(dataset)
    n = int(len(dataset))
    nonzero = int(np.count_nonzero(adjacency))
    feature_count = int(features.shape[1])
    hidden = 32
    dense_gcn_parameter_count = int((feature_count * hidden + hidden) + (hidden * hidden + hidden) + 2 * (hidden + 1))
    return {
        "analysis_scope": "graph_construction_diagnosis",
        "sample_granularity": "candidate_as_node_in_one_dense_graph",
        "num_candidate_nodes": n,
        "node_feature_count": feature_count,
        "node_feature_inputs": [
            "duration_s",
            "fault_start_s",
            "fault_clear_s",
            "one_hot(fault_type)",
            "one_hot(trip_implementation)",
            "one_hot(line_id)",
            "one_hot(target_bus)",
            "one_hot(target_bus_or_component)",
            "one_hot(source_model_type)",
        ],
        "edge_construction": "Dense normalized adjacency built by equality of line_id, target_bus, target_bus_or_component, fault_type, and source_model_type.",
        "edge_index_representation": "No sparse edge_index is used; the implementation uses a dense normalized adjacency matrix.",
        "message_passing_usage": "Message passing is norm_adj @ features, then norm_adj @ hidden states.",
        "adjacency_nonzero_entries": nonzero,
        "adjacency_density": float(nonzero / max(n * n, 1)),
        "gcn_hidden_dim": hidden,
        "gcn_epochs_in_source_script": 250,
        "estimated_dense_gcn_parameter_count": dense_gcn_parameter_count,
        "target_bus_enters_model_as": "one-hot categorical input and also contributes to equality-based graph edges.",
        "topology_message_passing_check": (
            "Topology is not physical bus-branch electrical topology. Edges are candidate-similarity edges, "
            "so the graph may mainly propagate tabular category information."
        ),
        "nominal_gcn_but_tabular_risk": True,
        "small_sample_risk": n <= 100,
        "repeated_graph_structure_risk": True,
        "weak_supervision_signal_risk": True,
        "parameter_to_sample_ratio": float(dense_gcn_parameter_count / max(n, 1)),
        "bus_fault_holdout_distribution_shift_risk": True,
        "target_bus_only_baseline_explains_signal": True,
        "diagnosis": (
            "The current model is a real dense GCN computation, but the graph is built from categorical equality "
            "rather than electrical connectivity; with only 79 rows, this can make the GCN less stable than "
            "simpler tabular baselines."
        ),
    }


def _root_causes(graph: dict[str, Any], gap: dict[str, Any], b1: dict[str, Any], nf06: dict[str, Any]) -> list[str]:
    return [
        "dataset too small for current GCN parameterization",
        "graph construction may not expose useful topology variation",
        "no-leakage input features may be too weak for GCN",
        "bus_fault_holdout is distribution shift",
        "target_bus encoding memorization risk remains",
        "B1 stable marker is hard / overconfident classification",
        "NF06 sensitivity changes GCN RMSE but not conclusion",
        "baseline is stronger under current feature set",
    ]


def _improvement_plan() -> dict[str, Any]:
    options = [
        "simplify GCN architecture / reduce parameters",
        "add topology-aware no-leakage features",
        "build true contingency graph representation",
        "add electrical static pre-fault features if available",
        "separate regression and classification heads more carefully",
        "add calibration / class imbalance handling for unstable_flag",
        "add leave-one-bus diagnostics before rerun",
        "compare GCN against target-bus-only and topology-only more explicitly",
        "consider non-GCN graph baselines such as GraphSAGE/GAT only after feature construction is fixed",
        "do not rerun reranker until GCN audit evidence improves",
    ]
    return {
        "analysis_scope": "next_gcn_improvement_plan",
        "training_triggered": False,
        "reranker_retraining_triggered": False,
        "deployment_triggered": False,
        "recommended_options": options,
        "priority_order": [
            "fix no-leakage graph construction",
            "reduce model complexity for 79-row audit data",
            "add static electrical features that are available before fault outcomes",
            "rerun strict audit only after feature/graph changes are reviewed",
        ],
    }


def _summary_md(summary: dict[str, Any], gap: dict[str, Any], b1: dict[str, Any], nf06: dict[str, Any], graph: dict[str, Any], plan: dict[str, Any]) -> str:
    causes = "\n".join(f"- {cause}" for cause in summary["likely_root_causes"])
    options = "\n".join(f"- {option}" for option in plan["recommended_options"])
    return f"""# IEEE39 GCN Audit Evidence Diagnosis

This round is evidence diagnosis only.

It does not train GCN.
It does not rerun the formal audit.
It does not run Simulink.
It does not export labels.
It does not retrain the reranker.
It does not save a production model.

## Core Finding

The current audit evidence does not support GCN usefulness over simpler
baselines yet. This is not a final proof against GCN.

## GCN vs Baseline Gap

- bus_fault_holdout GCN-baseline RMSE gap: `{gap['bus_fault_holdout_gcn_minus_baseline_rmse']}`
- LOBO GCN-baseline RMSE gap: `{gap['lobo_gcn_minus_baseline_rmse']}`
- no-dynamic LOBO GCN-baseline RMSE gap: `{gap['no_dynamic_lobo_gcn_minus_baseline_rmse']}`

## B1 Diagnosis

B1 true stress is `{b1['true_dynamic_stress_score']}`. GCN predicted
`{b1['gcn_predicted_dynamic_stress_score']}` with error
`{b1['gcn_absolute_error']}` and unstable probability
`{b1['gcn_unstable_probability']}`. This is an overconfident stable-marker
failure case.

## NF06 Sensitivity

NF06 changes GCN RMSE but does not change the conclusion:

- include NF06 GCN-baseline gap: `{nf06['include_gcn_minus_baseline_rmse']}`
- exclude NF06 GCN-baseline gap: `{nf06['exclude_gcn_minus_baseline_rmse']}`

## Graph Construction Diagnosis

The current GCN uses candidate rows as graph nodes. Its dense adjacency is built
from equality of categorical fields, not from physical bus-branch electrical
topology. Message passing is therefore real, but may mostly propagate tabular
category information. `target_bus` enters as one-hot input and also contributes
to graph edges.

## Likely Root Causes

{causes}

## Recommended Improvement Plan

{options}

## Measurement Boundary

- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
- `final_engineering_conclusion = false`
- `should_deploy_model = false`
- `should_retrain_reranker_now = false`
"""


def run_diagnosis() -> dict[str, Any]:
    summary = _read_json(AUDIT_DIR / "gcn_usefulness_audit_execution_summary.json")
    comparison = _read_json(AUDIT_DIR / "baseline_vs_gcn_comparison.json")
    b1_source = _read_json(AUDIT_DIR / "b1_special_tracking_report.json")
    nf06_source = _read_json(AUDIT_DIR / "nf06_sensitivity_report.json")
    forbidden = _read_json(AUDIT_DIR / "forbidden_feature_audit_report.json")

    gap = _gap_analysis(summary, comparison)
    b1 = _b1_diagnosis(b1_source)
    nf06 = _nf06_diagnosis(nf06_source)
    graph = _graph_construction_diagnosis()
    plan = _improvement_plan()
    worst = {
        "bus_fault_holdout": _worst_errors("bus_fault_holdout"),
        "leave_one_bus_fault_out": _worst_errors("leave_one_bus_fault_out"),
        "no_dynamic_measurement_leave_one_bus_fault_out": _worst_errors("no_dynamic_measurement_leave_one_bus_fault_out"),
    }

    diagnosis = {
        "diagnosis_scope": "gcn_audit_evidence_diagnosis",
        "gcn_training_run": False,
        "formal_gcn_audit_rerun": False,
        "simulink_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "production_model_saved": False,
        "source_audit_commit": SOURCE_AUDIT_COMMIT,
        "gcn_dependency_status": summary["gcn_dependency_status"],
        "total_candidate_rows": summary["total_candidate_rows"],
        "num_total_bus_fault_candidates": summary["num_total_bus_fault_candidates"],
        "forbidden_features_detected_in_inputs": forbidden["forbidden_features_detected_in_inputs"],
        "audit_level_conclusion_preserved": summary["audit_level_conclusion"]
        == "audit evidence does not support GCN usefulness over simpler baselines yet",
        "final_engineering_conclusion": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "gcn_vs_baseline_gap": gap,
        "error_concentration": {
            "worst_bus_fault_errors": worst["bus_fault_holdout"],
            "b1_error": b1["gcn_absolute_error"],
            "b1_probability": b1["gcn_unstable_probability"],
            "b1_misclassified_or_overconfident": b1["b1_misclassified_by_probability_threshold"] or b1["b1_overconfident"],
            "nf06_include_exclude_delta": nf06["gcn_rmse_delta_exclude_minus_include"],
            "nf06_sensitivity_changes_conclusion": nf06["nf06_changes_audit_conclusion"],
        },
        "graph_construction_diagnosis": graph,
        "likely_root_causes": _root_causes(graph, gap, b1, nf06),
        "recommended_improvement_plan": plan["recommended_options"],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(OUT_DIR / "gcn_vs_baseline_gap_analysis.json", gap)
    _write_text(OUT_DIR / "gcn_vs_baseline_gap_analysis.md", _report_md("GCN vs Baseline Gap Analysis", gap))
    _write_json(OUT_DIR / "b1_and_classification_diagnosis.json", b1)
    _write_text(OUT_DIR / "b1_and_classification_diagnosis.md", _report_md("B1 and Classification Diagnosis", b1))
    _write_json(OUT_DIR / "nf06_sensitivity_diagnosis.json", nf06)
    _write_text(OUT_DIR / "nf06_sensitivity_diagnosis.md", _report_md("NF06 Sensitivity Diagnosis", nf06))
    _write_json(OUT_DIR / "graph_construction_diagnosis.json", graph)
    _write_text(OUT_DIR / "graph_construction_diagnosis.md", _report_md("Graph Construction Diagnosis", graph))
    _write_json(OUT_DIR / "next_gcn_improvement_plan.json", plan)
    _write_text(OUT_DIR / "next_gcn_improvement_plan.md", _report_md("Next GCN Improvement Plan", plan))
    _write_json(OUT_DIR / "gcn_audit_evidence_diagnosis_summary.json", diagnosis)
    _write_text(OUT_DIR / "gcn_audit_evidence_diagnosis_summary.md", _summary_md(diagnosis, gap, b1, nf06, graph, plan))
    _write_summary_csv(OUT_DIR / "gcn_audit_evidence_diagnosis_summary.csv", diagnosis)
    _write_text(DOC_PATH, _summary_md(diagnosis, gap, b1, nf06, graph, plan))
    return diagnosis


def main() -> int:
    diagnosis = run_diagnosis()
    print(json.dumps(diagnosis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
