from __future__ import annotations

import argparse
import json

from ._common import load_config, resolve_path
from gcn_search.ieee14.rl_bridge import summarize_policy_on_gcn_subset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gcn_search/ieee14/ieee14_gcn.yaml")
    parser.add_argument("--top-k", type=int)
    args = parser.parse_args()
    cfg = load_config(args.config)
    eval_cfg = cfg["evaluation"]
    summaries = summarize_policy_on_gcn_subset(
        ranking_csv=resolve_path(eval_cfg["output_dir"]) / "test_risk_ranking.csv",
        rl_eval_dir=resolve_path(eval_cfg["rl_eval_dir"]),
        policy_files=eval_cfg["policies"],
        output_dir=resolve_path(eval_cfg["rl_bridge_dir"]),
        top_k=args.top_k or eval_cfg.get("top_k", 20),
    )
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()

