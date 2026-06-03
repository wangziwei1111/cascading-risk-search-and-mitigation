from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ._common import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--eval-episodes", type=int, default=1000)
    args = parser.parse_args()
    steps = min(args.steps, 2048) if args.smoke else args.steps
    eval_episodes = min(args.eval_episodes, 100) if args.smoke else args.eval_episodes
    commands = [
        ["scripts.rl_mitigation.paper.pretrain_do_nothing_ieee14", "--config", args.config, "--states", "512" if args.smoke else "2048"],
        ["scripts.rl_mitigation.paper.train_ieee14_ppo", "--config", args.config, "--steps", str(args.steps)] + (["--smoke"] if args.smoke else []),
        ["scripts.rl_mitigation.paper.evaluate_ieee14_paper_policy", "--config", args.config, "--episodes", str(args.eval_episodes)] + (["--smoke"] if args.smoke else []),
    ]
    for command in commands:
        _run(command)
    eval_csv = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "eval" / f"eval_{eval_episodes}_before_after{'_smoke' if args.smoke else ''}.csv"
    _run(["scripts.rl_mitigation.paper.evaluate_ieee14_survival", "--eval-csv", str(eval_csv), "--episodes", str(eval_episodes)] + (["--smoke"] if args.smoke else []))
    _run(["scripts.rl_mitigation.paper.check_ieee14_eval_integrity", "--eval-csv", str(eval_csv)])
    _run(["scripts.rl_mitigation.paper.check_ieee14_paper_claims", "--eval-csv", str(eval_csv)])
    _write_report(args.config, args.smoke, steps, eval_episodes, eval_csv)


def _run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", *args], check=True)


def _write_report(config: str, smoke: bool, steps: int, eval_episodes: int, eval_csv: Path) -> None:
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    reports = base / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    pretrain_path = base / "pretrain" / "pretrain_diagnostics.json"
    claim_path = reports / "ieee14_claim_check.json"
    pretrain = json.loads(pretrain_path.read_text(encoding="utf-8")) if pretrain_path.exists() else {}
    claim = json.loads(claim_path.read_text(encoding="utf-8")) if claim_path.exists() else {}
    after = pretrain.get("after", {})
    figure8 = base / "figures" / f"fig8_ieee14_negative_return_survival{'_smoke' if smoke else ''}.png"
    summary = {
        "config": config,
        "smoke": bool(smoke),
        "training_steps": int(steps),
        "eval_episodes": int(eval_episodes),
        "pretrain_diagnostics": {
            "mean_prob_do_nothing": after.get("mean_prob_do_nothing"),
            "median_prob_do_nothing": after.get("median_prob_do_nothing"),
            "mean_entropy": after.get("mean_entropy"),
            "mean_max_nonzero_prob": after.get("mean_max_nonzero_prob"),
        },
        "train_log": str(base / "train_logs" / f"proposed_pretrain_mask{'_smoke' if smoke else ''}.csv"),
        "checkpoint": str(base / "checkpoints" / "proposed_pretrain_mask" / "latest.pt"),
        "eval_csv": str(eval_csv),
        "figure8": str(figure8),
        "claim_check": str(claim_path),
        "overall": claim.get("overall", "not_supported"),
        "metrics": claim.get("metrics", {}),
        "boundary_statement": (
            "当前PYPOWER IEEE14替代环境下，plain paper PPO尚未稳定优于do-nothing。"
            "仓库已复现MDP、动作空间、奖励函数、do-nothing初始化、invalid action mask和PPO训练流程；"
            "性能结论仍需更长训练、更接近原论文grid2op环境或进一步调参验证。"
        ),
    }
    (reports / "ieee14_paper_pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# IEEE14 Paper Pipeline Report",
        "",
        f"Config: `{config}`",
        f"Smoke: `{smoke}`",
        f"Training steps: `{steps}`",
        f"Eval episodes: `{eval_episodes}`",
        "",
        "## Artifacts",
        "",
        f"- PPO train log: `{summary['train_log']}`",
        f"- Checkpoint: `{summary['checkpoint']}`",
        f"- Eval CSV: `{summary['eval_csv']}`",
        f"- Figure 8: `{summary['figure8']}`",
        f"- Claim check: `{summary['claim_check']}`",
        "",
        "## Do-Nothing Pretrain Diagnostics",
        "",
    ]
    for key, value in summary["pretrain_diagnostics"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Claim Metrics", "", "| Metric | do-nothing | proposed | diff | direction | supported |", "|---|---:|---:|---:|---|---:|"])
    for row in summary["metrics"].values():
        lines.append(
            f"| {row['metric']} | {row['do_nothing_mean']:.4f} | {row['proposed_mean']:.4f} | "
            f"{row['difference_proposed_minus_do_nothing']:.4f} | {row['direction']} | {row['supported']} |"
        )
    lines.extend(["", f"Overall: `{summary['overall']}`", "", summary["boundary_statement"]])
    (reports / "ieee14_paper_pipeline_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
