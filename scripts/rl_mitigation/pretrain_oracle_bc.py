from __future__ import annotations

import argparse
import csv

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.scenarios import load_scenarios
from rl_mitigation.rl.pretrain_oracle_bc import pretrain_oracle_bc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    args = parser.parse_args()
    cfg = load_config(args.config)
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    scenarios = load_scenarios(str(base / "eval" / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{args.episodes}.json"))
    with open(base / "action_value_scan" / f"action_value_scan_{args.episodes}.csv", newline="", encoding="utf-8") as f:
        scan_rows = list(csv.DictReader(f))
    diagnostics = pretrain_oracle_bc(
        make_ieee14_env_from_config(cfg),
        scenarios,
        scan_rows,
        str(base / "pretrain"),
        min_improvement=cfg.get("oracle_bc", {}).get("min_improvement", 1.0),
        epochs=cfg.get("oracle_bc", {}).get("epochs", 20),
        entropy_coef=cfg.get("oracle_bc", {}).get("entropy_coef", 0.01),
        seed=cfg.get("seed", 0),
    )
    print(f"Oracle BC diagnostics: {diagnostics}")


if __name__ == "__main__":
    main()
