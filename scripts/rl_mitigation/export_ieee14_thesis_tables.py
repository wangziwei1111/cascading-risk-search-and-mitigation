from __future__ import annotations

import csv
import json
from statistics import mean

import numpy as np

from ._common import ROOT


def main():
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    out = base / "tables"
    out.mkdir(parents=True, exist_ok=True)
    eval_rows = _read_csv(base / "eval" / "eval_before_after_100.csv")
    high_risk = _read_csv(base / "high_risk" / "high_risk_scenarios_top50.csv")
    with open(base / "calibration" / "cascade_scenario_summary.json", encoding="utf-8") as f:
        calibration = json.load(f)
    _write_before_after(eval_rows, out / "table_ieee14_before_after_summary.csv")
    _write_csv(high_risk[:10], out / "table_ieee14_high_risk_top10.csv")
    _write_csv(calibration["candidates"], out / "table_ieee14_capacity_calibration.csv")
    _write_explanation(out / "thesis_table_explanation.md", calibration.get("recommended_rate_a_scale"))
    print(f"Thesis tables written to {out}")


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_before_after(rows, path):
    out = []
    for policy in sorted({row["policy"] for row in rows}):
        cur = [row for row in rows if row["policy"] == policy]
        neg = [float(row["negative_return"]) for row in cur]
        out.append({
            "policy": policy,
            "episodes": len(cur),
            "mean_negative_return": mean(neg),
            "p95_negative_return": float(np.percentile(neg, 95)),
            "mean_num_generations": mean(float(row["num_generations"]) for row in cur),
            "mean_num_line_outages": mean(float(row["num_line_outages"]) for row in cur),
            "mean_load_shed_MW": mean(float(row["load_shed_MW"]) for row in cur),
            "mean_load_shed_ratio": mean(float(row["load_shed_ratio"]) for row in cur),
            "mean_num_proactive_actions": mean(float(row["num_proactive_actions"]) for row in cur),
            "mean_num_invalid_actions": mean(float(row["num_invalid_actions"]) for row in cur),
            "pf_failed_ratio": mean(str(row["pf_failed"]).lower() == "true" for row in cur),
        })
    _write_csv(out, path)


def _write_explanation(path, recommended_scale):
    path.write_text(
        "# IEEE14 小系统实验表格说明\n\n"
        "表格基于 PYPOWER IEEE14 小系统、N-1/共同母线 N-2 初始故障采样、"
        "以及 scaled_from_base_flow 容量校准得到。before/after 评估使用同一批 scenario，"
        "因此可用于比较 do-nothing 与 PPO agent 在负回报、级联代数、断线数和切负荷等指标上的差异。\n\n"
        f"容量校准脚本推荐的 rate_a_scale 为 `{recommended_scale}`。该值用于构造小系统压力场景，"
        "不等同于论文原始系统参数。\n\n"
        "论文中建议表述为：在 PYPOWER IEEE14 小系统环境下，PPO agent 相较 do-nothing 策略在若干指标上表现出缓解效果。"
        "不要表述为完全复现原论文 Figure 7/8 的数值结果。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
