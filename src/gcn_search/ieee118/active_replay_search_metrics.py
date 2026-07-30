from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analyze_ieee118_n1_residual_n2 import (
    annotate_n1_residual,
    evaluate_ranking,
    load_first_step_summary,
    load_valid_truth,
)
from convert_ieee118_step2_to_rts79_gcn_format import (
    PAPER_FEATURE_NAMES,
    normalize_x,
)
from evaluate_ieee118_n1_gated_search import order_n1_gated


@dataclass(frozen=True)
class ActiveReplaySearchContext:
    x_eval: np.ndarray
    truth: pd.DataFrame
    first_step: pd.DataFrame
    first_lines: np.ndarray
    line_labels: np.ndarray
    test_seed: int


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {label}: {path}. Formal active-replay search evaluation "
            "will not regenerate large local data."
        )


def _load_eval_x(dataset: Any, normalizer_json: Path | None) -> np.ndarray:
    if normalizer_json is None:
        return dataset["x_gcn"].astype(np.float32)
    _require_file(normalizer_json, "search feature normalizer JSON")
    if "physics_raw_features" not in dataset:
        raise ValueError(
            "Search evaluation dataset must contain physics_raw_features when "
            "--search-feature-normalizer-json is used."
        )
    normalizer = json.loads(normalizer_json.read_text(encoding="utf-8"))
    missing = sorted(set(PAPER_FEATURE_NAMES) - set(normalizer))
    if missing:
        raise ValueError(f"Search feature normalizer is missing fields: {missing}")
    return normalize_x(
        dataset["physics_raw_features"].astype(np.float32),
        normalizer,
        PAPER_FEATURE_NAMES,
    ).astype(np.float32)


def load_active_replay_search_context(
    *,
    eval_dataset_npz: Path,
    fulltruth_csv: Path,
    first_step_summary_csv: Path,
    feature_normalizer_json: Path | None,
    expected_line_labels: np.ndarray,
    expected_branch_from_bus: np.ndarray,
    expected_branch_to_bus: np.ndarray,
    test_seed: int,
) -> ActiveReplaySearchContext:
    _require_file(eval_dataset_npz, "176-state IEEE118 search evaluation dataset")
    _require_file(fulltruth_csv, "early-stop IEEE118 full-truth CSV")
    _require_file(first_step_summary_csv, "IEEE118 first-step summary CSV")
    dataset = np.load(eval_dataset_npz, allow_pickle=True)
    required = {
        "x_gcn",
        "first_line",
        "seed",
        "line_labels",
        "branch_from_bus",
        "branch_to_bus",
    }
    missing = sorted(required - set(dataset.files))
    if missing:
        raise ValueError(f"Search evaluation dataset is missing arrays: {missing}")
    line_labels = dataset["line_labels"].astype(str)
    if not np.array_equal(line_labels, np.asarray(expected_line_labels).astype(str)):
        raise ValueError("Search evaluation and active-replay line labels do not match.")
    if not np.array_equal(
        dataset["branch_from_bus"].astype(np.int64),
        np.asarray(expected_branch_from_bus).astype(np.int64),
    ) or not np.array_equal(
        dataset["branch_to_bus"].astype(np.int64),
        np.asarray(expected_branch_to_bus).astype(np.int64),
    ):
        raise ValueError("Search evaluation and active-replay branch graphs do not match.")

    selected = dataset["seed"].astype(np.int64) == int(test_seed)
    if not selected.any():
        raise ValueError(f"Search evaluation dataset contains no states for seed {test_seed}.")
    first_lines = dataset["first_line"].astype(str)[selected]
    if len(first_lines) != len(set(first_lines.tolist())):
        raise ValueError("Search evaluation first_line values must be unique within a seed.")
    x_eval = _load_eval_x(dataset, feature_normalizer_json)[selected]

    truth = load_valid_truth(fulltruth_csv)
    first_step = load_first_step_summary(first_step_summary_csv)
    if "seed" in truth:
        truth = truth.loc[pd.to_numeric(truth["seed"], errors="coerce").eq(test_seed)].copy()
    if "seed" in first_step:
        first_step = first_step.loc[
            pd.to_numeric(first_step["seed"], errors="coerce").eq(test_seed)
        ].copy()
    if truth.empty or first_step.empty:
        raise ValueError(f"Formal search truth contains no rows for seed {test_seed}.")
    annotated = annotate_n1_residual(truth, first_step)
    missing_first = sorted(set(annotated["first_line"].astype(str)) - set(first_lines))
    if missing_first:
        raise ValueError(
            "Search evaluation states do not cover valid full-truth first lines: "
            f"{missing_first[:10]}"
        )
    missing_second = sorted(
        set(annotated["second_line"].astype(str)) - set(line_labels)
    )
    if missing_second:
        raise ValueError(
            "Search evaluation line labels do not cover full-truth second lines: "
            f"{missing_second[:10]}"
        )
    return ActiveReplaySearchContext(
        x_eval=x_eval,
        truth=annotated.reset_index(drop=True),
        first_step=first_step.reset_index(drop=True),
        first_lines=first_lines,
        line_labels=line_labels,
        test_seed=int(test_seed),
    )


def make_active_replay_path_scores(
    context: ActiveReplaySearchContext,
    *,
    s0_probability: np.ndarray,
    s1_probability: np.ndarray,
) -> pd.DataFrame:
    s0_probability = np.asarray(s0_probability, dtype=float)
    s1_probability = np.asarray(s1_probability, dtype=float)
    expected_s0 = (len(context.line_labels),)
    expected_s1 = (len(context.first_lines), len(context.line_labels))
    if s0_probability.shape != expected_s0:
        raise ValueError(
            f"S0 probability shape {s0_probability.shape} does not match {expected_s0}."
        )
    if s1_probability.shape != expected_s1:
        raise ValueError(
            f"S1 probability shape {s1_probability.shape} does not match {expected_s1}."
        )
    line_index = {label: idx for idx, label in enumerate(context.line_labels)}
    state_index = {label: idx for idx, label in enumerate(context.first_lines)}
    score = context.truth.copy()
    first_indices = score["first_line"].astype(str).map(line_index).to_numpy(dtype=np.int64)
    second_indices = score["second_line"].astype(str).map(line_index).to_numpy(dtype=np.int64)
    state_indices = score["first_line"].astype(str).map(state_index).to_numpy(dtype=np.int64)
    score["p_shed_first"] = s0_probability[first_indices]
    score["p_shed_second"] = s1_probability[state_indices, second_indices]
    score["path_product_score"] = score["p_shed_first"] * score["p_shed_second"]
    return score


def active_replay_search_thresholds(
    context: ActiveReplaySearchContext,
    *,
    s0_probability: np.ndarray,
    s1_probability: np.ndarray,
) -> dict[str, Any]:
    score = make_active_replay_path_scores(
        context,
        s0_probability=s0_probability,
        s1_probability=s1_probability,
    )
    result: dict[str, Any] = {
        "search_num_valid_paths": int(len(score)),
        "search_num_critical_paths": int(score["critical"].sum()),
    }
    for score_column, prefix in (
        ("path_product_score", "search_path_prob"),
        ("p_shed_second", "search_second_only"),
    ):
        ranked = order_n1_gated(score, score_column)
        _, thresholds = evaluate_ranking(
            f"active_replay_{prefix}",
            ranked,
            universe="full",
        )
        for label in ("K90", "K95", "K99", "K100"):
            result[f"{prefix}_{label}"] = thresholds[label]
        residual_mask = (
            score["residual_ordered_n2"].astype(bool)
            if "residual_ordered_n2" in score
            else ~score["n1_second"].astype(bool)
        )
        residual = (
            score.loc[residual_mask]
            .sort_values([score_column, "path"], ascending=[False, True])
            .reset_index(drop=True)
        )
        _, residual_thresholds = evaluate_ranking(
            f"active_replay_residual_{prefix}",
            residual,
            universe="residual",
        )
        for label in ("K90", "K95", "K99", "K100"):
            result[f"search_residual_{prefix.removeprefix('search_')}_{label}"] = (
                residual_thresholds[label]
            )
    return result
