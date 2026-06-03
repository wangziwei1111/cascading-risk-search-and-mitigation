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
    steps: dict[str, dict] = {}

    if run_all or args.run_ieee5:
        _step(steps, "ieee5_dp", ["scripts.rl_mitigation.paper.run_ieee5_dp", "--config", "configs/rl_mitigation/paper/ieee5_dp.yaml"], ["results/rl_mitigation/paper/ieee5/ieee5_dp_report.md"])
        _step(steps, "figure1_trace", ["scripts.rl_mitigation.paper.check_figure1_cascade_flow", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml"], ["results/rl_mitigation/paper/figure1_trace/ieee14_example_trace.md"])

    if run_all or args.run_ieee14:
        _step(
            steps,
            "ieee14_paper_pipeline",
            ["scripts.rl_mitigation.paper.run_ieee14_paper_pipeline", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml", "--steps", str(args.ieee14_steps), "--eval-episodes", str(args.eval_episodes)] + (["--smoke"] if args.smoke else []),
            ["results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_report.md"],
        )
        _step(
            steps,
            "ieee14_gridsearch",
            ["scripts.rl_mitigation.paper.train_ieee14_gridsearch", "--config", "configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml", "--steps", str(min(args.ieee14_steps, 512) if args.smoke else args.ieee14_steps)] + (["--smoke"] if args.smoke else []),
            ["results/rl_mitigation/paper/ieee14/figures/fig7_ieee14_learning_curves_gridsearch_smoke.png" if args.smoke else "results/rl_mitigation/paper/ieee14/figures/fig7_ieee14_learning_curves_gridsearch.png"],
        )
        eval_csv = f"results/rl_mitigation/paper/ieee14/eval/eval_{min(args.eval_episodes, 100) if args.smoke else args.eval_episodes}_before_after{'_smoke' if args.smoke else ''}.csv"
        _step(steps, "ieee14_eval_integrity", ["scripts.rl_mitigation.paper.check_ieee14_eval_integrity", "--eval-csv", eval_csv], ["results/rl_mitigation/paper/ieee14/reports/ieee14_eval_integrity_check.json"])
        _step(steps, "ieee14_claim_check", ["scripts.rl_mitigation.paper.check_ieee14_paper_claims", "--eval-csv", eval_csv], ["results/rl_mitigation/paper/ieee14/reports/ieee14_claim_check.json", "results/rl_mitigation/paper/ieee14/tables/table_ieee14_claim_metrics.csv"])
        _step(steps, "ieee14_mask_pretrain_ablation", ["scripts.rl_mitigation.paper.compare_ieee14_mask_pretrain_ablation", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml", "--smoke", "--steps", "512", "--eval-episodes", "50"], ["results/rl_mitigation/paper/ieee14/ablation/mask_pretrain_ablation.csv"])

    if run_all or args.run_ieee118:
        _step(steps, "ieee118_pretrain", ["scripts.rl_mitigation.paper.pretrain_do_nothing_ieee118", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--states", "16" if args.smoke else "2048"], ["results/rl_mitigation/paper/ieee118/pretrain/pretrain_diagnostics.json"])
        _step(steps, "ieee118_ppo", ["scripts.rl_mitigation.paper.train_ieee118_ppo", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--steps", str(args.ieee118_steps)] + (["--smoke"] if args.smoke else []), ["results/rl_mitigation/paper/ieee118/train_logs/proposed_pretrain_mask_smoke.csv" if args.smoke else "results/rl_mitigation/paper/ieee118/train_logs/proposed_pretrain_mask.csv"])
        _step(steps, "ieee118_eval", ["scripts.rl_mitigation.paper.evaluate_ieee118_paper_policy", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--episodes", str(args.eval_episodes)] + (["--smoke"] if args.smoke else []), [f"results/rl_mitigation/paper/ieee118/eval/eval_{min(args.eval_episodes, 20) if args.smoke else args.eval_episodes}_before_after{'_smoke' if args.smoke else ''}.csv"])
        _step(steps, "ieee118_figures", ["scripts.rl_mitigation.paper.make_ieee118_paper_figures"] + (["--smoke"] if args.smoke else []), ["results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png" if args.smoke else "results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline.png"])

    _write_summary(steps, smoke=args.smoke)


def _step(steps: dict[str, dict], name: str, command: list[str], outputs: list[str]) -> None:
    try:
        completed = subprocess.run([sys.executable, "-m", *command], check=True, capture_output=True, text=True)
        steps[name] = {"status": "completed", "command": command, "outputs": outputs, "stdout": completed.stdout[-2000:]}
    except subprocess.CalledProcessError as exc:
        steps[name] = {
            "status": "failed",
            "command": command,
            "outputs": outputs,
            "stdout": (exc.stdout or "")[-2000:],
            "stderr": (exc.stderr or "")[-4000:],
            "returncode": exc.returncode,
        }


def _write_summary(steps: dict[str, dict], smoke: bool) -> None:
    out = ROOT / "results" / "rl_mitigation" / "paper"
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "smoke": bool(smoke),
        "steps": steps,
        "main_result_dir": "results/rl_mitigation/paper",
        "diagnostics_are_not_paper_results": True,
    }
    (out / "rl_paper_reproduction_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# RL Paper Reproduction Report",
        "",
        f"Smoke run: `{smoke}`",
        "",
        "## Step Status",
        "",
        "| Step | Status | Outputs |",
        "|---|---|---|",
    ]
    for name, row in steps.items():
        lines.append(f"| {name} | {row['status']} | {'; '.join(row.get('outputs', []))} |")
    lines.extend([
        "",
        "## IEEE5",
        "",
        f"IEEE5 DP: `{steps.get('ieee5_dp', {}).get('status', 'not-run')}`",
        "",
        "## Figure 1",
        "",
        f"Cascade trace: `{steps.get('figure1_trace', {}).get('status', 'not-run')}`",
        "",
        "## IEEE14",
        "",
        f"Paper pipeline: `{steps.get('ieee14_paper_pipeline', {}).get('status', 'not-run')}`",
        f"Claim check: `{steps.get('ieee14_claim_check', {}).get('status', 'not-run')}`",
        "",
        "## IEEE118",
        "",
        f"Smoke framework: `{steps.get('ieee118_ppo', {}).get('status', 'not-run')}`",
        "",
        "## Formal Commands",
        "",
        "```powershell",
        "python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --steps 60000 --eval-episodes 1000",
        "python -m scripts.rl_mitigation.paper.train_ieee118_ppo --config configs/rl_mitigation/paper/ieee118_paper_ppo.yaml --steps 600000",
        "```",
        "",
        "## Thesis Wording",
        "",
        "Use paper reproduction results under `results/rl_mitigation/paper/` as the main RL reproduction package. Diagnostics and enhanced experiments are not original paper results.",
    ])
    failed = [name for name, row in steps.items() if row["status"] == "failed"]
    if failed:
        lines.extend(["", "## Failed Steps", ""])
        for name in failed:
            lines.append(f"- `{name}`: `{steps[name].get('stderr', '')[:500]}`")
    (out / "rl_paper_reproduction_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
