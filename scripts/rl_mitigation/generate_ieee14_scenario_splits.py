from __future__ import annotations

import argparse
import json

from ._common import ROOT, load_config, make_ieee14_env_from_config
from rl_mitigation.evaluation.scenario_split import SPLIT_SEEDS, load_or_create_scenario_split


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee14_ppo.yaml")
    parser.add_argument("--train", type=int, default=300)
    parser.add_argument("--val", type=int, default=100)
    parser.add_argument("--test", type=int, default=100)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_ieee14_env_from_config(cfg)
    out_dir = ROOT / "results" / "rl_mitigation" / "ieee14" / "scenarios"
    counts = {"train": args.train, "val": args.val, "test": args.test}
    manifest = {"splits": {}}
    for split, episodes in counts.items():
        scenarios, path = load_or_create_scenario_split(env, out_dir, split, episodes, SPLIT_SEEDS[split], force=args.force)
        manifest["splits"][split] = {
            "path": str(path.relative_to(ROOT)),
            "episodes": len(scenarios),
            "seed": SPLIT_SEEDS[split],
        }
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "scenario_splits_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"Scenario splits written to {out_dir}")


if __name__ == "__main__":
    main()
