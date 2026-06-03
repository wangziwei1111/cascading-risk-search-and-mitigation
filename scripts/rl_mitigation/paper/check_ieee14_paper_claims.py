from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from ._common import ROOT, mode_suffix, normalize_mode, rel


KEY_METRICS = {
    "mean_negative_return",
    "mean_num_line_outages",
    "mean_load_shed_MW",
    "pf_failed_ratio",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-csv")
    parser.add_argument("--suffix", choices=["smoke", "medium", "formal"])
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    parser.add_argument("--checkpoint")
    parser.add_argument("--train-log")
    args = parser.parse_args()

    inferred = "medium" if args.eval_csv and "_medium" in args.eval_csv else None
    mode = normalize_mode(args.suffix or args.mode or inferred, bool(args.eval_csv and "_smoke" in args.eval_csv))
    suffix = mode_suffix(mode)
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    checkpoint = Path(args.checkpoint) if args.checkpoint else base / "checkpoints" / f"proposed_pretrain_mask{suffix}" / "latest.pt"
    train_log = Path(args.train_log) if args.train_log else base / "train_logs" / f"proposed_pretrain_mask{suffix}.csv"
    eval_path = _resolve_eval(base, args.eval_csv)

    rows = _read(eval_path) if eval_path and eval_path.exists() else []
    by_policy: dict[str, list[dict]] = {}
    for row in rows:
        by_policy.setdefault(row["policy"], []).append(row)

    report = {
        "source_eval": rel(eval_path) if eval_path else None,
        "source_eval_csv": rel(eval_path) if eval_path else None,
        "source_checkpoint": rel(checkpoint),
        "source_train_log": rel(train_log),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_scenarios": 0,
        "num_rows": len(rows),
        "mode": mode,
        "overall": "not_supported",
        "metrics": {},
        "checks": {},
        "plain_language_conclusion": "IEEE14 evaluation rows are missing or incomplete.",
        "recommended_thesis_wording": (
            "当前仓库已复现论文的MDP、动作空间、奖励函数、do-nothing初始化、"
            "invalid action mask和PPO训练流程；性能结论必须以claim check为准。"
        ),
    }

    metric_rows: list[dict] = []
    if "do_nothing" in by_policy and "paper_proposed_policy" in by_policy:
        dn = _summary(by_policy["do_nothing"])
        pp = _summary(by_policy["paper_proposed_policy"])
        metric_rows = _metric_rows(dn, pp)
        checks = {f"{row['metric']}_supported": bool(row["supported"]) for row in metric_rows}
        report.update({
            "do_nothing": dn,
            "paper_proposed_policy": pp,
            "metrics": {row["metric"]: row for row in metric_rows},
            "checks": checks,
            "overall": _overall(metric_rows),
            "num_scenarios": len({row.get("scenario_id") for row in rows}),
            "num_rows": len(rows),
        })
        if report["overall"] == "fully_supported":
            conclusion = "当前IEEE14评估支持paper proposed PPO相对do-nothing的主要缓解效果。"
        elif report["overall"] == "partially_supported":
            conclusion = "性能结论未完全复现：部分指标改善，但关键指标未全部优于do-nothing。"
        else:
            conclusion = "性能结论未复现：关键缓解指标未优于do-nothing。"
        if report["metrics"]["mean_negative_return"]["direction"] != "improved":
            conclusion += " 性能结论未完全复现，特别是mean negative return未降低。"
        report["plain_language_conclusion"] = conclusion
        report["recommended_thesis_wording"] = (
            f"在PYPOWER IEEE14替代环境下，当前{mode}运行完成了论文机制复现；"
            f"PPO缓解性能结论为{report['overall']}，不能写成完整数值复现。"
        )

    out = base / "reports"
    tables = base / "tables"
    out.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    (out / f"ieee14_claim_check{suffix}.json").write_text(payload, encoding="utf-8")
    (out / "ieee14_claim_check.json").write_text(payload, encoding="utf-8")
    _write_md(report, out / f"ieee14_claim_check{suffix}.md")
    _write_md(report, out / "ieee14_claim_check.md")
    if metric_rows:
        _write_metrics_csv(metric_rows, tables / f"table_ieee14_claim_metrics{suffix}.csv")
        _write_metrics_csv(metric_rows, tables / "table_ieee14_claim_metrics.csv")
    print(f"IEEE14 claim check written to {out}")


def _resolve_eval(base: Path, eval_csv: str | None) -> Path | None:
    if eval_csv:
        path = Path(eval_csv)
        return path if path.is_absolute() else ROOT / path
    files = sorted((base / "eval").glob("eval_*_before_after*.csv"))
    return files[-1] if files else None


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _summary(rows: list[dict]) -> dict:
    def mean(key: str) -> float:
        return float(np.mean([float(row.get(key, 0.0)) for row in rows])) if rows else 0.0

    vals = [float(row["negative_return"]) for row in rows]
    return {
        "n": len(rows),
        "mean_negative_return": mean("negative_return"),
        "p95_negative_return": float(np.percentile(vals, 95)) if vals else 0.0,
        "mean_num_generations": mean("num_generations"),
        "mean_num_line_outages": mean("num_line_outages"),
        "mean_load_shed_MW": mean("load_shed_MW"),
        "mean_load_shed_ratio": mean("load_shed_ratio"),
        "pf_failed_ratio": float(np.mean([str(row.get("pf_failed")).lower() == "true" for row in rows])) if rows else 0.0,
        "mean_num_invalid_actions": mean("num_invalid_actions"),
        "mean_num_proactive_actions": mean("num_proactive_actions"),
    }


def _metric_rows(dn: dict, pp: dict) -> list[dict]:
    metrics = [
        "mean_negative_return",
        "p95_negative_return",
        "mean_num_generations",
        "mean_num_line_outages",
        "mean_load_shed_MW",
        "mean_load_shed_ratio",
        "pf_failed_ratio",
        "mean_num_invalid_actions",
        "mean_num_proactive_actions",
    ]
    rows = []
    for metric in metrics:
        dn_val = float(dn.get(metric, 0.0))
        pp_val = float(pp.get(metric, 0.0))
        diff = pp_val - dn_val
        if abs(diff) < 1e-9:
            direction = "unchanged"
        else:
            direction = "improved" if diff < 0.0 else "worse"
        supported = direction in {"improved", "unchanged"}
        if metric == "mean_num_proactive_actions":
            supported = pp_val <= 2.0
            direction = "improved" if supported else "worse"
        rows.append({
            "metric": metric,
            "do_nothing_mean": dn_val,
            "proposed_mean": pp_val,
            "difference_proposed_minus_do_nothing": diff,
            "relative_change_percent": 0.0 if abs(dn_val) < 1e-12 else 100.0 * diff / abs(dn_val),
            "direction": direction,
            "supported": bool(supported),
        })
    return rows


def _overall(metric_rows: list[dict]) -> str:
    rows = {row["metric"]: row for row in metric_rows}
    key_improved = [
        rows["mean_negative_return"]["direction"] == "improved",
        rows["mean_num_line_outages"]["direction"] == "improved",
        rows["mean_load_shed_MW"]["direction"] == "improved",
    ]
    pf_not_higher = rows["pf_failed_ratio"]["difference_proposed_minus_do_nothing"] <= 1e-9
    if all(key_improved) and pf_not_higher:
        return "fully_supported"
    if any(key_improved):
        return "partially_supported"
    return "not_supported"


def _write_metrics_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "metric", "do_nothing_mean", "proposed_mean",
        "difference_proposed_minus_do_nothing", "relative_change_percent",
        "direction", "supported",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_md(report: dict, path: Path) -> None:
    lines = [
        "# IEEE14 Paper Claim Check",
        "",
        f"Mode: `{report['mode']}`",
        f"Overall: `{report['overall']}`",
        f"source_eval_csv: `{report['source_eval_csv']}`",
        f"source_checkpoint: `{report['source_checkpoint']}`",
        f"source_train_log: `{report['source_train_log']}`",
        "",
        report["plain_language_conclusion"],
        "",
        report["recommended_thesis_wording"],
    ]
    if report.get("metrics"):
        lines.extend(["", "| Metric | do-nothing | proposed | diff | direction | supported |", "|---|---:|---:|---:|---|---:|"])
        for row in report["metrics"].values():
            lines.append(
                f"| {row['metric']} | {row['do_nothing_mean']:.6f} | {row['proposed_mean']:.6f} | "
                f"{row['difference_proposed_minus_do_nothing']:.6f} | {row['direction']} | {row['supported']} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
