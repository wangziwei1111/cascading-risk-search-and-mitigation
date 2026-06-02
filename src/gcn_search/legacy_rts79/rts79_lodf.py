from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS, BR_X, F_BUS, PF, RATE_A, T_BUS
from pypower.idx_bus import BUS_I

from rts79_cascade import (
    Rts79InitialConfig,
    line_label_to_index_1based,
    run_initial_dcopf,
    run_sequential_initial_outages_dcpf,
)


def calculate_physical_vulnerability_y_p(case: dict, beta: float = 1.2) -> pd.DataFrame:
    """Calculate y_P in the paper; y_P is the LODF-based physical vulnerability index."""

    branch = case["branch"]
    bus = case["bus"]
    bus_numbers = bus[:, BUS_I].astype(int).tolist()
    bus_to_position = {bus_number: pos for pos, bus_number in enumerate(bus_numbers)}
    x_matrix = _build_nodal_reactance_matrix(case, bus_to_position)
    incidence = _build_branch_incidence_matrix(branch, bus_to_position)
    branch_x = branch[:, BR_X].astype(float)
    branch_flow = np.where(branch[:, BR_STATUS].astype(int) == 1, branch[:, PF].astype(float), 0.0)
    rate_a = branch[:, RATE_A].astype(float)
    status = branch[:, BR_STATUS].astype(int)
    x_pair = incidence.T @ x_matrix @ incidence

    records: list[dict] = []
    online = status == 1
    for k_idx in range(branch.shape[0]):
        line_label = f"L{k_idx + 1:02d}"
        if not online[k_idx]:
            records.append(
                {
                    "candidate_line": line_label,
                    "from_bus": int(branch[k_idx, F_BUS]),
                    "to_bus": int(branch[k_idx, T_BUS]),
                    "status": int(status[k_idx]),
                    "y_P": np.nan,
                    "max_alpha_line": "",
                    "max_alpha": np.nan,
                    "denominator": np.nan,
                    "is_singular_or_islanding": False,
                    "beta": beta,
                }
            )
            continue

        denominator = 1.0 - x_pair[k_idx, k_idx] / branch_x[k_idx]
        if abs(denominator) < 1e-8:
            records.append(
                {
                    "candidate_line": line_label,
                    "from_bus": int(branch[k_idx, F_BUS]),
                    "to_bus": int(branch[k_idx, T_BUS]),
                    "status": int(status[k_idx]),
                    "y_P": float(beta),
                    "max_alpha_line": "singular_or_islanding",
                    "max_alpha": float(beta),
                    "denominator": float(denominator),
                    "is_singular_or_islanding": True,
                    "beta": beta,
                }
            )
            continue

        alpha_hat = np.full(branch.shape[0], np.nan, dtype=float)
        for m_idx in range(branch.shape[0]):
            if not online[m_idx] or m_idx == k_idx or rate_a[m_idx] <= 0:
                continue
            d_mk = (x_pair[m_idx, k_idx] / branch_x[m_idx]) / denominator
            predicted_flow = branch_flow[m_idx] + d_mk * branch_flow[k_idx]
            alpha_hat[m_idx] = abs(predicted_flow) / rate_a[m_idx]

        if np.all(np.isnan(alpha_hat)):
            max_alpha = 0.0
            max_idx = -1
        else:
            max_idx = int(np.nanargmax(alpha_hat))
            max_alpha = float(alpha_hat[max_idx])
        records.append(
            {
                "candidate_line": line_label,
                "from_bus": int(branch[k_idx, F_BUS]),
                "to_bus": int(branch[k_idx, T_BUS]),
                "status": int(status[k_idx]),
                "y_P": max_alpha,
                "max_alpha_line": f"L{max_idx + 1:02d}" if max_idx >= 0 else "",
                "max_alpha": max_alpha,
                "denominator": float(denominator),
                "is_singular_or_islanding": False,
                "beta": beta,
            }
        )

    return pd.DataFrame(records).sort_values("y_P", ascending=False, na_position="last").reset_index(drop=True)


def _build_branch_incidence_matrix(branch: np.ndarray, bus_to_position: dict[int, int]) -> np.ndarray:
    incidence = np.zeros((len(bus_to_position), branch.shape[0]), dtype=float)
    for branch_idx, row in enumerate(branch):
        from_position = bus_to_position[int(row[F_BUS])]
        to_position = bus_to_position[int(row[T_BUS])]
        incidence[from_position, branch_idx] = 1.0
        incidence[to_position, branch_idx] = -1.0
    return incidence


def _build_nodal_reactance_matrix(case: dict, bus_to_position: dict[int, int]) -> np.ndarray:
    branch = case["branch"]
    bus_count = len(bus_to_position)
    b_bus = np.zeros((bus_count, bus_count), dtype=float)
    for row in branch:
        if int(row[BR_STATUS]) != 1:
            continue
        from_position = bus_to_position[int(row[F_BUS])]
        to_position = bus_to_position[int(row[T_BUS])]
        susceptance = 1.0 / float(row[BR_X])
        b_bus[from_position, from_position] += susceptance
        b_bus[to_position, to_position] += susceptance
        b_bus[from_position, to_position] -= susceptance
        b_bus[to_position, from_position] -= susceptance

    x_matrix = np.zeros_like(b_bus)
    active_positions = [idx for idx in range(bus_count) if np.any(np.abs(b_bus[idx, :]) > 1e-12)]
    if len(active_positions) <= 1:
        return x_matrix
    reference = active_positions[0]
    reduced_positions = [idx for idx in active_positions if idx != reference]
    reduced_b = b_bus[np.ix_(reduced_positions, reduced_positions)]
    reduced_x = np.linalg.pinv(reduced_b)
    x_matrix[np.ix_(reduced_positions, reduced_positions)] = reduced_x
    return x_matrix


def _load_case_after_outages(outage_sequence: list[str] | None, beta: float, security_limit: float) -> dict:
    if not outage_sequence:
        return run_initial_dcopf().case
    state = run_sequential_initial_outages_dcpf(
        outage_sequence,
        config=Rts79InitialConfig(),
        relay_threshold_beta=beta,
        security_limit=security_limit,
    )
    return state.case


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="计算论文公式 (2)-(6) 的 RTS-79 y_P 物理脆弱性指标。")
    parser.add_argument("--outages", nargs="*", default=[], help="当前已经断开的有序支路，例如 L10。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--output-csv", default=str(Path("outputs") / "lodf" / "rts79_y_p.csv"), help="输出 CSV 文件。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    case = _load_case_after_outages([label.upper() for label in args.outages], args.beta, args.security_limit)
    table = calculate_physical_vulnerability_y_p(case, beta=args.beta)
    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output_csv, index=False, encoding="utf-8-sig")
    print(f"[y_P] 已保存: {output_csv}")
    print(table.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
