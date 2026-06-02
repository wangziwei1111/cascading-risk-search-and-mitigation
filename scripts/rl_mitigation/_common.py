from __future__ import annotations

import yaml

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.contingency.sampler import ContingencySampler
from rl_mitigation.envs import CascadeMitigationEnv


def load_config(path: str) -> dict:
    with open(ROOT / path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_ieee14_env_from_config(cfg: dict, seed: int | None = None) -> CascadeMitigationEnv:
    case = make_ieee14_case()
    initial_cfg = cfg.get("initial_outages", {})
    sampler = ContingencySampler(
        case,
        seed=cfg.get("seed", 0) if seed is None else seed,
        include_n_minus_1=initial_cfg.get("include_n_minus_1", True),
        include_common_bus_n_minus_2=initial_cfg.get("include_common_bus_n_minus_2", True),
    )
    return CascadeMitigationEnv(
        case,
        seed=cfg.get("seed", 0) if seed is None else seed,
        alpha=cfg.get("alpha", 0.1),
        max_generations=cfg.get("max_generations", 10),
        use_action_mask=cfg.get("ppo", {}).get("use_action_mask", True),
        backend=cfg.get("backend", cfg.get("powerflow", {}).get("backend", "pypower_ac")),
        powerflow_config=cfg.get("powerflow", {}),
        initial_outage_mode=initial_cfg.get("mode", "sampled"),
        fixed_initial_outages=initial_cfg.get("fixed", []),
        contingency_sampler=sampler,
    )
