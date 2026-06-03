from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from ._common import ROOT


def main() -> None:
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    eval_files = sorted((base / "eval").glob("eval_*_before_after*.csv"))
    rows = _read(eval_files[-1]) if eval_files else []
    by_policy = {}
    for row in rows:
        by_policy.setdefault(row["policy"], []).append(row)
    report = {
        "source_eval": str(eval_files[-1]) if eval_files else None,
        "checks": {},
        "overall": "not_supported",
        "required_statement": "当前PYPOWER IEEE14替代环境下，论文关于PPO缓解效果的数值结论尚未完全复现；已复现MDP和训练机制，但性能结论需要进一步调参或更接近原论文grid2op环境。",
    }
    if "do_nothing" in by_policy and "paper_proposed_policy" in by_policy:
        dn = _summary(by_policy["do_nothing"])
        pp = _summary(by_policy["paper_proposed_policy"])
        checks = {
            "mean_negative_return_lower": pp["mean_negative_return"] < dn["mean_negative_return"],
            "p95_negative_return_lower": pp["p95_negative_return"] < dn["p95_negative_return"],
            "num_generations_lower": pp["mean_num_generations"] < dn["mean_num_generations"],
            "num_line_outages_lower": pp["mean_num_line_outages"] < dn["mean_num_line_outages"],
            "load_shed_lower": pp["mean_load_shed_MW"] < dn["mean_load_shed_MW"],
            "invalid_action_count_low": pp["mean_num_invalid_actions"] <= dn["mean_num_invalid_actions"],
            "proactive_actions_conservative": pp["mean_num_proactive_actions"] <= 2.0,
            "pf_failed_not_higher": pp["pf_failed_ratio"] <= dn["pf_failed_ratio"],
        }
        supported = sum(bool(v) for v in checks.values())
        report["do_nothing"] = dn
        report["paper_proposed_policy"] = pp
        report["checks"] = checks
        report["overall"] = "fully_supported" if supported == len(checks) else "partially_supported" if supported >= len(checks) // 2 else "not_supported"
    out = base / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ieee14_claim_check.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_md(report, out / "ieee14_claim_check.md")
    print(f"IEEE14 claim check written to {out}")


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _summary(rows: list[dict]) -> dict:
    def mean(key):
        return float(np.mean([float(row[key]) for row in rows])) if rows else 0.0
    vals = [float(row["negative_return"]) for row in rows]
    return {
        "n": len(rows),
        "mean_negative_return": mean("negative_return"),
        "p95_negative_return": float(np.percentile(vals, 95)) if vals else 0.0,
        "mean_num_generations": mean("num_generations"),
        "mean_num_line_outages": mean("num_line_outages"),
        "mean_load_shed_MW": mean("load_shed_MW"),
        "mean_num_invalid_actions": mean("num_invalid_actions"),
        "mean_num_proactive_actions": mean("num_proactive_actions"),
        "pf_failed_ratio": float(np.mean([str(row["pf_failed"]).lower() == "true" for row in rows])) if rows else 0.0,
    }


def _write_md(report: dict, path: Path) -> None:
    lines = ["# IEEE14 Paper Claim Check", "", f"Overall: `{report['overall']}`", "", report["required_statement"], ""]
    if report.get("checks"):
        lines.extend(["| Check | Supported |", "|---|---:|"])
        for key, value in report["checks"].items():
            lines.append(f"| {key} | {bool(value)} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

