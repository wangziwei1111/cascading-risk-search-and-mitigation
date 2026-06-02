from __future__ import annotations

from pathlib import Path

from .scenarios import generate_eval_scenarios, load_scenarios, save_scenarios


SPLIT_SEEDS = {"train": 0, "val": 1, "test": 2}


def scenario_split_path(base_dir: str | Path, split: str, episodes: int, seed: int | None = None) -> Path:
    seed_value = SPLIT_SEEDS[split] if seed is None else seed
    return Path(base_dir) / f"{split}_scenarios_seed{seed_value}_episodes{episodes}.json"


def generate_scenario_split(env, split: str, episodes: int, seed: int) -> list[dict]:
    scenarios = generate_eval_scenarios(env, episodes=episodes, seed=seed)
    for scenario in scenarios:
        scenario["split"] = split
    return scenarios


def load_or_create_scenario_split(
    env,
    base_dir: str | Path,
    split: str,
    episodes: int,
    seed: int | None = None,
    force: bool = False,
) -> tuple[list[dict], Path]:
    seed_value = SPLIT_SEEDS[split] if seed is None else seed
    path = scenario_split_path(base_dir, split, episodes, seed_value)
    if path.exists() and not force:
        return load_scenarios(str(path)), path
    scenarios = generate_scenario_split(env, split, episodes, seed_value)
    save_scenarios(scenarios, str(path))
    return scenarios, path


def infer_split_from_scenario_file(path: str | Path) -> str:
    name = Path(path).name
    for split in SPLIT_SEEDS:
        if name.startswith(f"{split}_"):
            return split
    return "custom"
