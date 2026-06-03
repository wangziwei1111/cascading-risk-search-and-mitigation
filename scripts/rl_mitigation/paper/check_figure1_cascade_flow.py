from __future__ import annotations

import argparse

from ._common import ROOT, load_config, make_paper_env
from rl_mitigation.envs.paper_cascade_trace import paper_trace_from_env, save_paper_trace


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee14_paper_ppo.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    env = make_paper_env(cfg)
    obs, info = env.reset(seed=cfg.get("seed", 0))
    done = False
    while not done:
        obs, reward, done, _, info = env.step(0)
    out = ROOT / "results" / "rl_mitigation" / "paper" / "figure1_trace"
    trace = paper_trace_from_env(env, policy_name="do_nothing")
    save_paper_trace(trace, out / "ieee14_example_trace.json", out / "ieee14_example_trace.md")
    print(f"Figure 1 trace written to {out}")


if __name__ == "__main__":
    main()

