from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from rl_mitigation.cases import make_ieee14_case, make_ieee118_case, make_ieee5_case
from rl_mitigation.chronics.generate_week_chronics import generate_week_chronics
from rl_mitigation.contingency.sampler import ContingencySampler
from rl_mitigation.envs import CascadeMitigationEnv


def load_config(path: str | Path) -> dict:
    cur = Path(path)
    if not cur.is_absolute():
        cur = ROOT / cur
    with open(cur, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve(path: str | Path) -> Path:
    cur = Path(path)
    return cur if cur.is_absolute() else ROOT / cur


def make_case(name: str) -> dict:
    if name == "ieee5":
        return make_ieee5_case()
    if name == "ieee14":
        return make_ieee14_case()
    if name == "ieee118":
        return make_ieee118_case()
    raise ValueError(f"Unsupported paper case: {name}")


def make_paper_env(cfg: dict, seed: int | None = None) -> CascadeMitigationEnv:
    case = make_case(cfg.get("case", "ieee14"))
    initial_cfg = cfg.get("initial_outages", {})
    include_n1 = initial_cfg.get("include_n_minus_1", True)
    include_n2 = initial_cfg.get("include_common_bus_n_minus_2", True)
    sampler = ContingencySampler(case, seed=cfg.get("seed", 0) if seed is None else seed, include_n_minus_1=include_n1, include_common_bus_n_minus_2=include_n2)
    chronics_cfg = cfg.get("chronics", {})
    days = chronics_cfg.get("days", 7)
    resolution = chronics_cfg.get("resolution_minutes", 5)
    num_steps = int(days * 24 * 60 / max(1, resolution))
    chronics = generate_week_chronics(
        num_steps=num_steps,
        seed=cfg.get("seed", 0) if seed is None else seed,
    )
    return CascadeMitigationEnv(
        case,
        seed=cfg.get("seed", 0) if seed is None else seed,
        alpha=cfg.get("alpha", 0.1),
        max_generations=cfg.get("max_generations", 10),
        use_action_mask=cfg.get("ppo", {}).get("use_action_mask", True),
        backend=cfg.get("backend", "pypower_ac"),
        powerflow_config=cfg.get("powerflow", {}),
        chronics=chronics,
        initial_outage_mode=initial_cfg.get("mode", "sampled"),
        fixed_initial_outages=initial_cfg.get("fixed", []),
        contingency_sampler=sampler,
    )
