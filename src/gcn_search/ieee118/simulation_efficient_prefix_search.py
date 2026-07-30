from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

import numpy as np
import pandas as pd


Prefix = tuple[str, ...]
StateBuilder = Callable[[], Any]
SecondScoreProvider = Callable[[str], Mapping[str, float]]
OutcomeOracle = Callable[[str], bool]
FirstStateBuilder = Callable[[str], Any]


class OrderedPrefixStateCache:
    """Cache physical states without merging differently ordered outages."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, Prefix], Any] = {}
        self.hits = 0
        self.misses = 0

    def get_or_build(
        self,
        scenario_id: str,
        ordered_prefix: Iterable[str],
        builder: StateBuilder,
    ) -> Any:
        key = (str(scenario_id), tuple(str(label) for label in ordered_prefix))
        if key in self._values:
            self.hits += 1
            return self._values[key]
        value = builder()
        self._values[key] = value
        self.misses += 1
        return value

    def __len__(self) -> int:
        return len(self._values)


@dataclass(frozen=True)
class LazyPrefixSearchResult:
    ranking: pd.DataFrame
    num_available_paths: int
    num_activated_first_lines: int
    num_n2_verifications: int
    cache_hits: int
    cache_misses: int

    @property
    def total_physical_evaluations(self) -> int:
        return self.num_activated_first_lines + self.num_n2_verifications


@dataclass(frozen=True)
class AdaptiveProbeSearchResult:
    ranking: pd.DataFrame
    num_available_paths: int
    num_activated_first_lines: int
    num_n2_verifications: int
    cache_hits: int
    cache_misses: int
    probe_paths: tuple[str, ...]
    promoted_second_lines: tuple[str, ...]

    @property
    def total_physical_evaluations(self) -> int:
        return self.num_activated_first_lines + self.num_n2_verifications


@dataclass(frozen=True)
class SecondLineProbeResult:
    probe_paths: tuple[str, ...]
    promoted_second_lines: tuple[str, ...]
    positive_counts: Mapping[str, int]
    probe_counts: Mapping[str, int]


def _validate_probability(value: float, label: str) -> float:
    probability = float(value)
    if not np.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError(f"{label} must be a finite probability in [0, 1].")
    return probability


def _validate_nonnegative_score(value: float, label: str) -> float:
    score = float(value)
    if not np.isfinite(score) or score < 0.0:
        raise ValueError(f"{label} must be a finite non-negative score.")
    return score


def probe_second_line_feedback(
    *,
    first_line_scores: Mapping[str, float],
    gate_second_lines: Iterable[str],
    query_outcome: OutcomeOracle,
    probes_per_second_line: int,
    promotion_min_positives: int,
    max_queries: int | None = None,
) -> SecondLineProbeResult:
    """Select high-impact second lines using only sequential probe outcomes."""

    first = {
        str(label): _validate_nonnegative_score(
            score,
            f"first score for {label}",
        )
        for label, score in first_line_scores.items()
    }
    if not first:
        raise ValueError("first_line_scores must not be empty.")
    gate = tuple(dict.fromkeys(str(label) for label in gate_second_lines))
    probes = int(probes_per_second_line)
    minimum = int(promotion_min_positives)
    if probes < 0:
        raise ValueError("probes_per_second_line must be non-negative.")
    if minimum < 1 or minimum > max(probes, 1):
        raise ValueError(
            "promotion_min_positives must be between 1 and the number of probes."
        )
    query_limit = (
        probes * len(gate) if max_queries is None else int(max_queries)
    )
    if query_limit < 0:
        raise ValueError("max_queries must be non-negative.")
    first_order = tuple(
        sorted(first, key=lambda label: (-first[label], label))
    )
    gate_order = {label: index for index, label in enumerate(gate)}
    paths: list[str] = []
    positives = {label: 0 for label in gate}
    counts = {label: 0 for label in gate}
    queried: set[str] = set()
    for _ in range(probes):
        for second_line in gate:
            if len(paths) >= query_limit:
                break
            eligible = [
                first_line
                for first_line in first_order
                if first_line != second_line
                and f"{first_line}->{second_line}" not in queried
            ]
            if not eligible:
                continue
            path = f"{eligible[0]}->{second_line}"
            outcome = bool(query_outcome(path))
            queried.add(path)
            paths.append(path)
            counts[second_line] += 1
            positives[second_line] += int(outcome)
        if len(paths) >= query_limit:
            break
    promoted = tuple(
        sorted(
            (
                label
                for label in gate
                if counts[label] == probes and positives[label] >= minimum
            ),
            key=lambda label: (
                -((1.0 + positives[label]) / (2.0 + counts[label])),
                gate_order[label],
                label,
            ),
        )
    )
    return SecondLineProbeResult(
        probe_paths=tuple(paths),
        promoted_second_lines=promoted,
        positive_counts=positives,
        probe_counts=counts,
    )


def lazy_best_first_ordered_n2(
    *,
    first_line_scores: Mapping[str, float],
    line_labels: Iterable[str],
    second_score_provider: SecondScoreProvider,
    max_candidates: int,
    scenario_id: str = "scenario",
    cache: OrderedPrefixStateCache | None = None,
) -> LazyPrefixSearchResult:
    """Rank ordered N-2 paths while constructing only competitive S1 states.

    For a path score ``score(first) * p(second | S1)``, ``score(first)`` is
    an admissible upper bound because the conditional probability is at most one.
    A first-outage prefix is therefore expanded only when its bound reaches the
    top of the best-first queue. Expanding it is the point where a deployment
    implementation constructs S1 and evaluates all candidate second lines.
    """

    labels = tuple(str(label) for label in line_labels)
    if len(labels) != len(set(labels)):
        raise ValueError("line_labels must be unique.")
    first = {
        str(label): _validate_nonnegative_score(
            score,
            f"first score for {label}",
        )
        for label, score in first_line_scores.items()
    }
    missing = sorted(set(first) - set(labels))
    if missing:
        raise ValueError(f"First-line scores contain unknown labels: {missing[:10]}")
    num_available = sum(len(labels) - int(label in labels) for label in first)
    if not 0 <= int(max_candidates) <= num_available:
        raise ValueError(
            f"max_candidates must be between 0 and {num_available}, "
            f"received {max_candidates}."
        )

    state_cache = cache if cache is not None else OrderedPrefixStateCache()
    initial_misses = state_cache.misses
    initial_hits = state_cache.hits
    # Heap fields: negative score, node type, lexical key, first, second.
    # Prefixes sort before exact path candidates on a tie, preserving the bound.
    queue: list[tuple[float, int, str, str, str]] = []
    conditional_by_path: dict[str, float] = {}
    for first_line, score in first.items():
        heapq.heappush(
            queue,
            (-score, 0, first_line, first_line, ""),
        )

    rows: list[dict[str, Any]] = []
    activated: set[str] = set()
    while queue and len(rows) < int(max_candidates):
        negative_score, node_type, lexical_key, first_line, second_line = (
            heapq.heappop(queue)
        )
        if node_type == 0:
            second_scores = state_cache.get_or_build(
                scenario_id,
                (first_line,),
                lambda first_line=first_line: dict(
                    second_score_provider(first_line)
                ),
            )
            activated.add(first_line)
            unknown = sorted(set(second_scores) - set(labels))
            if unknown:
                raise ValueError(
                    f"Second scores for {first_line} contain unknown labels: "
                    f"{unknown[:10]}"
                )
            required = set(labels) - {first_line}
            absent = sorted(required - set(second_scores))
            if absent:
                raise ValueError(
                    f"Second scores for {first_line} are missing labels: "
                    f"{absent[:10]}"
                )
            for candidate in required:
                conditional = _validate_probability(
                    second_scores[candidate],
                    f"second score for {first_line}->{candidate}",
                )
                path = f"{first_line}->{candidate}"
                exact_score = first[first_line] * conditional
                conditional_by_path[path] = conditional
                heapq.heappush(
                    queue,
                    (-exact_score, 1, path, first_line, candidate),
                )
            continue

        rank = len(rows) + 1
        path_score = -negative_score
        conditional = conditional_by_path[lexical_key]
        n1_calls = state_cache.misses - initial_misses
        rows.append(
            {
                "rank": rank,
                "path": lexical_key,
                "first_line": first_line,
                "second_line": second_line,
                "first_prefix_score": first[first_line],
                "p_shed_first": first[first_line],
                "p_shed_second": conditional,
                "path_product_score": path_score,
                "n1_state_constructions_so_far": n1_calls,
                "n2_verifications_so_far": rank,
                "total_physical_evaluations_so_far": n1_calls + rank,
            }
        )

    ranking = pd.DataFrame(rows)
    return LazyPrefixSearchResult(
        ranking=ranking,
        num_available_paths=num_available,
        num_activated_first_lines=len(activated),
        num_n2_verifications=len(rows),
        cache_hits=state_cache.hits - initial_hits,
        cache_misses=state_cache.misses - initial_misses,
    )


def adaptive_probe_then_promote_ordered_n2(
    *,
    first_line_scores: Mapping[str, float],
    line_labels: Iterable[str],
    fallback_ranking: pd.DataFrame,
    gate_second_lines: Iterable[str],
    outcome_oracle: OutcomeOracle,
    state_builder: FirstStateBuilder,
    probes_per_second_line: int,
    promotion_min_positives: int,
    max_candidates: int | None = None,
    scenario_id: str = "scenario",
    cache: OrderedPrefixStateCache | None = None,
) -> AdaptiveProbeSearchResult:
    """Probe cheap-risk second lines, then expand only feedback-confirmed lines.

    The policy receives outcomes exclusively through ``outcome_oracle`` after a
    path has been selected. This makes retrospective full-truth replay match a
    prospective simulator callback: unqueried labels cannot affect promotion.
    The supplied fallback order may come from the unchanged RTS-79 GCN.
    """

    labels = tuple(str(label) for label in line_labels)
    if len(labels) != len(set(labels)):
        raise ValueError("line_labels must be unique.")
    first = {
        str(label): _validate_nonnegative_score(
            score,
            f"first score for {label}",
        )
        for label, score in first_line_scores.items()
    }
    if not first:
        raise ValueError("first_line_scores must not be empty.")
    unknown_first = sorted(set(first) - set(labels))
    if unknown_first:
        raise ValueError(
            f"First-line scores contain unknown labels: {unknown_first[:10]}"
        )
    gate = tuple(dict.fromkeys(str(label) for label in gate_second_lines))
    unknown_gate = sorted(set(gate) - set(labels))
    if unknown_gate:
        raise ValueError(
            f"Gate contains unknown second-line labels: {unknown_gate[:10]}"
        )
    probes = int(probes_per_second_line)
    minimum = int(promotion_min_positives)
    if probes < 0:
        raise ValueError("probes_per_second_line must be non-negative.")
    if minimum < 1 or minimum > max(probes, 1):
        raise ValueError(
            "promotion_min_positives must be between 1 and the number of probes."
        )

    required_columns = {"path", "first_line", "second_line"}
    missing_columns = sorted(required_columns - set(fallback_ranking))
    if missing_columns:
        raise ValueError(
            f"fallback_ranking is missing fields: {missing_columns}"
        )
    fallback = fallback_ranking[list(required_columns)].copy()
    fallback["path"] = fallback["path"].astype(str)
    fallback["first_line"] = fallback["first_line"].astype(str)
    fallback["second_line"] = fallback["second_line"].astype(str)
    if fallback["path"].duplicated().any():
        raise ValueError("fallback_ranking paths must be unique.")
    canonical = (
        fallback["first_line"] + "->" + fallback["second_line"]
    )
    if not canonical.equals(fallback["path"]):
        raise ValueError("fallback_ranking path labels are not canonical.")
    if (fallback["first_line"] == fallback["second_line"]).any():
        raise ValueError("fallback_ranking contains repeated-line paths.")
    expected_paths = {
        f"{first_line}->{second_line}"
        for first_line in first
        for second_line in labels
        if first_line != second_line
    }
    actual_paths = set(fallback["path"])
    if actual_paths != expected_paths:
        missing_paths = sorted(expected_paths - actual_paths)
        extra_paths = sorted(actual_paths - expected_paths)
        raise ValueError(
            "fallback_ranking must contain every valid ordered path exactly "
            f"once; missing={missing_paths[:5]}, extra={extra_paths[:5]}"
        )

    num_available = len(fallback)
    limit = num_available if max_candidates is None else int(max_candidates)
    if not 0 <= limit <= num_available:
        raise ValueError(
            f"max_candidates must be between 0 and {num_available}, received {limit}."
        )
    fallback_rank = {
        path: rank
        for rank, path in enumerate(fallback["path"], start=1)
    }
    path_parts = {
        row.path: (row.first_line, row.second_line)
        for row in fallback.itertuples(index=False)
    }
    first_order = tuple(
        sorted(first, key=lambda label: (-first[label], label))
    )
    gate_order = {label: index for index, label in enumerate(gate)}
    state_cache = cache if cache is not None else OrderedPrefixStateCache()
    initial_hits = state_cache.hits
    initial_misses = state_cache.misses
    queried: set[str] = set()
    rows: list[dict[str, Any]] = []

    def query(path: str, stage: str) -> bool:
        first_line, second_line = path_parts[path]
        state_cache.get_or_build(
            scenario_id,
            (first_line,),
            lambda first_line=first_line: state_builder(first_line),
        )
        outcome = bool(outcome_oracle(path))
        queried.add(path)
        rank = len(rows) + 1
        rows.append(
            {
                "rank": rank,
                "path": path,
                "first_line": first_line,
                "second_line": second_line,
                "search_stage": stage,
                "first_prefix_score": first[first_line],
                "fallback_rank": fallback_rank[path],
                "proxy_gate_second_line": second_line in gate_order,
                "queried_target_positive": outcome,
                "n1_state_constructions_so_far": (
                    state_cache.misses - initial_misses
                ),
                "n2_verifications_so_far": rank,
                "total_physical_evaluations_so_far": (
                    state_cache.misses - initial_misses + rank
                ),
            }
        )
        return outcome

    feedback = probe_second_line_feedback(
        first_line_scores=first,
        gate_second_lines=gate,
        query_outcome=lambda path: query(path, "probe"),
        probes_per_second_line=probes,
        promotion_min_positives=minimum,
        max_queries=limit,
    )
    probe_paths = list(feedback.probe_paths)
    promoted = feedback.promoted_second_lines
    for second_line in promoted:
        for first_line in first_order:
            if len(rows) >= limit:
                break
            if first_line == second_line:
                continue
            path = f"{first_line}->{second_line}"
            if path in queried:
                continue
            query(path, "promoted_line_expansion")
        if len(rows) >= limit:
            break

    if len(rows) < limit:
        for path in fallback["path"]:
            if len(rows) >= limit:
                break
            if path in queried:
                continue
            query(path, "fallback")

    return AdaptiveProbeSearchResult(
        ranking=pd.DataFrame(rows),
        num_available_paths=num_available,
        num_activated_first_lines=state_cache.misses - initial_misses,
        num_n2_verifications=len(rows),
        cache_hits=state_cache.hits - initial_hits,
        cache_misses=state_cache.misses - initial_misses,
        probe_paths=tuple(probe_paths),
        promoted_second_lines=promoted,
    )


def evaluate_lazy_ranking(
    ranking: pd.DataFrame,
    truth: pd.DataFrame,
    budgets: Iterable[int],
    *,
    method: str,
) -> pd.DataFrame:
    required_ranking = {
        "path",
        "n1_state_constructions_so_far",
        "n2_verifications_so_far",
        "total_physical_evaluations_so_far",
    }
    required_truth = {
        "path",
        "critical",
        "relay_cascade",
        "total_load_shed_mw",
    }
    missing_ranking = sorted(required_ranking - set(ranking))
    missing_truth = sorted(required_truth - set(truth))
    if missing_ranking or missing_truth:
        raise ValueError(
            "Lazy ranking evaluation is missing fields: "
            f"ranking={missing_ranking}, truth={missing_truth}"
        )
    joined = ranking.merge(
        truth[list(required_truth)],
        on="path",
        how="left",
        validate="one_to_one",
    )
    if joined[list(required_truth - {"path"})].isna().any().any():
        raise ValueError("Lazy ranking contains paths absent from the truth table.")

    critical = joined["critical"].astype(bool).to_numpy()
    relay = joined["relay_cascade"].astype(bool).to_numpy()
    shed = pd.to_numeric(
        joined["total_load_shed_mw"],
        errors="coerce",
    ).fillna(0.0).to_numpy()
    relay_shed = shed * relay
    c_critical = np.cumsum(critical)
    c_relay = np.cumsum(relay)
    c_shed = np.cumsum(shed)
    c_relay_shed = np.cumsum(relay_shed)
    total_critical = int(truth["critical"].astype(bool).sum())
    total_relay = int(truth["relay_cascade"].astype(bool).sum())
    total_shed = float(
        pd.to_numeric(truth["total_load_shed_mw"], errors="coerce")
        .fillna(0.0)
        .sum()
    )
    total_relay_shed = float(
        pd.to_numeric(
            truth.loc[truth["relay_cascade"].astype(bool), "total_load_shed_mw"],
            errors="coerce",
        )
        .fillna(0.0)
        .sum()
    )
    rows: list[dict[str, Any]] = []
    for raw_budget in sorted(set(int(value) for value in budgets)):
        k = min(raw_budget, len(joined))
        if k <= 0:
            continue
        trace = joined.iloc[k - 1]
        critical_hits = int(c_critical[k - 1])
        relay_hits = int(c_relay[k - 1])
        rows.append(
            {
                "method": str(method),
                "candidate_evaluations": k,
                "n2_physical_verifications": int(
                    trace["n2_verifications_so_far"]
                ),
                "n1_state_constructions": int(
                    trace["n1_state_constructions_so_far"]
                ),
                "total_physical_evaluations": int(
                    trace["total_physical_evaluations_so_far"]
                ),
                "critical_paths_found": critical_hits,
                "recall_critical": critical_hits / max(total_critical, 1),
                "precision_at_k": critical_hits / k,
                "relay_cascade_paths_found": relay_hits,
                "recall_relay_cascade": relay_hits / max(total_relay, 1),
                "captured_load_shed_mw": float(c_shed[k - 1]),
                "captured_load_shed_ratio": float(c_shed[k - 1])
                / max(total_shed, np.finfo(float).eps),
                "captured_relay_load_shed_mw": float(c_relay_shed[k - 1]),
                "captured_relay_load_shed_ratio": float(c_relay_shed[k - 1])
                / max(total_relay_shed, np.finfo(float).eps),
            }
        )
    return pd.DataFrame(rows)
