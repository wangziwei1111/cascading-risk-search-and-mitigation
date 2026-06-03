from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ._common import ROOT, MODE_DEFAULTS, mode_suffix, normalize_mode, rel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    parser.add_argument("--steps", type=int)
    parser.add_argument("--eval-episodes", type=int)
    args = parser.parse_args()
    mode = normalize_mode(args.mode, args.smoke)
    steps = args.steps or MODE_DEFAULTS[mode]["steps"]
    eval_episodes = args.eval_episodes or MODE_DEFAULTS[mode]["eval_episodes"]
    suffix = mode_suffix(mode)
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    train_log = base / "train_logs" / f"proposed_pretrain_mask{suffix}.csv"
    checkpoint = base / "checkpoints" / f"proposed_pretrain_mask{suffix}" / "latest.pt"
    eval_csv = base / "eval" / f"eval_{eval_episodes}_before_after{suffix}.csv"

    commands = [
        ["scripts.rl_mitigation.paper.pretrain_do_nothing_ieee14", "--config", args.config, "--mode", mode, "--states", str(MODE_DEFAULTS[mode]["pretrain_states"])],
        ["scripts.rl_mitigation.paper.train_ieee14_ppo", "--config", args.config, "--mode", mode, "--steps", str(steps)],
        ["scripts.rl_mitigation.paper.evaluate_ieee14_paper_policy", "--config", args.config, "--mode", mode, "--episodes", str(eval_episodes), "--checkpoint", str(checkpoint)],
        ["scripts.rl_mitigation.paper.check_ieee14_eval_integrity", "--eval-csv", str(eval_csv), "--suffix", mode],
        ["scripts.rl_mitigation.paper.evaluate_ieee14_survival", "--eval-csv", str(eval_csv), "--episodes", str(eval_episodes), "--mode", mode],
        ["scripts.rl_mitigation.paper.check_ieee14_paper_claims", "--eval-csv", str(eval_csv), "--suffix", mode, "--checkpoint", str(checkpoint), "--train-log", str(train_log)],
    ]
    for command in commands:
        _run(command)
    _write_report(args.config, mode, steps, eval_episodes, eval_csv, checkpoint, train_log)


def _run(args: list[str]) -> None:
    subprocess.run([sys.executable, "-m", *args], check=True)


def _write_report(config: str, mode: str, steps: int, eval_episodes: int, eval_csv: Path, checkpoint: Path, train_log: Path) -> None:
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    reports = base / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    suffix = mode_suffix(mode)
    pretrain_path = base / "pretrain" / "pretrain_diagnostics.json"
    claim_path = reports / f"ieee14_claim_check{suffix}.json"
    pretrain = json.loads(pretrain_path.read_text(encoding="utf-8")) if pretrain_path.exists() else {}
    claim = json.loads(claim_path.read_text(encoding="utf-8")) if claim_path.exists() else {}
    figure8 = base / "figures" / f"fig8_ieee14_negative_return_survival{suffix}.png"
    summary = {
        "config": config,
        "mode": mode,
        "training_steps": int(steps),
        "eval_episodes": int(eval_episodes),
        "source_eval_csv": rel(eval_csv),
        "source_checkpoint": rel(checkpoint),
        "source_train_log": rel(train_log),
        "pretrain_diagnostics": {
            "mean_prob_do_nothing": pretrain.get("mean_prob_do_nothing"),
            "median_prob_do_nothing": pretrain.get("median_prob_do_nothing"),
            "mean_entropy": pretrain.get("mean_entropy"),
            "mean_max_nonzero_prob": pretrain.get("mean_max_nonzero_prob"),
            "target_reached": pretrain.get("target_reached"),
            "warning": pretrain.get("warning"),
        },
        "figure8": rel(figure8),
        "claim_check": rel(claim_path),
        "overall": claim.get("overall", "not_supported"),
        "metrics": claim.get("metrics", {}),
        "plain_language_conclusion": claim.get("plain_language_conclusion", ""),
        "recommended_thesis_wording": claim.get("recommended_thesis_wording", ""),
    }
    summary_path = reports / f"ieee14_paper_pipeline_summary{suffix}.json"
    report_path = reports / f"ieee14_paper_pipeline_report{suffix}.md"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# IEEE14 Paper Pipeline Report",
        "",
        f"Mode: `{mode}`",
        f"Config: `{config}`",
        f"Training steps: `{steps}`",
        f"Eval episodes: `{eval_episodes}`",
        "",
        "## Sources",
        "",
        f"- source_eval_csv: `{summary['source_eval_csv']}`",
        f"- source_checkpoint: `{summary['source_checkpoint']}`",
        f"- source_train_log: `{summary['source_train_log']}`",
        f"- Figure 8: `{summary['figure8']}`",
        f"- Claim check: `{summary['claim_check']}`",
        "",
        "## Do-Nothing Pretrain Diagnostics",
        "",
    ]
    for key, value in summary["pretrain_diagnostics"].items():
        lines.append(f"- {key}: `{value}`")
    if summary["pretrain_diagnostics"].get("warning"):
        lines.extend(["", f"Warning: `{summary['pretrain_diagnostics']['warning']}`"])
    lines.extend(["", "## Claim Metrics", "", "| Metric | do-nothing | proposed | diff | direction | supported |", "|---|---:|---:|---:|---|---:|"])
    for row in summary["metrics"].values():
        lines.append(
            f"| {row['metric']} | {row['do_nothing_mean']:.6f} | {row['proposed_mean']:.6f} | "
            f"{row['difference_proposed_minus_do_nothing']:.6f} | {row['direction']} | {row['supported']} |"
        )
    lines.extend(["", f"Overall: `{summary['overall']}`", "", summary["plain_language_conclusion"], "", summary["recommended_thesis_wording"]])
    report_text = "\n".join(lines) + "\n"
    report_path.write_text(report_text, encoding="utf-8")
    (reports / "ieee14_paper_pipeline_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (reports / "ieee14_paper_pipeline_report.md").write_text(report_text, encoding="utf-8")


if __name__ == "__main__":
    main()
