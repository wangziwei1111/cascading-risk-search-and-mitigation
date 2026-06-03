from __future__ import annotations

import csv
from pathlib import Path

import numpy as np


METRICS = ("negative_return", "num_line_outages", "load_shed_MW", "pf_failed")


def load_gcn_topk(ranking_csv: Path, top_k: int) -> tuple[list[int], list[dict]]:
    rows = _read_csv(ranking_csv)
    top_rows = rows[:top_k]
    return [int(row["scenario_id"]) for row in top_rows], top_rows


def summarize_policy_on_gcn_subset(
    ranking_csv: Path,
    rl_eval_dir: Path,
    policy_files: dict[str, str],
    output_dir: Path,
    top_k: int = 20,
) -> list[dict]:
    top_ids, top_rows = load_gcn_topk(ranking_csv, top_k)
    top_id_set = set(top_ids)
    summaries = []
    for policy, filename in policy_files.items():
        rows = _read_csv(rl_eval_dir / filename)
        summaries.append(_summarize_rows(policy, "all_test", rows))
        summaries.append(_summarize_rows(policy, f"gcn_top_{len(top_ids)}", [row for row in rows if int(row["scenario_id"]) in top_id_set]))
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "gcn_topk_rl_policy_summary.csv"
    fields = ["policy", "subset", "num_scenarios", "mean_negative_return", "mean_num_line_outages", "mean_load_shed_MW", "pf_failed_rate"]
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    _write_topk_csv(top_rows, output_dir / "gcn_topk_scenarios.csv")
    _write_report(summaries, top_rows, output_dir / "gcn_rl_bridge_report.md")
    return summaries


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _as_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def _summarize_rows(policy: str, subset: str, rows: list[dict]) -> dict:
    def mean_float(key: str) -> float:
        return float(np.mean([float(row[key]) for row in rows])) if rows else 0.0

    return {
        "policy": policy,
        "subset": subset,
        "num_scenarios": len(rows),
        "mean_negative_return": mean_float("negative_return"),
        "mean_num_line_outages": mean_float("num_line_outages"),
        "mean_load_shed_MW": mean_float("load_shed_MW"),
        "pf_failed_rate": float(np.mean([_as_bool(row["pf_failed"]) for row in rows])) if rows else 0.0,
    }


def _write_topk_csv(rows: list[dict], path: Path) -> None:
    fields = ["rank", "scenario_id", "gcn_score", "true_do_nothing_negative_return", "best_improvement", "initial_outages"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(summaries: list[dict], top_rows: list[dict], path: Path) -> None:
    lines = [
        "# IEEE14 GCN-to-RL Bridge",
        "",
        "This report uses the same PYPOWER IEEE14 scenario IDs for both risk identification and mitigation evaluation.",
        "No RTS79, IEEE39, or legacy GCN branch mapping is used.",
        "",
        "## GCN-selected test scenarios",
        "",
        f"Top-K size: {len(top_rows)}",
        "",
        "| rank | scenario_id | GCN score | do-nothing risk | best action improvement | initial outages |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for row in top_rows[:20]:
        lines.append(
            f"| {row['rank']} | {row['scenario_id']} | {float(row['gcn_score']):.4f} | "
            f"{float(row['true_do_nothing_negative_return']):.4f} | {float(row['best_improvement']):.4f} | {row['initial_outages']} |"
        )
    lines.extend([
        "",
        "## RL evaluation on all test vs GCN top-K",
        "",
        "| policy | subset | n | mean negative return | mean line outages | mean load shed MW | PF failed rate |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in summaries:
        lines.append(
            f"| {row['policy']} | {row['subset']} | {row['num_scenarios']} | "
            f"{row['mean_negative_return']:.4f} | {row['mean_num_line_outages']:.4f} | "
            f"{row['mean_load_shed_MW']:.4f} | {row['pf_failed_rate']:.4f} |"
        )
    lines.extend([
        "",
        "Interpretation: the GCN module defines a same-system IEEE14 high-risk subset; the RL policies are evaluated on that subset without changing the action interface.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

