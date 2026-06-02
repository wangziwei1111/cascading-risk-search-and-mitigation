from __future__ import annotations

import csv
import json
from pathlib import Path

from ._common import ROOT, load_config


def main():
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    required = [
        base / "calibration" / "cascade_scenario_summary.json",
        base / "pretrain" / "policy_pretrained_torch.pt",
        base / "train_logs" / "ppo_clip_train.csv",
        base / "checkpoints" / "latest.pt",
        base / "eval" / "eval_before_after_100.csv",
        base / "figures" / "fig_ieee14_survival_negative_return_100.png",
        base / "high_risk" / "high_risk_scenarios_top50.csv",
    ]
    errors = [f"missing: {path}" for path in required if not path.exists()]
    eval_path = base / "eval" / "eval_before_after_100.csv"
    if eval_path.exists():
        errors.extend(_check_eval(eval_path))
    report = {"passed": not errors, "errors": errors}
    out = base / "reports" / "result_integrity_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Integrity check written to {out}; passed={report['passed']}")
    if errors:
        raise SystemExit(1)


def _check_eval(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    errors = []
    allowed = {"do_nothing", "agent"}
    by_id = {}
    for row in rows:
        by_id.setdefault(row["scenario_id"], []).append(row)
        if row["policy"] not in allowed:
            errors.append(f"bad policy {row['policy']}")
        if row.get("negative_return", "") == "":
            errors.append(f"missing negative_return scenario {row['scenario_id']}")
        if int(float(row["num_line_outages"])) < len([x for x in row["initial_outages"].split(",") if x != ""]):
            errors.append(f"line outages less than initial outages scenario {row['scenario_id']}")
    for scenario_id, pair in by_id.items():
        if {row["policy"] for row in pair} != allowed:
            errors.append(f"scenario {scenario_id} missing before/after pair")
            continue
        for key in ["initial_outages", "chronic_index", "load_scale", "gen_scale"]:
            if len({row[key] for row in pair}) != 1:
                errors.append(f"scenario {scenario_id} mismatched {key}")
        agent = [row for row in pair if row["policy"] == "agent"][0]
        if float(agent["num_invalid_actions"]) > 1e-6:
            errors.append(f"scenario {scenario_id} agent invalid actions not near zero")
    return errors


if __name__ == "__main__":
    main()
