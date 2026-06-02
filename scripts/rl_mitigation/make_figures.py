from __future__ import annotations

import argparse
import csv
import json

import matplotlib.pyplot as plt
import numpy as np
import yaml

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.evaluation.survival import survival_by_policy
from rl_mitigation.plotting.plot_learning_curves import plot_learning_curve
from rl_mitigation.plotting.plot_survival import plot_survival_by_policy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="ieee14")
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    args = parser.parse_args()
    with open(ROOT / args.config, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    figures = base / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    train_csv = base / "train_logs" / "ppo_clip_train.csv"
    plot_learning_curve(str(train_csv), str(figures / "fig_ieee14_learning_curve_smoke.png"), str(figures / "fig_ieee14_learning_curve_smoke.pdf"))
    _copy_learning_data(train_csv, figures / "fig_ieee14_learning_curve_smoke.csv")
    _plot_gridsearch_curves(base / "gridsearch_logs", figures)

    eval_csv = base / "eval" / "eval_before_after_100.csv"
    if not eval_csv.exists():
        eval_csv = base / "eval" / "eval_10_smoke.csv"
    rows = _read_csv(eval_csv) if eval_csv.exists() else []
    plot_survival_by_policy(
        rows,
        str(figures / "fig_ieee14_survival_negative_return_100.png"),
        str(figures / "fig_ieee14_survival_negative_return_100.pdf"),
        yscale=cfg.get("figures", {}).get("survival_yscale", "linear"),
    )
    _write_survival_data(rows, figures / "fig_ieee14_survival_negative_return_100.csv")
    _plot_action_improvement(base, figures)
    _plot_oracle_survival(base, figures, cfg)
    _plot_policy_action_probability(base, figures)
    _plot_training_ablation(base, figures)
    _plot_test_policy_survival(base, figures, cfg)
    _plot_improvable_subset(base, figures)
    _plot_oracle_gap_vs_ppo_gap(base, figures)
    _plot_bc_full_vs_positive_only(base, figures)
    _plot_safe_gate_threshold_tuning(base, figures)
    _plot_safe_policy_survival(base, figures, cfg)
    _plot_policy_multimetric_summary(base, figures)
    _write_captions(figures)
    print(f"Figures written to {figures}")


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _copy_learning_data(src, dst):
    if not src.exists():
        return
    rows = _read_csv(src)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["step", "episode_return", "negative_return"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"step": row.get("step", 0), "episode_return": row.get("episode_return", 0), "negative_return": row.get("negative_return", 0)})


def _write_survival_data(rows, dst):
    survival_rows = survival_by_policy(rows)
    with open(dst, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["policy", "negative_return", "survival_probability"])
        writer.writeheader()
        writer.writerows(survival_rows)


def _plot_gridsearch_curves(log_dir, figures):
    files = sorted(log_dir.glob("lr_*_ent_*.csv"))
    if not files:
        return
    combined_rows = []
    plt.figure(figsize=(7, 4.5), facecolor="white")
    for path in files:
        rows = _read_csv(path)
        steps = [float(row["step"]) for row in rows]
        returns = [float(row["episode_return"]) for row in rows]
        if not steps:
            continue
        smooth = _ema(returns, alpha=0.2)
        label = path.stem.replace("lr_", "lr=").replace("_ent_", ", ent=")
        plt.plot(steps, smooth, label=label, linewidth=1.2)
        for step, value in zip(steps, smooth):
            combined_rows.append({"setting": label, "step": step, "smoothed_episode_return": value})
    plt.xlabel("Training step")
    plt.ylabel("EMA episode return (smoke)")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(figures / "fig7_learning_curves_gridsearch.png", dpi=200)
    plt.savefig(figures / "fig7_learning_curves_gridsearch.pdf")
    plt.close()
    with open(figures / "fig7_learning_curves_gridsearch.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["setting", "step", "smoothed_episode_return"])
        writer.writeheader()
        writer.writerows(combined_rows)


def _ema(values, alpha=0.2):
    out = []
    cur = None
    for value in values:
        cur = value if cur is None else alpha * value + (1.0 - alpha) * cur
        out.append(cur)
    return out


def _plot_action_improvement(base, figures):
    summary = base / "action_value_scan" / "test_action_value_summary.json"
    if not summary.exists():
        summary = base / "action_value_scan" / "action_value_summary.json"
    if not summary.exists():
        return
    with open(summary, encoding="utf-8") as f:
        data = json.load(f)
    vals = [float(row["improvement"]) for row in data.get("scenario_improvements", [])]
    if not vals:
        return
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.hist(vals, bins=20)
    plt.xlabel("Best action improvement over do-nothing")
    plt.ylabel("Scenario count")
    plt.tight_layout()
    plt.savefig(figures / "fig_action_improvement_distribution.png", dpi=200)
    plt.savefig(figures / "fig_action_improvement_distribution.pdf")
    plt.close()
    with open(figures / "fig_action_improvement_distribution.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario_id", "improvement", "best_action", "do_nothing_negative_return", "best_negative_return"])
        writer.writeheader()
        writer.writerows(data.get("scenario_improvements", []))


def _plot_oracle_survival(base, figures, cfg):
    matches = sorted((base / "eval").glob("*eval_do_nothing_agent_oracle*.csv"))
    if not matches:
        return
    rows = _read_csv(matches[-1])
    plot_survival_by_policy(
        rows,
        str(figures / "fig_oracle_vs_do_nothing_vs_agent_survival.png"),
        str(figures / "fig_oracle_vs_do_nothing_vs_agent_survival.pdf"),
        yscale=cfg.get("figures", {}).get("survival_yscale", "linear"),
    )
    _write_survival_data(rows, figures / "fig_oracle_vs_do_nothing_vs_agent_survival.csv")


def _plot_policy_action_probability(base, figures):
    diag_csv = base / "diagnostics" / "policy_action_diagnostics.csv"
    if not diag_csv.exists():
        return
    rows = _read_csv(diag_csv)
    if not rows:
        return
    xs = list(range(len(rows)))
    do_nothing = [float(row["prob_do_nothing"]) for row in rows]
    nonzero = [float(row["max_nonzero_action_prob"]) for row in rows]
    plt.figure(figsize=(6, 4), facecolor="white")
    plt.plot(xs, do_nothing, label="P(do-nothing)", linewidth=1.4)
    plt.plot(xs, nonzero, label="max P(nonzero action)", linewidth=1.4)
    plt.xlabel("Scenario index")
    plt.ylabel("Action probability")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figures / "fig_policy_action_probability.png", dpi=200)
    plt.savefig(figures / "fig_policy_action_probability.pdf")
    plt.close()
    with open(figures / "fig_policy_action_probability.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["scenario_id", "prob_do_nothing", "max_nonzero_action_prob", "entropy", "argmax_action"])
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in ["scenario_id", "prob_do_nothing", "max_nonzero_action_prob", "entropy", "argmax_action"]})


def _plot_training_ablation(base, figures):
    path = base / "ablation" / "training_ablation_summary.csv"
    if not path.exists():
        return
    rows = [row for row in _read_csv(path) if row["eval_mode"] == "deterministic"]
    if not rows:
        return
    labels = [row["variant"].replace("ppo_", "").replace("_init", "") for row in rows]
    values = [float(row["mean_negative_return"]) for row in rows]
    plt.figure(figsize=(7, 4), facecolor="white")
    plt.bar(labels, values)
    plt.ylabel("Mean negative return")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(figures / "fig_training_ablation_negative_return.png", dpi=200)
    plt.savefig(figures / "fig_training_ablation_negative_return.pdf")
    plt.close()
    _write_csv(rows, figures / "fig_training_ablation_negative_return.csv")


def _plot_test_policy_survival(base, figures, cfg):
    rows = []
    for path in sorted((base / "eval").glob("test_eval_*.csv")):
        if "stochastic" in path.name or "before_after" in path.name or "do_nothing_agent_oracle" in path.name:
            continue
        rows.extend(_read_csv(path))
    if not rows:
        return
    plot_survival_by_policy(
        rows,
        str(figures / "fig_policy_survival_test_split.png"),
        str(figures / "fig_policy_survival_test_split.pdf"),
        yscale=cfg.get("figures", {}).get("survival_yscale", "linear"),
    )
    _write_survival_data(rows, figures / "fig_policy_survival_test_split.csv")


def _plot_improvable_subset(base, figures):
    path = base / "analysis" / "improvable_subset_summary.csv"
    if not path.exists():
        return
    rows = [row for row in _read_csv(path) if row["subset"] == "improvable"]
    if not rows:
        return
    plt.figure(figsize=(7, 4), facecolor="white")
    plt.bar([row["policy"] for row in rows], [float(row["mean_negative_return"]) for row in rows])
    plt.ylabel("Mean negative return")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(figures / "fig_improvable_subset_bar.png", dpi=200)
    plt.savefig(figures / "fig_improvable_subset_bar.pdf")
    plt.close()
    _write_csv(rows, figures / "fig_improvable_subset_bar.csv")


def _plot_oracle_gap_vs_ppo_gap(base, figures):
    summary_path = base / "action_value_scan" / "test_action_value_summary.json"
    ppo_path = base / "eval" / "test_eval_ppo_oracle_bc_init_deterministic.csv"
    dn_path = base / "eval" / "test_eval_do_nothing.csv"
    if not (summary_path.exists() and ppo_path.exists() and dn_path.exists()):
        return
    with open(summary_path, encoding="utf-8") as f:
        action_summary = json.load(f)
    oracle_gap = {str(row["scenario_id"]): float(row["improvement"]) for row in action_summary.get("scenario_improvements", [])}
    ppo = {str(row["scenario_id"]): row for row in _read_csv(ppo_path)}
    dn = {str(row["scenario_id"]): row for row in _read_csv(dn_path)}
    points = []
    for sid in sorted(set(ppo) & set(dn) & set(oracle_gap)):
        points.append({
            "scenario_id": sid,
            "oracle_improvement": oracle_gap[sid],
            "ppo_improvement": float(dn[sid]["negative_return"]) - float(ppo[sid]["negative_return"]),
        })
    if not points:
        return
    plt.figure(figsize=(5, 5), facecolor="white")
    plt.scatter([p["oracle_improvement"] for p in points], [p["ppo_improvement"] for p in points], s=18)
    plt.xlabel("One-step oracle improvement")
    plt.ylabel("PPO oracle-BC init improvement")
    plt.tight_layout()
    plt.savefig(figures / "fig_oracle_gap_vs_ppo_gap.png", dpi=200)
    plt.savefig(figures / "fig_oracle_gap_vs_ppo_gap.pdf")
    plt.close()
    _write_csv(points, figures / "fig_oracle_gap_vs_ppo_gap.csv")


def _plot_bc_full_vs_positive_only(base, figures):
    path = base / "analysis" / "improvable_subset_summary.csv"
    if not path.exists():
        return
    rows = [row for row in _read_csv(path) if row["policy"] in {"oracle_bc_positive_only", "oracle_bc_full"} and row["subset"] in {"improvable", "non_improvable"}]
    if not rows:
        return
    labels = [f"{row['policy']}:{row['subset']}" for row in rows]
    values = [float(row["mean_negative_return"]) for row in rows]
    plt.figure(figsize=(8, 4), facecolor="white")
    plt.bar(labels, values)
    plt.ylabel("Mean negative return")
    plt.xticks(rotation=25, ha="right")
    plt.tight_layout()
    plt.savefig(figures / "fig_bc_full_vs_positive_only.png", dpi=200)
    plt.savefig(figures / "fig_bc_full_vs_positive_only.pdf")
    plt.close()
    _write_csv(rows, figures / "fig_bc_full_vs_positive_only.csv")


def _plot_safe_gate_threshold_tuning(base, figures):
    path = base / "ablation" / "safe_policy_threshold_tuning.csv"
    selected_path = base / "ablation" / "safe_policy_threshold_selected.json"
    if not path.exists():
        return
    rows = _read_csv(path)
    labels = [f"{row['active_prob_threshold']}/{row['margin_threshold']}" for row in rows]
    values = [float(row["mean_negative_return"]) for row in rows]
    plt.figure(figsize=(8, 4), facecolor="white")
    plt.plot(range(len(values)), values, marker="o", linewidth=1.2)
    if selected_path.exists():
        with open(selected_path, encoding="utf-8") as f:
            selected = json.load(f)
        selected_label = f"{selected['active_prob_threshold']}/{selected['margin_threshold']}"
        if selected_label in labels:
            idx = labels.index(selected_label)
            plt.scatter([idx], [values[idx]], color="red", zorder=3, label="selected")
            plt.legend()
    plt.xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=7)
    plt.ylabel("Val mean negative return")
    plt.tight_layout()
    plt.savefig(figures / "fig_safe_gate_threshold_tuning.png", dpi=200)
    plt.savefig(figures / "fig_safe_gate_threshold_tuning.pdf")
    plt.close()
    _write_csv(rows, figures / "fig_safe_gate_threshold_tuning.csv")


def _plot_safe_policy_survival(base, figures, cfg):
    rows = []
    keep = {"do_nothing", "one_step_oracle", "oracle_bc_full", "safe_oracle_bc_full"}
    for path in sorted((base / "eval").glob("test_eval_*.csv")):
        if "stochastic" in path.name or "do_nothing_agent_oracle" in path.name:
            continue
        cur = [row for row in _read_csv(path) if row["policy"] in keep]
        rows.extend(cur)
    if not rows:
        return
    plot_survival_by_policy(
        rows,
        str(figures / "fig_safe_policy_test_survival.png"),
        str(figures / "fig_safe_policy_test_survival.pdf"),
        yscale=cfg.get("figures", {}).get("survival_yscale", "linear"),
    )
    _write_survival_data(rows, figures / "fig_safe_policy_test_survival.csv")


def _plot_policy_multimetric_summary(base, figures):
    path = base / "tables" / "table_policy_multi_metric_test_summary.csv"
    if not path.exists():
        return
    rows = _read_csv(path)
    if not rows:
        return
    metrics = ["mean_negative_return", "pf_failed_ratio", "mean_num_line_outages", "mean_load_shed_MW", "mean_num_proactive_actions"]
    policies = [row["policy"] for row in rows]
    x = np.arange(len(policies))
    plt.figure(figsize=(9, 4.8), facecolor="white")
    for metric in metrics:
        vals = np.asarray([float(row[metric]) for row in rows], dtype=float)
        denom = max(vals.max() - vals.min(), 1e-9)
        norm = (vals - vals.min()) / denom
        plt.plot(x, norm, marker="o", linewidth=1.1, label=metric)
    plt.xticks(x, policies, rotation=25, ha="right", fontsize=7)
    plt.ylabel("Normalized metric")
    plt.legend(fontsize=7)
    plt.tight_layout()
    plt.savefig(figures / "fig_policy_multimetric_summary.png", dpi=200)
    plt.savefig(figures / "fig_policy_multimetric_summary.pdf")
    plt.close()
    _write_csv(rows, figures / "fig_policy_multimetric_summary.csv")


def _write_csv(rows, path):
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_captions(figures):
    (figures / "figure_caption_suggestions_zh.md").write_text(
        "# 中文图名建议\n\n"
        "- 图：IEEE14 小系统 PPO 训练回报曲线，smoke 训练，EMA 平滑。\n"
        "- 图：IEEE14 小系统 PPO 超参数网格搜索训练回报曲线，smoke 训练，EMA 平滑。\n"
        "- 图：IEEE14 小系统 do-nothing 与 PPO agent 负回报生存函数对比。\n"
        "- 图：IEEE14 小系统单步主动断线动作相对 do-nothing 的改善分布。\n"
        "- 图：IEEE14 小系统 do-nothing、PPO agent 与 one-step oracle 负回报生存函数对比。\n"
        "- 图：IEEE14 小系统策略初始动作概率诊断。\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
