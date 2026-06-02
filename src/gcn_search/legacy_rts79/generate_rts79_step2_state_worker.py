from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from generate_rts79_step2_state_dataset import Step2StateDatasetConfig, _generate_one_scenario_checkpoint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a disjoint RTS-79 Step2-State checkpoint shard.")
    parser.add_argument("--output-dir", required=True, help="Shared dataset output directory.")
    parser.add_argument("--num-scenarios", type=int, required=True, help="Number of scenarios in this shard.")
    parser.add_argument("--first-seed", type=int, required=True, help="First random seed in this shard.")
    parser.add_argument("--scenario-id-offset", type=int, required=True, help="Checkpoint scenario id offset.")
    parser.add_argument("--max-active-depth", type=int, default=1)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = Step2StateDatasetConfig(
        num_scenarios=args.num_scenarios,
        first_seed=args.first_seed,
        scenario_id_offset=args.scenario_id_offset,
        max_active_depth=args.max_active_depth,
        relay_threshold_beta=args.beta,
        security_limit=args.security_limit,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = out / "scenario_checkpoints"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    config_path = out / f"rts79_step2_state_worker_config_{args.scenario_id_offset + 1:04d}.json"
    config_path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")

    for scenario_offset in range(config.num_scenarios):
        scenario_id = config.scenario_id_offset + scenario_offset + 1
        seed = config.first_seed + scenario_offset
        checkpoint_path = checkpoint_dir / f"scenario_{scenario_id:04d}_step2_state_raw.npz"
        if checkpoint_path.exists():
            print(f"[worker] scenario={scenario_id} seed={seed} done, skip.", flush=True)
            continue
        checkpoint = _generate_one_scenario_checkpoint(scenario_id, seed, config)
        np.savez(checkpoint_path, **checkpoint)
        print(f"[worker] saved scenario={scenario_id} seed={seed}: {checkpoint_path}", flush=True)


if __name__ == "__main__":
    main()
