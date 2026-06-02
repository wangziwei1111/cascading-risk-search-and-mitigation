from __future__ import annotations

import argparse
import csv
from pathlib import Path

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.scenarios import load_scenarios
from rl_mitigation.rl.pretrain_oracle_bc import pretrain_oracle_bc


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--scenario-file")
    parser.add_argument("--scan-file")
    args = parser.parse_args()
    cfg = load_config(args.config)
    base = ROOT / "results" / "rl_mitigation" / "ieee14"
    oracle_cfg = cfg.get("oracle_bc", {})
    scenario_file = _resolve(args.scenario_file or oracle_cfg.get("train_scenarios", base / "eval" / f"eval_scenarios_seed{cfg.get('seed', 0)}_episodes{args.episodes}.json"))
    scan_file = _resolve(args.scan_file or oracle_cfg.get("train_split_scan", base / "action_value_scan" / f"action_value_scan_{args.episodes}.csv"))
    if "test_" in scenario_file.name or "test_" in scan_file.name:
        raise SystemExit("Oracle BC must not use test split scenarios or scans.")
    scenarios = load_scenarios(str(scenario_file))
    with open(scan_file, newline="", encoding="utf-8") as f:
        scan_rows = list(csv.DictReader(f))
    diagnostics = pretrain_oracle_bc(
        make_ieee14_env_from_config(cfg),
        scenarios,
        scan_rows,
        str(base / "pretrain"),
        min_improvement=oracle_cfg.get("min_improvement", 1.0),
        epochs=oracle_cfg.get("epochs", 20),
        entropy_coef=oracle_cfg.get("entropy_coef", 0.01),
        learning_rate=oracle_cfg.get("learning_rate", 1e-3),
        seed=cfg.get("seed", 0),
    )
    print(f"Oracle BC diagnostics: {diagnostics}")


def _resolve(path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


if __name__ == "__main__":
    main()
