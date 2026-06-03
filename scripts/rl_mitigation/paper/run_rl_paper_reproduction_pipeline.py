from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ._common import ROOT


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--run-ieee5", action="store_true")
    parser.add_argument("--run-ieee14", action="store_true")
    parser.add_argument("--run-ieee118", action="store_true")
    parser.add_argument("--ieee14-steps", type=int, default=60000)
    parser.add_argument("--ieee118-steps", type=int, default=600000)
    parser.add_argument("--eval-episodes", type=int, default=1000)
    args = parser.parse_args()
    run_all = not (args.run_ieee5 or args.run_ieee14 or args.run_ieee118)
    completed = []
    if run_all or args.run_ieee5:
        _run(["scripts.rl_mitigation.paper.run_ieee5_dp", "--config", "configs/rl_mitigation/paper/ieee5_dp.yaml"])
        _run(["scripts.rl_mitigation.paper.check_figure1_cascade_flow", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml"])
        completed.extend(["ieee5_dp", "figure1_trace"])
    if run_all or args.run_ieee14:
        cmd = ["scripts.rl_mitigation.paper.run_ieee14_paper_pipeline", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml", "--steps", str(args.ieee14_steps), "--eval-episodes", str(args.eval_episodes)]
        if args.smoke:
            cmd.append("--smoke")
        _run(cmd)
        _run(["scripts.rl_mitigation.paper.train_ieee14_gridsearch", "--config", "configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml", "--steps", str(min(args.ieee14_steps, 512) if args.smoke else args.ieee14_steps)] + (["--smoke"] if args.smoke else []))
        completed.append("ieee14_paper")
    if run_all or args.run_ieee118:
        _run(["scripts.rl_mitigation.paper.pretrain_do_nothing_ieee118", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--states", "16" if args.smoke else "2048"])
        _run(["scripts.rl_mitigation.paper.train_ieee118_ppo", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--steps", str(args.ieee118_steps)] + (["--smoke"] if args.smoke else []))
        _run(["scripts.rl_mitigation.paper.evaluate_ieee118_paper_policy", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--episodes", str(args.eval_episodes)] + (["--smoke"] if args.smoke else []))
        _run(["scripts.rl_mitigation.paper.make_ieee118_paper_figures"] + (["--smoke"] if args.smoke else []))
        completed.append("ieee118_smoke")
    _write_summary(completed, smoke=args.smoke)


def _run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", *args], check=True)


def _write_summary(completed: list[str], smoke: bool) -> None:
    out = ROOT / "results" / "rl_mitigation" / "paper"
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "smoke": bool(smoke),
        "completed": completed,
        "main_result_dir": "results/rl_mitigation/paper",
        "diagnostics_are_not_paper_results": True,
    }
    (out / "rl_paper_reproduction_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    lines = [
        "# RL Paper Reproduction Report",
        "",
        f"Smoke run: `{smoke}`",
        f"Completed: `{', '.join(completed)}`",
        "",
        "The main reproduction output is separated under `results/rl_mitigation/paper/`.",
        "Diagnostics and enhanced experiments are not claimed as original paper results.",
        "",
        "Current IEEE14 claim check should be read before making thesis claims.",
    ]
    (out / "rl_paper_reproduction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

