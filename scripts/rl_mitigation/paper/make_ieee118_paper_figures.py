from __future__ import annotations

import argparse
import csv

import matplotlib.pyplot as plt

from ._common import ROOT
from rl_mitigation.plotting.plot_survival import plot_survival_by_policy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee118"
    figs = base / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    _plot_learning(base, figs, args.smoke)
    eval_files = sorted((base / "eval").glob("eval_*_before_after*.csv"))
    rows = _read(eval_files[-1]) if eval_files else []
    if rows:
        plot_survival_by_policy(rows, str(figs / "fig10_ieee118_negative_return_survival.png"), str(figs / "fig10_ieee118_negative_return_survival.pdf"))
        _metric_survival(rows, figs / "fig11a_ieee118_generations_survival.png", "num_generations")
        _metric_survival(rows, figs / "fig11b_ieee118_line_outages_survival.png", "num_line_outages")
        _metric_survival(rows, figs / "fig11c_ieee118_load_shed_survival.png", "load_shed_MW")
        _action_frequency(rows, figs / "fig12_ieee118_action_frequency.png")
    print(f"IEEE118 paper figure interfaces written to {figs}")


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _plot_learning(base, figs, smoke):
    files = sorted((base / "train_logs").glob("*.csv"))
    plt.figure(figsize=(7, 4), facecolor="white")
    for path in files:
        rows = _read(path)
        if rows:
            plt.plot([float(r["step"]) for r in rows], [float(r["episode_return"]) for r in rows], label=path.stem)
    plt.xlabel("Training steps")
    plt.ylabel("Episode return")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(figs / "fig9_ieee118_learning_curve_pretrain_mask_vs_baseline.png", dpi=200)
    plt.savefig(figs / "fig9_ieee118_learning_curve_pretrain_mask_vs_baseline.pdf")
    plt.close()


def _metric_survival(rows, out_png, key):
    vals = sorted(float(r[key]) for r in rows)
    if not vals:
        return
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.step(vals, [1.0 - i / len(vals) for i in range(len(vals))], where="post")
    plt.xlabel(key)
    plt.ylabel("P(value > x)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.savefig(out_png.with_suffix(".pdf"))
    plt.close()


def _action_frequency(rows, out_png):
    counts = {}
    for row in rows:
        counts[row.get("num_proactive_actions", "0")] = counts.get(row.get("num_proactive_actions", "0"), 0) + 1
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.bar(list(counts), list(counts.values()))
    plt.xlabel("Number of proactive actions")
    plt.ylabel("Episode count")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.savefig(out_png.with_suffix(".pdf"))
    plt.close()


if __name__ == "__main__":
    main()

