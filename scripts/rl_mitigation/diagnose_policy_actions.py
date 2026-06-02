from __future__ import annotations

import argparse
import csv
import json
from collections import Counter

import numpy as np

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios, load_scenarios, save_scenarios
from rl_mitigation.rl.ppo_clip import load_checkpoint
from rl_mitigation.rl.torch_networks import TorchActorCritic, torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    scenario_path = ROOT / "results" / "rl_mitigation" / "ieee14" / "eval" / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{args.episodes}.json"
    scenarios = load_scenarios(str(scenario_path)) if scenario_path.exists() else generate_eval_scenarios(env, args.episodes, cfg.get("seed", 0))
    save_scenarios(scenarios, str(scenario_path))
    ckpt = ROOT / "results" / "rl_mitigation" / "ieee14" / "checkpoints" / "latest.pt"
    model = load_checkpoint(str(ckpt)) if ckpt.exists() else TorchActorCritic(env.observation_space_shape[0], env.action_space_n)
    rows = [_diagnose_one(env, model, scenario) for scenario in scenarios[:args.episodes]]
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "diagnostics"
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "policy_action_diagnostics.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = _summary(rows)
    with open(out_dir / "policy_action_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    _write_report(out_dir / "policy_diagnosis_report.md", summary)
    print(f"Policy diagnostics written to {out_dir}; argmax_do_nothing_ratio={summary['argmax_do_nothing_ratio']:.3f}")


def _diagnose_one(env, model, scenario):
    obs, info = env.reset(seed=int(scenario["seed"]), options={"scenario": scenario})
    mask = info["action_mask"]
    with torch.no_grad():
        logits = model.masked_logits(
            torch.tensor(obs, dtype=torch.float32).unsqueeze(0),
            torch.tensor(mask, dtype=torch.bool).unsqueeze(0),
        )[0]
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
    order = np.argsort(-probs)[:3]
    nonzero = probs[1:]
    entropy = -float(np.sum(probs * np.log(probs + 1e-12)))
    argmax_action = int(order[0])
    return {
        "scenario_id": scenario["scenario_id"],
        "initial_outages": ",".join(str(x) for x in scenario["initial_outages"]),
        "initial_outage_type": scenario["initial_outage_type"],
        "valid_action_count": int(mask.sum()),
        "argmax_action": argmax_action,
        "argmax_action_type": "do_nothing" if argmax_action == 0 else "open_line",
        "prob_do_nothing": float(probs[0]),
        "max_nonzero_action_prob": float(nonzero.max()) if len(nonzero) else 0.0,
        "entropy": entropy,
        "top1_action": int(order[0]),
        "top1_prob": float(probs[order[0]]),
        "top2_action": int(order[1]),
        "top2_prob": float(probs[order[1]]),
        "top3_action": int(order[2]),
        "top3_prob": float(probs[order[2]]),
    }


def _summary(rows):
    probs = [float(r["prob_do_nothing"]) for r in rows]
    ent = [float(r["entropy"]) for r in rows]
    argmax_dn = [int(r["argmax_action"]) == 0 for r in rows]
    nonzero_actions = [int(r["argmax_action"]) for r in rows if int(r["argmax_action"]) != 0]
    return {
        "mean_prob_do_nothing": float(np.mean(probs)),
        "median_prob_do_nothing": float(np.median(probs)),
        "mean_entropy": float(np.mean(ent)),
        "argmax_do_nothing_ratio": float(np.mean(argmax_dn)),
        "nonzero_action_argmax_ratio": 1.0 - float(np.mean(argmax_dn)),
        "top_nonzero_actions_frequency": dict(Counter(nonzero_actions).most_common(10)),
    }


def _write_report(path, summary):
    conclusion = "策略明显坍缩到 do-nothing。" if summary["argmax_do_nothing_ratio"] > 0.9 else "策略存在非零主动动作偏好。"
    path.write_text(
        "# Policy Diagnosis Report\n\n"
        f"- mean_prob_do_nothing: {summary['mean_prob_do_nothing']:.4f}\n"
        f"- median_prob_do_nothing: {summary['median_prob_do_nothing']:.4f}\n"
        f"- mean_entropy: {summary['mean_entropy']:.4f}\n"
        f"- argmax_do_nothing_ratio: {summary['argmax_do_nothing_ratio']:.4f}\n\n"
        f"结论：{conclusion}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
