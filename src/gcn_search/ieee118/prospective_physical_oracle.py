from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from simulation_efficient_prefix_search import (
    OrderedPrefixStateCache,
    lazy_best_first_ordered_n2,
)


FirstStateBuilder = Callable[[str], Any]
FirstStateDescriber = Callable[[Any, str], Mapping[str, Any]]
SecondStateBuilder = Callable[[Any, str], Any]
SecondStateDescriber = Callable[[Any, str, str], Mapping[str, Any]]
SecondScoreProvider = Callable[[str], Mapping[str, float]]
CheckpointCallback = Callable[["OnDemandCascadeOracle"], None]


@dataclass(frozen=True)
class ProspectiveSearchResult:
    query_rows: tuple[dict[str, Any], ...]
    first_step_rows: tuple[dict[str, Any], ...]
    probe_paths: tuple[str, ...]
    promoted_second_lines: tuple[str, ...]
    num_n1_state_constructions: int
    num_unique_n2_queries: int
    num_new_n2_simulations: int
    budget_exhausted: bool


class OnDemandCascadeOracle:
    """Expose cascade outcomes only after an ordered path is queried."""

    def __init__(
        self,
        *,
        line_labels: Iterable[str],
        first_state_builder: FirstStateBuilder,
        first_state_describer: FirstStateDescriber,
        second_state_builder: SecondStateBuilder,
        second_state_describer: SecondStateDescriber,
        resume_rows: Iterable[Mapping[str, Any]] = (),
        resume_first_step_rows: Iterable[Mapping[str, Any]] = (),
        checkpoint_callback: CheckpointCallback | None = None,
    ) -> None:
        self.line_labels = tuple(str(label) for label in line_labels)
        if not self.line_labels or len(set(self.line_labels)) != len(
            self.line_labels
        ):
            raise ValueError("line_labels must be non-empty and unique.")
        self._line_set = set(self.line_labels)
        self._first_state_builder = first_state_builder
        self._first_state_describer = first_state_describer
        self._second_state_builder = second_state_builder
        self._second_state_describer = second_state_describer
        self._checkpoint_callback = checkpoint_callback
        self._first_states: dict[str, Any] = {}
        self._first_descriptions: dict[str, dict[str, Any]] = {}
        self.first_step_rows: list[dict[str, Any]] = []
        self._first_row_by_line: dict[str, dict[str, Any]] = {}
        for original in resume_first_step_rows:
            row = dict(original)
            first = str(row.get("first_line", ""))
            if first not in self._line_set:
                raise ValueError(f"Resumed first-step row has unknown line: {first}")
            if first in self._first_row_by_line:
                raise ValueError(f"Duplicate resumed first-step row: {first}")
            row["resumed"] = True
            self.first_step_rows.append(row)
            self._first_row_by_line[first] = row
        self.query_rows: list[dict[str, Any]] = []
        self._query_by_path: dict[str, dict[str, Any]] = {}
        self._resume_order: list[str] = []
        self._policy_consumed: set[str] = set()
        self._resume_cursor = 0
        self._new_n2_simulations = 0

        ordered_resume = sorted(
            (dict(row) for row in resume_rows),
            key=lambda row: int(row.get("query_rank", 0)),
        )
        for row in ordered_resume:
            first = str(row.get("first_line", ""))
            second = str(row.get("second_line", ""))
            path = str(row.get("path", f"{first}->{second}"))
            self._validate_path(first, second, path)
            if path in self._query_by_path:
                raise ValueError(f"Duplicate resumed ordered path: {path}")
            row["query_rank"] = len(self.query_rows) + 1
            row["resumed"] = True
            self.query_rows.append(row)
            self._query_by_path[path] = row
            self._resume_order.append(path)

    @property
    def num_n1_state_constructions(self) -> int:
        return len(self._first_states)

    @property
    def num_new_n2_simulations(self) -> int:
        return self._new_n2_simulations

    @property
    def num_unique_n2_queries(self) -> int:
        return len(self.query_rows)

    @property
    def num_policy_queries(self) -> int:
        return len(self._policy_consumed)

    def has_query(self, path: str) -> bool:
        return str(path) in self._query_by_path

    def has_consumed_query(self, path: str) -> bool:
        return str(path) in self._policy_consumed

    def _validate_path(self, first_line: str, second_line: str, path: str) -> None:
        if first_line not in self._line_set or second_line not in self._line_set:
            raise ValueError(f"Ordered path contains an unknown line: {path}")
        if first_line == second_line or path != f"{first_line}->{second_line}":
            raise ValueError(f"Invalid canonical ordered path: {path}")

    def get_first_state(self, first_line: str) -> tuple[Any, dict[str, Any]]:
        first = str(first_line)
        if first not in self._line_set:
            raise ValueError(f"Unknown first-line label: {first}")
        if first not in self._first_states:
            state = self._first_state_builder(first)
            description = dict(self._first_state_describer(state, first))
            valid_second_lines = tuple(
                str(label)
                for label in description.pop(
                    "valid_second_lines",
                    tuple(label for label in self.line_labels if label != first),
                )
            )
            invalid = sorted(set(valid_second_lines) - self._line_set)
            if invalid or first in valid_second_lines:
                raise ValueError(
                    f"Invalid second-line set for {first}: {invalid[:5]}"
                )
            description["valid_second_lines"] = valid_second_lines
            self._first_states[first] = state
            self._first_descriptions[first] = description
            first_row = {
                "first_line": first,
                "first_step_converged": bool(description.get("converged", True)),
                "first_step_critical": bool(description.get("critical", False)),
                "first_step_total_load_shed_mw": float(
                    description.get("total_load_shed_mw", 0.0)
                ),
                "num_valid_second_lines": len(valid_second_lines),
            }
            for name, value in description.items():
                if name in {
                    "converged",
                    "critical",
                    "total_load_shed_mw",
                    "valid_second_lines",
                }:
                    continue
                first_row[f"first_step_{name}"] = value
            existing = self._first_row_by_line.get(first)
            if existing is None:
                self.first_step_rows.append(first_row)
                self._first_row_by_line[first] = first_row
            else:
                for name in (
                    "first_step_converged",
                    "first_step_critical",
                    "num_valid_second_lines",
                ):
                    if str(existing.get(name)) != str(first_row.get(name)):
                        raise ValueError(
                            f"Resumed first-step state changed for {first}: {name}"
                        )
        return self._first_states[first], self._first_descriptions[first]

    def query(
        self,
        first_line: str,
        second_line: str,
        *,
        stage: str,
    ) -> dict[str, Any] | None:
        first = str(first_line)
        second = str(second_line)
        path = f"{first}->{second}"
        self._validate_path(first, second, path)
        if path in self._query_by_path:
            if path not in self._policy_consumed:
                if self._resume_cursor >= len(self._resume_order):
                    raise ValueError(
                        f"Resume path {path} has no remaining query-rank entry."
                    )
                expected = self._resume_order[self._resume_cursor]
                if path != expected:
                    raise ValueError(
                        "Prospective policy diverged from the resume log: "
                        f"expected {expected}, selected {path}."
                    )
                self._resume_cursor += 1
                self._policy_consumed.add(path)
            return self._query_by_path[path]

        first_state, first_description = self.get_first_state(first)
        if not bool(first_description.get("converged", True)) or bool(
            first_description.get("critical", False)
        ):
            return None
        if second not in set(first_description["valid_second_lines"]):
            return None

        if self._resume_cursor < len(self._resume_order):
            raise ValueError(
                "Prospective policy selected a new path before replaying all "
                f"resume rows; expected {self._resume_order[self._resume_cursor]}."
            )

        second_state = self._second_state_builder(first_state, second)
        outcome = dict(self._second_state_describer(second_state, first, second))
        row = {
            "query_rank": len(self.query_rows) + 1,
            "path": path,
            "first_line": first,
            "second_line": second,
            "search_stage": str(stage),
            **outcome,
            "resumed": False,
        }
        self.query_rows.append(row)
        self._query_by_path[path] = row
        self._policy_consumed.add(path)
        self._new_n2_simulations += 1
        if self._checkpoint_callback is not None:
            self._checkpoint_callback(self)
        return row


def run_frozen_adaptive_ordered_n2(
    *,
    first_line_scores: Mapping[str, float],
    line_labels: Iterable[str],
    gate_second_lines: Iterable[str],
    second_score_provider: SecondScoreProvider,
    oracle: OnDemandCascadeOracle,
    probes_per_second_line: int,
    promotion_min_positives: int,
    max_n2_queries: int,
) -> ProspectiveSearchResult:
    """Run the frozen Phase-3 policy against a query-only physical oracle."""

    labels = tuple(str(label) for label in line_labels)
    if labels != oracle.line_labels:
        raise ValueError("Search labels must match the physical oracle labels.")
    first = {str(label): float(score) for label, score in first_line_scores.items()}
    if set(first) != set(labels):
        raise ValueError("Prospective first-line scores must cover every line.")
    if any(not np_is_finite_nonnegative(value) for value in first.values()):
        raise ValueError("Prospective first-line scores must be finite and non-negative.")
    probes = int(probes_per_second_line)
    minimum = int(promotion_min_positives)
    budget = int(max_n2_queries)
    if probes <= 0 or minimum <= 0 or minimum > probes:
        raise ValueError("Probe and promotion counts are inconsistent.")
    if budget < oracle.num_unique_n2_queries:
        raise ValueError("Resume rows already exceed max_n2_queries.")

    first_order = tuple(sorted(first, key=lambda label: (-first[label], label)))
    gate = tuple(dict.fromkeys(str(label) for label in gate_second_lines))
    if set(gate) - set(labels):
        raise ValueError("Physics gate contains unknown line labels.")
    gate_order = {label: position for position, label in enumerate(gate)}
    probe_paths: list[str] = []
    positive_counts: dict[str, int] = {label: 0 for label in gate}
    probe_counts: dict[str, int] = {label: 0 for label in gate}

    for second_line in gate:
        for first_line in first_order:
            if oracle.num_policy_queries >= budget:
                break
            if first_line == second_line or probe_counts[second_line] >= probes:
                continue
            row = oracle.query(first_line, second_line, stage="probe")
            if row is None:
                continue
            path = str(row["path"])
            if path not in probe_paths:
                probe_paths.append(path)
            probe_counts[second_line] += 1
            positive_counts[second_line] += int(bool(row.get("critical", False)))
        if oracle.num_policy_queries >= budget:
            break

    promoted = tuple(
        sorted(
            (
                label
                for label in gate
                if probe_counts[label] == probes
                and positive_counts[label] >= minimum
            ),
            key=lambda label: (
                -((1.0 + positive_counts[label]) / (2.0 + probe_counts[label])),
                gate_order[label],
                label,
            ),
        )
    )
    for second_line in promoted:
        for first_line in first_order:
            if oracle.num_policy_queries >= budget:
                break
            if first_line == second_line:
                continue
            oracle.query(first_line, second_line, stage="promoted_line_expansion")
        if oracle.num_policy_queries >= budget:
            break

    num_available = len(labels) * (len(labels) - 1)
    requested = min(
        num_available,
        max(budget + oracle.num_unique_n2_queries + len(labels), 1),
    )
    score_cache = OrderedPrefixStateCache()
    while oracle.num_policy_queries < budget:
        fallback = lazy_best_first_ordered_n2(
            first_line_scores=first,
            line_labels=labels,
            second_score_provider=second_score_provider,
            max_candidates=requested,
            scenario_id="prospective",
            cache=score_cache,
        ).ranking
        for candidate in fallback.itertuples(index=False):
            if oracle.num_policy_queries >= budget:
                break
            if oracle.has_consumed_query(candidate.path):
                continue
            oracle.query(
                candidate.first_line,
                candidate.second_line,
                stage="unchanged_gcn_fallback",
            )
        if oracle.num_policy_queries >= budget or requested >= num_available:
            break
        requested = min(num_available, max(requested + len(labels), requested * 2))

    return ProspectiveSearchResult(
        query_rows=tuple(oracle.query_rows),
        first_step_rows=tuple(oracle.first_step_rows),
        probe_paths=tuple(probe_paths),
        promoted_second_lines=promoted,
        num_n1_state_constructions=oracle.num_n1_state_constructions,
        num_unique_n2_queries=oracle.num_unique_n2_queries,
        num_new_n2_simulations=oracle.num_new_n2_simulations,
        budget_exhausted=oracle.num_policy_queries >= budget,
    )


def np_is_finite_nonnegative(value: float) -> bool:
    return value >= 0.0 and value != float("inf") and value == value
