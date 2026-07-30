from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DcLodfMatrix:
    lodf: np.ndarray
    singular_candidate: np.ndarray


@dataclass(frozen=True)
class IterativeRelayProxyResult:
    num_relay_trips: int
    max_event_loading_ratio: float
    num_singular_outages: int
    final_branch_status: np.ndarray

    @property
    def has_relay_cascade(self) -> bool:
        return self.num_relay_trips > 0


def build_dc_lodf_matrix(
    branch_from_bus: np.ndarray,
    branch_to_bus: np.ndarray,
    branch_x: np.ndarray,
    branch_status: np.ndarray,
    *,
    branch_tap_ratio: np.ndarray | None = None,
    denominator_tolerance: float = 1e-8,
) -> DcLodfMatrix:
    """Build the DC line-outage distribution matrix for one topology."""
    from_bus = np.asarray(branch_from_bus, dtype=np.int64)
    to_bus = np.asarray(branch_to_bus, dtype=np.int64)
    reactance = np.asarray(branch_x, dtype=np.float64)
    status = np.asarray(branch_status, dtype=bool)
    num_lines = len(from_bus)
    tap = (
        np.ones(num_lines, dtype=np.float64)
        if branch_tap_ratio is None
        else np.asarray(branch_tap_ratio, dtype=np.float64).copy()
    )
    if not (
        to_bus.shape
        == reactance.shape
        == status.shape
        == tap.shape
        == (num_lines,)
    ):
        raise ValueError(
            "Branch endpoint, reactance, tap, and status arrays must align."
        )
    if np.any(status & (~np.isfinite(reactance) | (np.abs(reactance) < 1e-12))):
        raise ValueError("Every in-service branch must have finite non-zero reactance.")
    tap[np.isclose(tap, 0.0)] = 1.0
    if np.any(status & (~np.isfinite(tap) | (tap <= 0.0))):
        raise ValueError(
            "Every in-service transformer tap must be finite and positive."
        )
    branch_susceptance = 1.0 / (reactance * tap)

    bus_numbers = np.unique(np.concatenate((from_bus, to_bus)))
    bus_position = {
        int(bus_number): position
        for position, bus_number in enumerate(bus_numbers.tolist())
    }
    incidence = np.zeros((len(bus_numbers), num_lines), dtype=np.float64)
    for line_idx in range(num_lines):
        incidence[bus_position[int(from_bus[line_idx])], line_idx] = 1.0
        incidence[bus_position[int(to_bus[line_idx])], line_idx] = -1.0

    active = np.where(status)[0]
    b_bus = np.zeros((len(bus_numbers), len(bus_numbers)), dtype=np.float64)
    if len(active):
        active_incidence = incidence[:, active]
        b_bus = (
            active_incidence
            * branch_susceptance[active][None, :]
        ) @ active_incidence.T
    x_bus = np.linalg.pinv(b_bus, rcond=1e-10, hermitian=True)
    x_pair = incidence.T @ x_bus @ incidence

    lodf = np.full((num_lines, num_lines), np.nan, dtype=np.float64)
    singular = np.zeros(num_lines, dtype=bool)
    for candidate_idx in active:
        denominator = (
            1.0
            - x_pair[candidate_idx, candidate_idx]
            * branch_susceptance[candidate_idx]
        )
        if not np.isfinite(denominator) or abs(denominator) < denominator_tolerance:
            singular[candidate_idx] = True
            continue
        monitored = active[active != candidate_idx]
        lodf[monitored, candidate_idx] = (
            x_pair[monitored, candidate_idx]
            * branch_susceptance[monitored]
            / denominator
        )
        lodf[candidate_idx, candidate_idx] = -1.0
    return DcLodfMatrix(lodf=lodf, singular_candidate=singular)


def dc_lodf_max_loading_proxy(
    abs_flow: np.ndarray,
    flow_sign: np.ndarray,
    rate_a: np.ndarray,
    current_branch_status: np.ndarray,
    matrix: DcLodfMatrix,
    *,
    singular_score: float = 1.2,
) -> np.ndarray:
    """Estimate post-candidate-outage maximum loading without an N-2 solve."""
    flow_magnitude = np.asarray(abs_flow, dtype=np.float64)
    sign = np.asarray(flow_sign, dtype=np.float64)
    limit = np.asarray(rate_a, dtype=np.float64)
    status = np.asarray(current_branch_status, dtype=bool)
    num_lines = len(flow_magnitude)
    if not (
        sign.shape == limit.shape == status.shape == (num_lines,)
        and matrix.lodf.shape == (num_lines, num_lines)
        and matrix.singular_candidate.shape == (num_lines,)
    ):
        raise ValueError("Flow, limit, status, and LODF dimensions must align.")
    if np.any(status & (~np.isfinite(limit) | (limit <= 0.0))):
        raise ValueError("Every monitored in-service branch must have a positive limit.")
    if np.any(~np.isfinite(flow_magnitude)) or np.any(flow_magnitude < 0.0):
        raise ValueError("abs_flow must be finite and non-negative.")

    signed_flow = flow_magnitude * np.where(sign < 0.0, -1.0, 1.0)
    predicted_flow = np.abs(
        signed_flow[:, None]
        + matrix.lodf * signed_flow[None, :]
    )
    loading = predicted_flow / limit[:, None]
    loading[~status, :] = np.nan
    diagonal = np.arange(num_lines)
    loading[diagonal, diagonal] = np.nan

    score = np.full(num_lines, np.nan, dtype=np.float64)
    active_candidates = np.where(status)[0]
    for candidate_idx in active_candidates:
        if matrix.singular_candidate[candidate_idx]:
            current_loading = flow_magnitude[status] / limit[status]
            score[candidate_idx] = max(
                float(singular_score),
                float(np.max(current_loading)) if len(current_loading) else 0.0,
            )
            continue
        candidate_loading = loading[:, candidate_idx]
        finite = np.isfinite(candidate_loading)
        score[candidate_idx] = (
            float(np.max(candidate_loading[finite]))
            if finite.any()
            else 0.0
        )
    return score


def iterative_dc_lodf_relay_proxy(
    signed_flow: np.ndarray,
    rate_a: np.ndarray,
    initial_branch_status: np.ndarray,
    initial_outage_index: int,
    *,
    branch_from_bus: np.ndarray,
    branch_to_bus: np.ndarray,
    branch_x: np.ndarray,
    branch_tap_ratio: np.ndarray | None = None,
    beta: float = 1.2,
    max_rounds: int = 20,
    topology_cache: dict[bytes, DcLodfMatrix] | None = None,
) -> IterativeRelayProxyResult:
    """Run a cheap iterative LODF relay screen without DCPF or redispatch."""
    flow = np.asarray(signed_flow, dtype=np.float64).copy()
    limit = np.asarray(rate_a, dtype=np.float64)
    status = np.asarray(initial_branch_status, dtype=bool).copy()
    num_lines = len(flow)
    if not (
        limit.shape == status.shape == (num_lines,)
        and len(branch_from_bus) == len(branch_to_bus) == len(branch_x) == num_lines
        and (
            branch_tap_ratio is None
            or len(branch_tap_ratio) == num_lines
        )
    ):
        raise ValueError("Iterative relay proxy branch arrays must align.")
    if not 0 <= int(initial_outage_index) < num_lines:
        raise ValueError("initial_outage_index is out of range.")
    if not status[int(initial_outage_index)]:
        raise ValueError("The initial candidate outage is already offline.")
    if beta <= 0.0 or max_rounds <= 0:
        raise ValueError("beta and max_rounds must be positive.")

    cache = topology_cache if topology_cache is not None else {}
    max_loading = 0.0
    relay_trips = 0
    singular_outages = 0

    def matrix_for(current_status: np.ndarray) -> DcLodfMatrix:
        key = np.packbits(current_status).tobytes()
        if key not in cache:
            cache[key] = build_dc_lodf_matrix(
                branch_from_bus,
                branch_to_bus,
                branch_x,
                current_status,
                branch_tap_ratio=branch_tap_ratio,
            )
        return cache[key]

    def open_one(line_idx: int) -> bool:
        nonlocal flow, status, singular_outages
        matrix = matrix_for(status)
        if matrix.singular_candidate[line_idx]:
            singular_outages += 1
            flow[line_idx] = 0.0
            status[line_idx] = False
            return False
        monitored = np.where(status)[0]
        monitored = monitored[monitored != line_idx]
        flow[monitored] = (
            flow[monitored]
            + matrix.lodf[monitored, line_idx] * flow[line_idx]
        )
        flow[line_idx] = 0.0
        status[line_idx] = False
        return True

    if not open_one(int(initial_outage_index)):
        max_loading = float(beta)
    for _ in range(max_rounds):
        online = np.where(status)[0]
        if not len(online):
            break
        loading = np.abs(flow[online]) / limit[online]
        max_loading = max(max_loading, float(np.max(loading)))
        overloaded = online[loading > beta]
        if not len(overloaded):
            break
        relay_trips += int(len(overloaded))
        for line_idx in sorted(overloaded.tolist()):
            if status[line_idx]:
                open_one(int(line_idx))
    return IterativeRelayProxyResult(
        num_relay_trips=relay_trips,
        max_event_loading_ratio=max_loading,
        num_singular_outages=singular_outages,
        final_branch_status=status,
    )


def binary_low_fidelity_target(
    proxy_score: np.ndarray,
    proxy_mask: np.ndarray,
    split: np.ndarray,
    *,
    mode: str,
    overload_threshold: float = 1.2,
    upper_quantile: float = 0.95,
) -> tuple[np.ndarray, float]:
    """Freeze a low-fidelity binary target using only training proxy scores."""
    score = np.asarray(proxy_score, dtype=np.float64)
    mask = np.asarray(proxy_mask, dtype=bool)
    split_name = np.asarray(split, dtype=str)
    if score.shape != mask.shape or score.shape[0] != len(split_name):
        raise ValueError("Proxy score, mask, and split arrays must align.")
    training_score = score[mask & (split_name == "train")[:, None]]
    training_score = training_score[np.isfinite(training_score)]
    if len(training_score) == 0:
        raise ValueError("No finite training proxy scores are available.")
    if mode == "overload":
        threshold = float(overload_threshold)
    elif mode == "top_quantile":
        if not 0.0 < upper_quantile < 1.0:
            raise ValueError("upper_quantile must be in (0, 1).")
        threshold = float(np.quantile(training_score, upper_quantile))
    elif mode == "per_state_top_quantile":
        if not 0.0 < upper_quantile < 1.0:
            raise ValueError("upper_quantile must be in (0, 1).")
        target = np.zeros(score.shape, dtype=np.int64)
        row_thresholds = []
        for row_idx in range(score.shape[0]):
            row_active = mask[row_idx] & np.isfinite(score[row_idx])
            if not row_active.any():
                continue
            row_threshold = float(
                np.quantile(score[row_idx, row_active], upper_quantile)
            )
            row_thresholds.append(row_threshold)
            target[row_idx, row_active] = (
                score[row_idx, row_active] >= row_threshold
            ).astype(np.int64)
        return target, float(np.median(row_thresholds))
    else:
        raise ValueError(f"Unsupported low-fidelity target mode: {mode!r}")
    target = np.zeros(score.shape, dtype=np.int64)
    target[mask & np.isfinite(score)] = (
        score[mask & np.isfinite(score)] >= threshold
    ).astype(np.int64)
    return target, threshold
