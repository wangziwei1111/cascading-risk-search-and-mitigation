from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from statistics import mean

import numpy as np

from ._common import ROOT
from rl_mitigation.evaluation.paired_stats import paired_improvement_summary


VARIANTS = [
    ("ppo_random_init", "none"),
    ("ppo_do_nothing_init", "do_nothing"),
    ("ppo_oracle_bc_init", "oracle_bc"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--train-steps", type=int, default=20000)
    parser.add_argument("--eval-episodes", type=int, default=100)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    steps = min(args.train_steps, 2048) if args.smoke else args.train_steps
    eval_episodes = min(args.eval_episodes, 50) if args.smoke else args.eval_episodes
    _ensure_inputs(args.config, eval_episodes)
    _run([sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--config", args.config, "--split", "test", "--episodes", str(eval_episodes), "--without-agent"])
    _run([sys.executable, "-m", "scripts.rl_mitigation.evaluate_oracle_policy", "--config", args.config, "--split", "test", "--episodes", str(eval_episodes)])
    all_rows = _read_csv(ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / "test_eval_do_nothing.csv")
    all_rows.extend(_read_csv(ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / "test_eval_one_step_oracle.csv"))
    summary_rows = []
    for variant, init in VARIANTS:
        _run([sys.executable, "-m", "scripts.rl_mitigation.train_ppo", "--case", "ieee14", "--config", args.config, "--steps", str(steps), "--init", init, *(("--smoke",) if args.smoke else ())])
        ckpt = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / f"ppo_init_{init}" / "latest.pt"
        for mode in ["deterministic", "stochastic"]:
            _run([
                sys.executable, "-m", "scripts.rl_mitigation.evaluate_policy", "--config", args.config,
                "--split", "test", "--episodes", str(eval_episodes), "--with-agent",
                "--checkpoint", str(ckpt), "--policy-name", variant, "--eval-mode", mode,
            ])
        _run([
            sys.executable, "-m", "scripts.rl_mitigation.diagnose_policy_actions", "--config", args.config,
            "--split", "test", "--episodes", str(eval_episodes), "--checkpoint", str(ckpt), "--policy-name", variant,
        ])
        for mode in ["deterministic", "stochastic"]:
            eval_rows = _read_csv(ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / f"test_eval_{variant}_{mode}.csv")
            all_rows.extend(eval_rows)
            diag = _read_json(ROOT / "results" / "rl_mitigation" / "ieee14" / "diagnostics" / f"test_{variant}_summary.json")
            summary_rows.append(_summary_row(eval_rows, all_rows, variant, init, steps, mode, diag))
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "ablation"
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(summary_rows, out_dir / "training_ablation_summary.csv")
    with open(out_dir / "training_ablation_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_rows, f, indent=2, ensure_ascii=False)
    print(f"Training ablation written to {out_dir}")


def _ensure_inputs(config: str, eval_episodes: int):
    _run([sys.executable, "-m", "scripts.rl_mitigation.generate_ieee14_scenario_splits", "--config", config, "--train", "300", "--val", "100", "--test", "100"])
    for split in ["train", "val", "test"]:
        summary = ROOT / "results" / "rl_mitigation" / "ieee14" / "action_value_scan" / f"{split}_action_value_summary.json"
        if not summary.exists():
            _run([sys.executable, "-m", "scripts.rl_mitigation.scan_ieee14_action_values", "--config", config, "--split", split])
    oracle_bc = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain" / "oracle_bc_policy.pt"
    if not oracle_bc.exists():
        _run([sys.executable, "-m", "scripts.rl_mitigation.pretrain_oracle_bc", "--config", config, "--episodes", "300"])
    do_nothing = ROOT / "results" / "rl_mitigation" / "ieee14" / "pretrain" / "policy_pretrained_torch.pt"
    if not do_nothing.exists():
        _run([sys.executable, "-m", "scripts.rl_mitigation.pretrain_do_nothing", "--case", "ieee14", "--config", config])


def _summary_row(rows, all_rows, variant, init, train_steps, mode, diag):
    neg = [float(row["negative_return"]) for row in rows]
    out = {
        "variant": variant,
        "init_type": init,
        "train_steps": train_steps,
        "eval_split": "test",
        "eval_mode": mode,
        "mean_negative_return": mean(neg),
        "p95_negative_return": float(np.percentile(neg, 95)),
        "mean_num_generations": mean(float(row["num_generations"]) for row in rows),
        "mean_num_line_outages": mean(float(row["num_line_outages"]) for row in rows),
        "mean_load_shed_MW": mean(float(row["load_shed_MW"]) for row in rows),
        "mean_load_shed_ratio": mean(float(row["load_shed_ratio"]) for row in rows),
        "mean_num_proactive_actions": mean(float(row["num_proactive_actions"]) for row in rows),
        "mean_num_invalid_actions": mean(float(row["num_invalid_actions"]) for row in rows),
        "pf_failed_ratio": mean(str(row["pf_failed"]).lower() == "true" for row in rows),
        "argmax_do_nothing_ratio": diag.get("argmax_do_nothing_ratio", 0.0),
        "mean_prob_do_nothing": diag.get("mean_prob_do_nothing", 0.0),
        "mean_entropy": diag.get("mean_entropy", 0.0),
    }
    out.update(paired_improvement_summary(all_rows, variant, "do_nothing"))
    return out


def _run(cmd):
    subprocess.run(cmd, cwd=ROOT, check=True)


def _read_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
