from __future__ import annotations

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--eval-episodes", type=int, default=1000)
    args = parser.parse_args()
    _run(["scripts.rl_mitigation.paper.pretrain_do_nothing_ieee14", "--config", args.config, "--states", "512" if args.smoke else "2048"])
    train = ["scripts.rl_mitigation.paper.train_ieee14_ppo", "--config", args.config, "--steps", str(args.steps)]
    if args.smoke:
        train.append("--smoke")
    _run(train)
    eval_cmd = ["scripts.rl_mitigation.paper.evaluate_ieee14_paper_policy", "--config", args.config, "--episodes", str(args.eval_episodes)]
    if args.smoke:
        eval_cmd.append("--smoke")
    _run(eval_cmd)
    eval_csv = f"results/rl_mitigation/paper/ieee14/eval/eval_{min(args.eval_episodes, 100) if args.smoke else args.eval_episodes}_before_after{'_smoke' if args.smoke else ''}.csv"
    _run(["scripts.rl_mitigation.paper.evaluate_ieee14_survival", "--eval-csv", eval_csv, "--episodes", str(min(args.eval_episodes, 100) if args.smoke else args.eval_episodes)])
    _run(["scripts.rl_mitigation.paper.check_ieee14_paper_claims"])


def _run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", *args], check=True)


if __name__ == "__main__":
    main()

