from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(IEEE118_DIR))

from run_ieee118_active_label_replay import DEFAULT_DATASET
from simulation_efficient_prefix_search import probe_second_line_feedback


DEFAULT_PROXY_SCORES = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_iterative_lodf_n1_proxy"
    / "ieee118_iterative_lodf_n1_proxy_validation_scores.csv"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_adaptive_probe_policy_selection"
)


@dataclass(frozen=True)
class ValidationProbeScenario:
    seed: int
    first_line_scores: Mapping[str, float]
    gate_second_lines: tuple[str, ...]
    path_truth: Mapping[str, bool]
    source_s1_state_count: int | None = None
    system_first_line_count: int | None = None


def _second_line(path: str) -> str:
    parts = str(path).split("->")
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid ordered path label: {path}")
    return parts[1]


def evaluate_validation_probe_grid(
    scenarios: Iterable[ValidationProbeScenario],
    *,
    configurations: Iterable[tuple[int, int]],
    gate_size: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay feedback-only probe policies on validation scenarios."""

    scenario_list = list(scenarios)
    config_list = sorted(
        set((int(probes), int(minimum)) for probes, minimum in configurations)
    )
    if not scenario_list:
        raise ValueError("At least one validation probe scenario is required.")
    if not config_list:
        raise ValueError("At least one probe configuration is required.")
    rows: list[dict[str, Any]] = []
    for scenario in scenario_list:
        truth = {str(path): bool(value) for path, value in scenario.path_truth.items()}
        gate = tuple(scenario.gate_second_lines[: int(gate_size)])
        if len(gate) != int(gate_size):
            raise ValueError(
                f"Seed {scenario.seed} has {len(gate)} gate lines; "
                f"expected {gate_size}."
            )
        gate_set = set(gate)
        complete_first_line_count = len(scenario.first_line_scores)
        source_s1_state_count = int(
            scenario.source_s1_state_count
            if scenario.source_s1_state_count is not None
            else complete_first_line_count
        )
        system_first_line_count = int(
            scenario.system_first_line_count
            if scenario.system_first_line_count is not None
            else complete_first_line_count
        )
        if source_s1_state_count < complete_first_line_count:
            raise ValueError(
                "source_s1_state_count cannot be smaller than the complete subset."
            )
        if system_first_line_count < complete_first_line_count:
            raise ValueError(
                "system_first_line_count cannot be smaller than the complete subset."
            )
        total_critical = int(sum(truth.values()))
        gate_critical = int(
            sum(
                value
                for path, value in truth.items()
                if _second_line(path) in gate_set
            )
        )
        line_counts: dict[str, int] = {}
        line_positives: dict[str, int] = {}
        for path, value in truth.items():
            second = _second_line(path)
            line_counts[second] = line_counts.get(second, 0) + 1
            line_positives[second] = line_positives.get(second, 0) + int(value)
        high_impact = {
            line
            for line in gate
            if line_counts.get(line, 0) > 0
            and line_positives.get(line, 0) / line_counts[line] >= 0.5
        }
        for probes, minimum in config_list:
            feedback = probe_second_line_feedback(
                first_line_scores=scenario.first_line_scores,
                gate_second_lines=gate,
                query_outcome=lambda path, truth=truth: truth[path],
                probes_per_second_line=probes,
                promotion_min_positives=minimum,
            )
            promoted = set(feedback.promoted_second_lines)
            expansion_paths = {
                path for path in truth if _second_line(path) in promoted
            }
            queried_paths = set(feedback.probe_paths) | expansion_paths
            captured = int(sum(truth[path] for path in queried_paths))
            promoted_high_impact = len(promoted & high_impact)
            rows.append(
                {
                    "seed": int(scenario.seed),
                    "gate_size": int(gate_size),
                    "probes_per_second_line": probes,
                    "promotion_min_positives": minimum,
                    "num_first_line_states": len(scenario.first_line_scores),
                    "num_complete_subset_path_labels": len(truth),
                    "num_source_s1_states": source_s1_state_count,
                    "num_system_first_lines": system_first_line_count,
                    "complete_first_line_fraction_of_source_s1": (
                        complete_first_line_count / source_s1_state_count
                        if source_s1_state_count
                        else 0.0
                    ),
                    "complete_first_line_fraction_of_system": (
                        complete_first_line_count / system_first_line_count
                        if system_first_line_count
                        else 0.0
                    ),
                    "num_probe_paths": len(feedback.probe_paths),
                    "num_probe_positives": int(
                        sum(feedback.positive_counts.values())
                    ),
                    "num_promoted_second_lines": len(promoted),
                    "promoted_second_lines": ";".join(
                        feedback.promoted_second_lines
                    ),
                    "num_high_impact_gate_lines": len(high_impact),
                    "num_promoted_high_impact_gate_lines": (
                        promoted_high_impact
                    ),
                    "high_impact_line_recall": (
                        promoted_high_impact / len(high_impact)
                        if high_impact
                        else 1.0
                    ),
                    "num_total_critical_paths": total_critical,
                    "num_gate_critical_paths": gate_critical,
                    "num_captured_critical_paths": captured,
                    "gate_critical_recall": (
                        captured / gate_critical if gate_critical else 1.0
                    ),
                    "complete_subset_critical_recall": (
                        captured / total_critical if total_critical else 1.0
                    ),
                    "estimated_n2_queries_before_fallback": len(queried_paths),
                }
            )
    per_seed = pd.DataFrame(rows)
    summary = (
        per_seed.groupby(
            [
                "gate_size",
                "probes_per_second_line",
                "promotion_min_positives",
            ],
            sort=True,
        )
        .agg(
            num_validation_scenarios=("seed", "nunique"),
            num_complete_subset_validation_path_labels=(
                "num_complete_subset_path_labels",
                "sum",
            ),
            gate_critical_recall_mean=("gate_critical_recall", "mean"),
            gate_critical_recall_std=("gate_critical_recall", "std"),
            gate_critical_recall_min=("gate_critical_recall", "min"),
            complete_subset_critical_recall_mean=(
                "complete_subset_critical_recall",
                "mean",
            ),
            complete_first_line_fraction_of_source_s1_mean=(
                "complete_first_line_fraction_of_source_s1",
                "mean",
            ),
            complete_first_line_fraction_of_system_mean=(
                "complete_first_line_fraction_of_system",
                "mean",
            ),
            high_impact_line_recall_mean=("high_impact_line_recall", "mean"),
            high_impact_line_recall_min=("high_impact_line_recall", "min"),
            num_promoted_second_lines_mean=(
                "num_promoted_second_lines",
                "mean",
            ),
            estimated_n2_queries_mean=(
                "estimated_n2_queries_before_fallback",
                "mean",
            ),
            estimated_n2_queries_max=(
                "estimated_n2_queries_before_fallback",
                "max",
            ),
        )
        .reset_index()
    )
    summary["gate_critical_recall_std"] = summary[
        "gate_critical_recall_std"
    ].fillna(0.0)
    return per_seed, summary


def select_probe_configuration(
    summary: pd.DataFrame,
    *,
    min_mean_gate_recall: float,
    min_worst_gate_recall: float,
) -> dict[str, Any]:
    required = {
        "probes_per_second_line",
        "promotion_min_positives",
        "gate_critical_recall_mean",
        "gate_critical_recall_min",
        "estimated_n2_queries_mean",
    }
    missing = sorted(required - set(summary))
    if missing:
        raise ValueError(f"Probe summary is missing fields: {missing}")
    feasible = summary.loc[
        summary["gate_critical_recall_mean"].ge(min_mean_gate_recall)
        & summary["gate_critical_recall_min"].ge(min_worst_gate_recall)
    ].copy()
    selection_feasible = not feasible.empty
    candidates = feasible if selection_feasible else summary.copy()
    if candidates.empty:
        raise ValueError("Probe summary contains no configurations.")
    if selection_feasible:
        candidates = candidates.sort_values(
            [
                "gate_critical_recall_min",
                "gate_critical_recall_mean",
                "estimated_n2_queries_mean",
                "probes_per_second_line",
                "promotion_min_positives",
            ],
            ascending=[False, False, True, True, True],
            kind="stable",
        )
    else:
        candidates = candidates.sort_values(
            [
                "gate_critical_recall_min",
                "gate_critical_recall_mean",
                "estimated_n2_queries_mean",
                "probes_per_second_line",
                "promotion_min_positives",
            ],
            ascending=[False, False, True, True, True],
            kind="stable",
        )
    selected = candidates.iloc[0].to_dict()
    selected["selection_feasible"] = bool(selection_feasible)
    selected["minimum_mean_gate_recall"] = float(min_mean_gate_recall)
    selected["minimum_worst_gate_recall"] = float(min_worst_gate_recall)
    return selected


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Select IEEE118 feedback-probe hyperparameters using validation "
            "scenarios only."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--validation-proxy-scores-csv",
        type=Path,
        default=DEFAULT_PROXY_SCORES,
    )
    parser.add_argument("--gate-sizes", type=int, nargs="+", default=[26, 76])
    parser.add_argument("--probe-counts", type=int, nargs="+", default=[1, 3, 5])
    parser.add_argument("--min-mean-gate-recall", type=float, default=0.90)
    parser.add_argument("--min-worst-gate-recall", type=float, default=0.80)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def _build_validation_scenarios(
    dataset: Mapping[str, np.ndarray],
    proxy_scores: pd.DataFrame,
    gate_size: int,
) -> list[ValidationProbeScenario]:
    line_labels = np.asarray(dataset["line_labels"], dtype=str)
    split = np.asarray(dataset["split"], dtype=str)
    sample_type = np.asarray(dataset["sample_type"], dtype=str)
    seeds = np.asarray(dataset["seed"], dtype=np.int64)
    source_mask = np.asarray(dataset["source_loss_mask"], dtype=bool)
    source_y = np.asarray(dataset["source_y_gcn"], dtype=np.int64)
    active_first = np.asarray(dataset["active_first_line"], dtype=str)
    scenarios: list[ValidationProbeScenario] = []
    for seed in sorted(proxy_scores["seed"].astype(int).unique()):
        source_state_indices = np.where(
            (seeds == int(seed))
            & (split == "validation")
            & (sample_type == "S1")
        )[0]
        state_indices = source_state_indices[
            source_mask[source_state_indices].sum(axis=1)
            == len(line_labels) - 1
        ]
        if not len(state_indices):
            raise ValueError(
                f"Validation seed {seed} has no fully labeled S1 states."
            )
        first_lines = active_first[state_indices]
        if len(set(first_lines)) != len(first_lines):
            raise ValueError(
                f"Validation seed {seed} contains duplicate first-line states."
            )
        seed_proxy = proxy_scores.loc[
            proxy_scores["seed"].astype(int).eq(int(seed))
        ].copy()
        seed_proxy = seed_proxy.sort_values(
            ["selected_proxy_score", "line_label"],
            ascending=[False, True],
            kind="stable",
        )
        score_by_line = dict(
            zip(
                seed_proxy["line_label"].astype(str),
                pd.to_numeric(
                    seed_proxy["selected_proxy_score"],
                    errors="raise",
                ).astype(float),
            )
        )
        if set(line_labels) - set(score_by_line):
            raise ValueError(f"Proxy scores do not cover all lines for seed {seed}.")
        path_truth: dict[str, bool] = {}
        for row_index, first_line in zip(state_indices, first_lines):
            for line_index, second_line in enumerate(line_labels):
                if first_line == second_line:
                    continue
                path_truth[f"{first_line}->{second_line}"] = bool(
                    source_y[row_index, line_index]
                )
        scenarios.append(
            ValidationProbeScenario(
                seed=int(seed),
                first_line_scores={
                    line: score_by_line[line] for line in first_lines
                },
                gate_second_lines=tuple(
                    seed_proxy["line_label"].astype(str).head(gate_size)
                ),
                path_truth=path_truth,
                source_s1_state_count=int(len(source_state_indices)),
                system_first_line_count=int(len(line_labels)),
            )
        )
    return scenarios


def select_policy(args: argparse.Namespace) -> dict[str, Any]:
    for path, label in (
        (args.dataset_npz, "IEEE118 training dataset"),
        (args.validation_proxy_scores_csv, "validation proxy scores"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing local {label}: {path}")
    if not 0.0 <= args.min_mean_gate_recall <= 1.0:
        raise ValueError("--min-mean-gate-recall must be in [0, 1].")
    if not 0.0 <= args.min_worst_gate_recall <= 1.0:
        raise ValueError("--min-worst-gate-recall must be in [0, 1].")
    data = np.load(args.dataset_npz, allow_pickle=True)
    proxy = pd.read_csv(args.validation_proxy_scores_csv)
    required_proxy = {
        "seed",
        "split",
        "line_label",
        "selected_proxy_score",
    }
    missing_proxy = sorted(required_proxy - set(proxy))
    if missing_proxy:
        raise ValueError(f"Validation proxy scores are missing: {missing_proxy}")
    if not proxy["split"].astype(str).eq("validation").all():
        raise ValueError("Policy selection accepts validation proxy rows only.")
    configurations = [
        (probes, minimum)
        for probes in sorted(set(int(value) for value in args.probe_counts))
        for minimum in range(1, probes + 1)
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_seed_parts = []
    summary_parts = []
    selections = []
    for gate_size in sorted(set(int(value) for value in args.gate_sizes)):
        scenarios = _build_validation_scenarios(data, proxy, gate_size)
        per_seed, summary = evaluate_validation_probe_grid(
            scenarios,
            configurations=configurations,
            gate_size=gate_size,
        )
        selected = select_probe_configuration(
            summary,
            min_mean_gate_recall=float(args.min_mean_gate_recall),
            min_worst_gate_recall=float(args.min_worst_gate_recall),
        )
        selections.append(selected)
        per_seed_parts.append(per_seed)
        summary_parts.append(summary)
    per_seed_all = pd.concat(per_seed_parts, ignore_index=True)
    summary_all = pd.concat(summary_parts, ignore_index=True)
    validation_label_counts = summary_all.groupby("gate_size")[
        "num_complete_subset_validation_path_labels"
    ].first()
    if validation_label_counts.nunique() != 1:
        raise ValueError(
            "Validation path-label count changed across gate-size policies."
        )
    num_policy_selection_labels = int(validation_label_counts.iloc[0])
    per_seed_all.to_csv(
        args.output_dir / "ieee118_adaptive_probe_policy_by_seed.csv",
        index=False,
        encoding="utf-8-sig",
    )
    summary_all.to_csv(
        args.output_dir / "ieee118_adaptive_probe_policy_grid.csv",
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(selections).to_csv(
        args.output_dir / "ieee118_adaptive_probe_policy_selected.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result = {
        "status": "complete",
        "research_stage": "Phase 3 validation-only adaptive probe selection",
        "num_validation_seeds": int(proxy["seed"].nunique()),
        "gate_sizes": sorted(set(int(value) for value in args.gate_sizes)),
        "probe_counts": sorted(set(int(value) for value in args.probe_counts)),
        "selection": selections,
        "selection_uses_test_seed_outcomes": False,
        "selection_uses_validation_n2_outcomes": True,
        "num_policy_selection_high_fidelity_labels": num_policy_selection_labels,
        "policy_selection_labels_are_subset_of_training_validation_labels": True,
        "policy_input_contains_high_fidelity_labels": False,
        "validation_outcomes_visible_only_after_probe_query": True,
        "validation_recall_scope": (
            "Recall is computed only over fully labeled validation S1 states. "
            "Coverage fractions are reported against source validation S1 "
            "states and all IEEE118 first-line candidates; it is not global "
            "full-system recall."
        ),
        "cost_definition": (
            "Unique N-2 probes plus all unprobed paths under promoted second "
            "lines, before unchanged-GCN fallback."
        ),
    }
    (args.output_dir / "ieee118_adaptive_probe_policy_summary.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_adaptive_probe_policy_readme.md").write_text(
        "# IEEE118 adaptive probe policy selection\n\n"
        "Probe count and promotion threshold are selected on eight validation "
        "operating scenarios. The frozen `20260708` test outcomes are not read "
        "during selection. Low-fidelity proxy scores are label-free policy "
        "inputs; high-fidelity validation labels are returned only after each "
        "selected probe in the retrospective oracle replay. Recall statistics "
        "cover only fully labeled validation S1 states; the output reports the "
        "subset coverage and must not be read as global IEEE118 recall.\n\n"
        "Validation policy selection reads "
        f"{num_policy_selection_labels:,} high-fidelity path labels from the "
        "fully labeled validation S1 subset. These labels are a subset of "
        "the same validation labels already used for model selection and "
        "calibration, so they are reported separately but not double-counted "
        "in unique development-label cost.\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    print(json.dumps(select_policy(parse_args()), indent=2))


if __name__ == "__main__":
    main()
