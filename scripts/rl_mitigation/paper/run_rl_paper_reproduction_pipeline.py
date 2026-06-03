from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from ._common import ROOT, MODE_DEFAULTS, mode_suffix, normalize_mode, rel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    parser.add_argument("--run-ieee5", action="store_true")
    parser.add_argument("--run-ieee14", action="store_true")
    parser.add_argument("--run-ieee118", action="store_true")
    parser.add_argument("--ieee14-steps", type=int)
    parser.add_argument("--ieee118-steps", type=int)
    parser.add_argument("--eval-episodes", type=int)
    args = parser.parse_args()
    mode = normalize_mode(args.mode, args.smoke)
    defaults = MODE_DEFAULTS[mode]
    ieee14_steps = args.ieee14_steps or defaults["steps"]
    ieee118_steps = args.ieee118_steps or (2048 if mode in {"smoke", "medium"} else MODE_DEFAULTS["formal"]["steps"])
    eval_episodes = args.eval_episodes or defaults["eval_episodes"]
    run_all = not (args.run_ieee5 or args.run_ieee14 or args.run_ieee118)
    steps: dict[str, dict] = {}
    suffix = mode_suffix(mode)

    if run_all or args.run_ieee5:
        _step(steps, "ieee5_dp", ["scripts.rl_mitigation.paper.run_ieee5_dp", "--config", "configs/rl_mitigation/paper/ieee5_dp.yaml"], ["results/rl_mitigation/paper/ieee5/ieee5_dp_report.md"])
        _step(steps, "figure1_trace", ["scripts.rl_mitigation.paper.check_figure1_cascade_flow", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml"], ["results/rl_mitigation/paper/figure1_trace/ieee14_example_trace.md"])

    if run_all or args.run_ieee14:
        eval_csv = f"results/rl_mitigation/paper/ieee14/eval/eval_{eval_episodes}_before_after{suffix}.csv"
        _step(steps, "ieee14_paper_pipeline", ["scripts.rl_mitigation.paper.run_ieee14_paper_pipeline", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml", "--mode", mode, "--steps", str(ieee14_steps), "--eval-episodes", str(eval_episodes)], [f"results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_report{suffix}.md"])
        _step(steps, "ieee14_gridsearch", ["scripts.rl_mitigation.paper.train_ieee14_gridsearch", "--config", "configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml", "--mode", mode, "--steps", str(defaults["gridsearch_steps"])], [f"results/rl_mitigation/paper/ieee14/figures/fig7_ieee14_learning_curves_gridsearch{suffix}.png"])
        _step(steps, "ieee14_eval_integrity", ["scripts.rl_mitigation.paper.check_ieee14_eval_integrity", "--eval-csv", eval_csv, "--suffix", mode], [f"results/rl_mitigation/paper/ieee14/reports/ieee14_eval_integrity_check{suffix}.json"])
        _step(steps, "ieee14_claim_check", ["scripts.rl_mitigation.paper.check_ieee14_paper_claims", "--eval-csv", eval_csv, "--suffix", mode, "--checkpoint", f"results/rl_mitigation/paper/ieee14/checkpoints/proposed_pretrain_mask{suffix}/latest.pt", "--train-log", f"results/rl_mitigation/paper/ieee14/train_logs/proposed_pretrain_mask{suffix}.csv"], [f"results/rl_mitigation/paper/ieee14/reports/ieee14_claim_check{suffix}.json", f"results/rl_mitigation/paper/ieee14/tables/table_ieee14_claim_metrics{suffix}.csv"])
        _step(steps, "ieee14_mask_pretrain_ablation", ["scripts.rl_mitigation.paper.compare_ieee14_mask_pretrain_ablation", "--config", "configs/rl_mitigation/paper/ieee14_paper_ppo.yaml", "--mode", mode, "--steps", str(defaults["ablation_steps"]), "--eval-episodes", str(defaults["ablation_eval_episodes"])], [f"results/rl_mitigation/paper/ieee14/ablation/mask_pretrain_ablation{suffix}.csv"])

    if run_all or args.run_ieee118:
        _step(steps, "ieee118_pretrain", ["scripts.rl_mitigation.paper.pretrain_do_nothing_ieee118", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--states", "16"], ["results/rl_mitigation/paper/ieee118/pretrain/pretrain_diagnostics.json"])
        _step(steps, "ieee118_ppo", ["scripts.rl_mitigation.paper.train_ieee118_ppo", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--smoke", "--steps", str(ieee118_steps)], ["results/rl_mitigation/paper/ieee118/train_logs/proposed_pretrain_mask_smoke.csv"])
        _step(steps, "ieee118_eval", ["scripts.rl_mitigation.paper.evaluate_ieee118_paper_policy", "--config", "configs/rl_mitigation/paper/ieee118_paper_ppo.yaml", "--smoke", "--episodes", "20"], ["results/rl_mitigation/paper/ieee118/eval/eval_20_before_after_smoke.csv"])
        _step(steps, "ieee118_figures", ["scripts.rl_mitigation.paper.make_ieee118_paper_figures", "--smoke"], ["results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png"])

    _write_summary(steps, mode=mode)


def _step(steps: dict[str, dict], name: str, command: list[str], outputs: list[str]) -> None:
    try:
        completed = subprocess.run([sys.executable, "-m", *command], check=True, capture_output=True, text=True)
        steps[name] = {"status": "completed", "command": command, "outputs": outputs, "stdout_or_summary": _sanitize(completed.stdout[-2000:])}
    except subprocess.CalledProcessError as exc:
        steps[name] = {
            "status": "failed",
            "command": command,
            "outputs": outputs,
            "stdout_or_summary": _sanitize((exc.stdout or "")[-2000:]),
            "error_if_failed": _sanitize((exc.stderr or "")[-4000:]),
            "returncode": exc.returncode,
        }


def _sanitize(text: str) -> str:
    return (text or "").replace(str(ROOT), ".").replace(str(ROOT).replace("\\", "/"), ".")


def _write_summary(steps: dict[str, dict], mode: str) -> None:
    out = ROOT / "results" / "rl_mitigation" / "paper"
    out.mkdir(parents=True, exist_ok=True)
    suffix = mode_suffix(mode)
    claim_path = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "reports" / f"ieee14_claim_check{suffix}.json"
    claim = json.loads(claim_path.read_text(encoding="utf-8")) if claim_path.exists() else {}
    figure_status = {
        "figure7": rel(ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "figures" / f"fig7_ieee14_learning_curves_gridsearch{suffix}.png"),
        "figure8": rel(ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "figures" / f"fig8_ieee14_negative_return_survival{suffix}.png"),
        "ieee118_fig9_smoke": "results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png",
    }
    summary = {
        "smoke_or_mode": mode,
        "steps": steps,
        "main_result_dir": "results/rl_mitigation/paper",
        "diagnostics_are_not_paper_results": True,
        "claim_check_overall": claim.get("overall"),
        "source_eval_csv": claim.get("source_eval_csv"),
        "figure_status": figure_status,
    }
    summary_name = f"rl_paper_reproduction_summary{suffix}.json" if mode != "smoke" else "rl_paper_reproduction_summary.json"
    report_name = f"rl_paper_reproduction_report{suffix}.md" if mode != "smoke" else "rl_paper_reproduction_report.md"
    (out / summary_name).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# RL Paper Reproduction Report",
        "",
        f"Mode: `{mode}`",
        f"IEEE14 claim check: `{summary['claim_check_overall']}`",
        f"Source eval CSV: `{summary['source_eval_csv']}`",
        "",
        "| Step | Status | Outputs |",
        "|---|---|---|",
    ]
    for name, row in steps.items():
        lines.append(f"| {name} | {row['status']} | {'; '.join(row.get('outputs', []))} |")
    lines.extend([
        "",
        "## Formal Commands",
        "",
        "```powershell",
        "python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --mode formal",
        "python -m scripts.rl_mitigation.paper.train_ieee14_gridsearch --config configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml --mode formal",
        "python -m scripts.rl_mitigation.paper.train_ieee118_ppo --config configs/rl_mitigation/paper/ieee118_paper_ppo.yaml --steps 600000",
        "```",
        "",
        "Diagnostics and enhanced experiments are not paper reproduction results.",
    ])
    failed = [name for name, row in steps.items() if row["status"] == "failed"]
    if failed:
        lines.extend(["", "## Failed Steps", ""])
        for name in failed:
            lines.append(f"- `{name}`: `{steps[name].get('error_if_failed', '')[:500]}`")
    (out / report_name).write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
