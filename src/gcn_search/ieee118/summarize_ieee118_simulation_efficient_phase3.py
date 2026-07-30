from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
)
DEFAULT_BASELINE_CONFIG = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "eval_k6"
    / "ieee118_n1_gated_search_config.json"
)
DEFAULT_OUTPUT = RESULT_ROOT / "phase3_compact_summary"


def build_phase3_high_fidelity_cost_accounting(
    replay_row: dict[str, Any] | pd.Series,
    policy_summary: dict[str, Any],
    *,
    online_probe_n2_calls: int,
) -> dict[str, Any]:
    policy_labels = int(
        policy_summary["num_policy_selection_high_fidelity_labels"]
    )
    policy_reuses_validation = bool(
        policy_summary[
            "policy_selection_labels_are_subset_of_training_validation_labels"
        ]
    )
    incremental_policy = 0 if policy_reuses_validation else policy_labels
    replay_unique = int(
        round(float(replay_row["unique_development_high_fidelity_labels"]))
    )
    full_reference = int(
        round(float(replay_row["full_label_reference_development_labels"]))
    )
    unique_development = replay_unique + incremental_policy
    adjusted_full_reference = full_reference + incremental_policy
    return {
        "training_query_high_fidelity_labels": int(
            round(float(replay_row["queried_training_labels"]))
        ),
        "training_query_fraction": float(
            replay_row["queried_training_label_fraction"]
        ),
        "training_query_label_reduction_fraction": float(
            1.0 - float(replay_row["queried_training_label_fraction"])
        ),
        "validation_model_selection_high_fidelity_labels": int(
            round(float(replay_row["validation_model_selection_labels"]))
        ),
        "calibration_high_fidelity_labels": int(
            round(float(replay_row["calibration_labels"]))
        ),
        "calibration_reuses_model_selection_validation": True,
        "policy_selection_high_fidelity_labels": policy_labels,
        "policy_selection_reuses_model_selection_validation": (
            policy_reuses_validation
        ),
        "policy_selection_incremental_unique_labels": incremental_policy,
        "unique_development_high_fidelity_labels": unique_development,
        "full_label_reference_development_high_fidelity_labels": (
            adjusted_full_reference
        ),
        "total_development_label_reduction_fraction": float(
            1.0
            - unique_development / max(adjusted_full_reference, 1)
        ),
        "test_audit_labels_not_counted_as_development_data": int(
            round(float(replay_row["test_audit_labels"]))
        ),
        "formal_search_audit_path_labels_not_counted_as_development": int(
            round(float(replay_row["formal_search_audit_path_labels"]))
        ),
        "online_probe_n2_calls_included_in_ranked_candidate_count": int(
            online_probe_n2_calls
        ),
    }


def _comparison_row(
    comparison: pd.DataFrame,
    method: str,
) -> pd.Series:
    selected = comparison.loc[comparison["method"].astype(str).eq(method)]
    if len(selected) != 1:
        raise ValueError(
            f"Expected one comparison row for {method}; found {len(selected)}."
        )
    return selected.iloc[0]


def build_phase3_relative_comparisons(
    comparison: pd.DataFrame,
) -> dict[str, dict[str, float]]:
    """Report matched head-retrieval controls and the anchor tail tradeoff."""
    main = _comparison_row(
        comparison,
        "MF_active_GCN_adaptive_probe_gate26",
    )
    phase2 = _comparison_row(
        comparison,
        "Phase2_active_GCN_adaptive_probe_gate26",
    )
    random_label = _comparison_row(
        comparison,
        "random_label_GCN_adaptive_probe_gate26",
    )
    anchor = _comparison_row(
        comparison,
        "MF_active_plus_random_anchor_mean_adaptive_probe",
    )
    exact = _comparison_row(
        comparison,
        "full_label_GCN_exact_N1_gate",
    )
    return {
        "main_vs_full_label": {
            "critical_K90_increase": float(
                main["critical_K90"] - exact["critical_K90"]
            ),
            "critical_K90_ratio": float(
                main["critical_K90"] / exact["critical_K90"]
            ),
            "total_physical_K90_ratio": float(
                main["critical_K90_total_physical"]
                / exact["critical_K90_total_physical"]
            ),
        },
        "main_vs_phase2_active": {
            "critical_K90_reduction": float(
                phase2["critical_K90"] - main["critical_K90"]
            ),
            "critical_K90_relative_reduction": float(
                1.0 - main["critical_K90"] / phase2["critical_K90"]
            ),
        },
        "main_vs_random_label": {
            "critical_K90_reduction": float(
                random_label["critical_K90"] - main["critical_K90"]
            ),
            "critical_K90_relative_reduction": float(
                1.0
                - main["critical_K90"] / random_label["critical_K90"]
            ),
        },
        "tail_anchor_tradeoff": {
            "critical_K90_increase": float(
                anchor["critical_K90"] - main["critical_K90"]
            ),
            "critical_K99_reduction": float(
                main["critical_K99"] - anchor["critical_K99"]
            ),
            "critical_K99_relative_reduction": float(
                1.0 - anchor["critical_K99"] / main["critical_K99"]
            ),
        },
    }


def extract_lazy_method_row(
    thresholds_csv: Path,
    *,
    method: str,
) -> dict[str, Any]:
    if not thresholds_csv.exists():
        raise FileNotFoundError(f"Missing lazy threshold summary: {thresholds_csv}")
    table = pd.read_csv(thresholds_csv)
    required = {
        "target",
        "target_fraction",
        "candidate_evaluations_mean",
        "candidate_evaluations_std",
        "n1_state_constructions_mean",
        "total_physical_evaluations_mean",
    }
    missing = sorted(required - set(table))
    if missing:
        raise ValueError(f"Lazy threshold summary is missing fields: {missing}")
    row: dict[str, Any] = {"method": str(method)}
    for target, prefix in (("critical", "critical"), ("relay_cascade", "relay")):
        selected = table.loc[table["target"].astype(str).eq(target)]
        for fraction, label in ((0.90, "K90"), (0.95, "K95"), (0.99, "K99")):
            match = selected.loc[
                np.isclose(
                    pd.to_numeric(selected["target_fraction"], errors="coerce"),
                    fraction,
                )
            ]
            if len(match) != 1:
                raise ValueError(
                    f"Expected one {target} {label} row in {thresholds_csv}; "
                    f"found {len(match)}."
                )
            value = match.iloc[0]
            row[f"{prefix}_{label}"] = float(
                value["candidate_evaluations_mean"]
            )
            row[f"{prefix}_{label}_std"] = float(
                value["candidate_evaluations_std"]
            )
            row[f"{prefix}_{label}_n1_state_constructions"] = float(
                value["n1_state_constructions_mean"]
            )
            row[f"{prefix}_{label}_total_physical"] = float(
                value["total_physical_evaluations_mean"]
            )
    return row


def _lazy_row(
    directory: Path,
    *,
    method: str,
    training_labels: float,
    training_fraction: float,
    low_fidelity_pretraining: bool,
    feedback_probes: int,
) -> dict[str, Any]:
    row = extract_lazy_method_row(
        directory / "ieee118_lazy_prefix_thresholds.csv",
        method=method,
    )
    row.update(
        {
            "model_class": "PaperStyleRts79Gcn",
            "training_high_fidelity_labels": float(training_labels),
            "training_high_fidelity_fraction": float(training_fraction),
            "low_fidelity_pretraining": bool(low_fidelity_pretraining),
            "adaptive_feedback": bool(feedback_probes > 0),
            "feedback_probe_n2_calls": int(feedback_probes),
            "requires_upfront_exact_n1_prescreen": False,
        }
    )
    return row


def _baseline_rows(config_path: Path) -> list[dict[str, Any]]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing full-label baseline config: {config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    wanted = {
        "N1_gate_plus_RTS79_residual_reachable_GCN_path_prob": (
            "full_label_GCN_exact_N1_gate",
            1_239_452,
            1.0,
            True,
        ),
        "line_order": ("line_order", 0, 0.0, False),
        "LODF_yP": ("LODF_yP", 0, 0.0, False),
        "random": ("random_10_seed_mean", 0, 0.0, False),
        "N1_gate_plus_line_order": (
            "line_order_exact_N1_gate",
            0,
            0.0,
            True,
        ),
        "N1_gate_plus_LODF_yP": (
            "LODF_yP_exact_N1_gate",
            0,
            0.0,
            True,
        ),
        "N1_gate_plus_random": (
            "random_exact_N1_gate_10_seed_mean",
            0,
            0.0,
            True,
        ),
    }
    rows = []
    for threshold in config["thresholds"]:
        source_method = str(threshold["method"])
        if source_method not in wanted:
            continue
        method, labels, fraction, exact_gate = wanted[source_method]
        n1_cost = float(threshold.get("n1_prescreen_evaluations", 0))
        row: dict[str, Any] = {
            "method": method,
            "model_class": (
                "PaperStyleRts79Gcn"
                if method.startswith("full_label_GCN")
                else None
            ),
            "training_high_fidelity_labels": float(labels),
            "training_high_fidelity_fraction": float(fraction),
            "low_fidelity_pretraining": False,
            "adaptive_feedback": False,
            "feedback_probe_n2_calls": 0,
            "requires_upfront_exact_n1_prescreen": bool(exact_gate),
        }
        for label in ("K90", "K95", "K99"):
            row[f"critical_{label}"] = float(threshold[label])
            row[f"critical_{label}_std"] = float(
                threshold.get(f"{label}_std", 0.0)
            )
            row[f"critical_{label}_n1_state_constructions"] = n1_cost
            row[f"critical_{label}_total_physical"] = float(
                threshold.get(
                    f"total_physical_{label}",
                    float(threshold[label]) + n1_cost,
                )
            )
        rows.append(row)
    return rows


def _final_replay_row(root_name: str, method: str) -> dict[str, Any]:
    path = (
        RESULT_ROOT
        / root_name
        / "compact"
        / "ieee118_active_label_replay_aggregate.csv"
    )
    if not path.exists():
        raise FileNotFoundError(f"Missing active replay aggregate: {path}")
    table = pd.read_csv(path)
    selected = table.loc[table["method"].astype(str).eq(method)].copy()
    if selected.empty:
        raise ValueError(f"Method {method} is absent from {path}")
    selected["queried_training_labels"] = pd.to_numeric(
        selected["queried_training_labels"],
        errors="raise",
    )
    return selected.sort_values("queried_training_labels").iloc[-1].to_dict()


def summarize(output_dir: Path, baseline_config: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _baseline_rows(baseline_config)
    lazy_specs = [
        (
            "phase3_lazy_prefix_mf_iterative_nogate_load100",
            "MF_active_GCN_no_gate",
            61_973,
            0.0500003227,
            True,
            0,
        ),
        (
            "phase3_lazy_prefix_mf_iterative_gate26_load100",
            "MF_active_GCN_static_proxy_gate26",
            61_973,
            0.0500003227,
            True,
            0,
        ),
        (
            "phase3_adaptive_probe_gate26_safety_selected",
            "MF_active_GCN_adaptive_probe_gate26",
            61_973,
            0.0500003227,
            True,
            130,
        ),
        (
            "phase3_adaptive_probe_gate26_phase2_control",
            "Phase2_active_GCN_adaptive_probe_gate26",
            61_973,
            0.0500003227,
            False,
            130,
        ),
        (
            "phase3_adaptive_probe_gate26_random_control",
            "random_label_GCN_adaptive_probe_gate26",
            61_973,
            0.0500003227,
            False,
            130,
        ),
        (
            "phase3_adaptive_probe_gate76_validation_selected",
            "MF_active_GCN_adaptive_probe_gate76_sensitivity",
            61_973,
            0.0500003227,
            True,
            380,
        ),
    ]
    for spec in lazy_specs:
        rows.append(
            _lazy_row(
                RESULT_ROOT / spec[0],
                method=spec[1],
                training_labels=spec[2],
                training_fraction=spec[3],
                low_fidelity_pretraining=spec[4],
                feedback_probes=spec[5],
            )
        )
    fusion_dir = RESULT_ROOT / "phase3_adaptive_probe_gate26_mf_random_mean_fusion"
    fusion_summary = json.loads(
        (fusion_dir / "ieee118_lazy_prefix_summary.json").read_text(
            encoding="utf-8"
        )
    )
    fusion_union = float(
        np.mean(
            [
                row["union_training_oracle_labels"]
                for row in fusion_summary["runs"]
            ]
        )
    )
    rows.append(
        _lazy_row(
            fusion_dir,
            method="MF_active_plus_random_anchor_mean_adaptive_probe",
            training_labels=fusion_union,
            training_fraction=fusion_union / 1_239_452,
            low_fidelity_pretraining=True,
            feedback_probes=130,
        )
    )

    comparison = pd.DataFrame(rows)
    full_k90 = float(
        comparison.loc[
            comparison["method"].eq("full_label_GCN_exact_N1_gate"),
            "critical_K90",
        ].iloc[0]
    )
    comparison["critical_K90_relative_to_full_label"] = (
        comparison["critical_K90"] / full_k90
    )
    relative_comparisons = build_phase3_relative_comparisons(comparison)
    comparison.to_csv(
        output_dir / "ieee118_phase3_method_comparison.csv",
        index=False,
        encoding="utf-8-sig",
    )

    replay_specs = [
        ("phase2_budget_curve", "random", "random_5pct"),
        (
            "phase2_budget_curve",
            "pmf_hybrid_prior_corrected",
            "phase2_active_5pct",
        ),
        ("phase3_pg_lure_curve", "pg_lure", "LURE_pure_5pct"),
        (
            "phase3_pg_lure_curve",
            "pg_lure_unweighted",
            "propensity_sampled_unweighted_5pct",
        ),
        (
            "phase3_pg_lure_blend25_curve",
            "pg_lure_blend",
            "LURE_blend25_5pct",
        ),
        (
            "phase3_lure_entropy_curve",
            "lure_entropy",
            "LURE_entropy_5pct",
        ),
        (
            "phase3_mf_all_candidates_perstate95_e1_w5_curve",
            "pmf_hybrid_prior_corrected",
            "multifidelity_active_5pct",
        ),
    ]
    replay_rows = []
    for root_name, method, alias in replay_specs:
        row = _final_replay_row(root_name, method)
        row["experiment"] = alias
        replay_rows.append(row)
    main_replay_row = next(
        row
        for row in replay_rows
        if row["experiment"] == "multifidelity_active_5pct"
    )
    training_ablation = pd.DataFrame(replay_rows)
    keep = [
        "experiment",
        "method",
        "queried_training_labels",
        "queried_training_label_fraction",
        "validation_average_precision_mean",
        "validation_average_precision_std",
        "test_average_precision_mean",
        "test_average_precision_std",
        "test_s1_average_precision_mean",
        "test_s1_average_precision_std",
        "search_path_prob_K90_mean",
        "search_path_prob_K95_mean",
        "search_path_prob_K99_mean",
        "search_residual_path_prob_K90_mean",
        "lure_weight_effective_sample_fraction_mean",
    ]
    training_ablation[[name for name in keep if name in training_ablation]].to_csv(
        output_dir / "ieee118_phase3_training_ablation.csv",
        index=False,
        encoding="utf-8-sig",
    )

    main = comparison.loc[
        comparison["method"].eq("MF_active_GCN_adaptive_probe_gate26")
    ].iloc[0]
    no_gate = comparison.loc[
        comparison["method"].eq("MF_active_GCN_no_gate")
    ].iloc[0]
    static_gate = comparison.loc[
        comparison["method"].eq("MF_active_GCN_static_proxy_gate26")
    ].iloc[0]
    exact = comparison.loc[
        comparison["method"].eq("full_label_GCN_exact_N1_gate")
    ].iloc[0]
    proxy_summary = json.loads(
        (
            RESULT_ROOT
            / "phase3_iterative_lodf_n1_proxy"
            / "ieee118_iterative_lodf_n1_proxy_summary.json"
        ).read_text(encoding="utf-8")
    )
    policy_summary = json.loads(
        (
            RESULT_ROOT
            / "phase3_adaptive_probe_policy_selection"
            / "ieee118_adaptive_probe_policy_summary.json"
        ).read_text(encoding="utf-8")
    )
    high_fidelity_cost_accounting = build_phase3_high_fidelity_cost_accounting(
        main_replay_row,
        policy_summary,
        online_probe_n2_calls=int(main["feedback_probe_n2_calls"]),
    )
    summary = {
        "status": "complete",
        "research_stage": (
            "Phase 3 retrospective simulation-efficient GCN and adaptive "
            "prefix-search experiment"
        ),
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "main_method": "MF_active_GCN_adaptive_probe_gate26",
        "main_result": {
            "training_high_fidelity_labels": int(
                main["training_high_fidelity_labels"]
            ),
            "training_high_fidelity_fraction": float(
                main["training_high_fidelity_fraction"]
            ),
            "unique_development_high_fidelity_labels": (
                high_fidelity_cost_accounting[
                    "unique_development_high_fidelity_labels"
                ]
            ),
            "feedback_probe_n2_calls": int(main["feedback_probe_n2_calls"]),
            "critical_K90": float(main["critical_K90"]),
            "critical_K90_std": float(main["critical_K90_std"]),
            "critical_K90_n1_state_constructions": int(
                main["critical_K90_n1_state_constructions"]
            ),
            "critical_K90_total_physical": float(
                main["critical_K90_total_physical"]
            ),
            "critical_K95": float(main["critical_K95"]),
            "critical_K99": float(main["critical_K99"]),
            "relay_K90": float(main["relay_K90"]),
        },
        "relative_results": {
            "critical_K90_over_full_label": float(
                main["critical_K90"] / exact["critical_K90"]
            ),
            "total_physical_K90_over_full_label": float(
                main["critical_K90_total_physical"]
                / exact["critical_K90_total_physical"]
            ),
            "critical_K90_reduction_vs_no_gate": float(
                1.0 - main["critical_K90"] / no_gate["critical_K90"]
            ),
            "critical_K90_reduction_vs_static_proxy_gate": float(
                1.0 - main["critical_K90"] / static_gate["critical_K90"]
            ),
            "high_fidelity_training_label_reduction_vs_full": float(
                1.0 - main["training_high_fidelity_fraction"]
            ),
            "high_fidelity_total_development_label_reduction_vs_full": (
                high_fidelity_cost_accounting[
                    "total_development_label_reduction_fraction"
                ]
            ),
        },
        "high_fidelity_cost_accounting": high_fidelity_cost_accounting,
        "matched_control_comparisons": relative_comparisons,
        "validation_selected_policy": policy_summary["selection"][0],
        "low_fidelity_proxy": proxy_summary,
        "formal_limitations": [
            "The experiment replays already generated labels; it does not reclaim their historical simulation cost.",
            "The 95% reduction applies to queried training labels only; complete validation/model-selection labels reduce the total development-data saving.",
            "Adaptive-policy recall is measured only on fully labeled validation S1 states, covering about 39.38% of all IEEE118 first-line candidates on average; it is not global recall.",
            "No exhaustive high-fidelity N-1 prescreen is required before search, but 176 cached S1 states have been constructed by K90.",
            "K95 and K99 remain materially worse than the full-label exact-N1 baseline.",
            "The selected policy has been audited on one frozen deployment seed; additional independent operating scenarios are required.",
            "No IEEE300, ACTIVSg2000, utility-grid, or N-3/N-4 deployment claim is made.",
        ],
        "negative_results": {
            "pure_propensity_correction": (
                "LURE-style pure correction reduced mean test AP and did not "
                "pass the full-label gate."
            ),
            "dual_anchor_mean_fusion": (
                "The representative anchor improved K99 but worsened K90, so "
                "it remains a tail sensitivity rather than the main method."
            ),
        },
        "outputs": {
            "method_comparison": "ieee118_phase3_method_comparison.csv",
            "training_ablation": "ieee118_phase3_training_ablation.csv",
        },
    }
    (output_dir / "ieee118_phase3_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    (output_dir / "ieee118_phase3_readme.md").write_text(
        "# IEEE118 simulation-efficient GCN Phase 3\n\n"
        "The main method retains `PaperStyleRts79Gcn`, pretrains it on a cheap "
        "DC/LODF target, fine-tunes with 5% retrospective high-fidelity labels, "
        "and applies validation-selected feedback probing before unchanged-GCN "
        "fallback. Candidate N-2 counts and S1 construction counts are reported "
        "separately. The 5% figure is a training-query fraction; complete "
        "validation/model-selection labels are included in the separate total "
        "development-data cost.\n\n"
        f"- Queried training labels: {int(main['training_high_fidelity_labels']):,}\n"
        f"- Unique development labels: "
        f"{high_fidelity_cost_accounting['unique_development_high_fidelity_labels']:,}\n"
        f"- Total development-label reduction: "
        f"{100.0 * high_fidelity_cost_accounting['total_development_label_reduction_fraction']:.2f}%\n"
        f"- Critical K90 / K95 / K99: {main['critical_K90']:.1f} / "
        f"{main['critical_K95']:.1f} / {main['critical_K99']:.1f}\n"
        f"- K90 S1 constructions / total physical operations: "
        f"{int(main['critical_K90_n1_state_constructions'])} / "
        f"{main['critical_K90_total_physical']:.1f}\n\n"
        "This is a retrospective IEEE118 experiment, not a real-grid deployment "
        "or a completed N-k scalability claim.\n",
        encoding="utf-8",
    )
    return summary


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact IEEE118 Phase-3 experiment summaries."
    )
    parser.add_argument(
        "--baseline-config",
        type=Path,
        default=DEFAULT_BASELINE_CONFIG,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    print(json.dumps(summarize(args.output_dir, args.baseline_config), indent=2))


if __name__ == "__main__":
    main()
