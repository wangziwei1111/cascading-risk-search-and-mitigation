from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from pypower.idx_bus import BUS_I, PD
from pypower.idx_gen import GEN_BUS, PG, PMAX, PMIN

from rts79_cascade import Rts79InitialConfig, copy_case, run_initial_dcopf


@dataclass(frozen=True)
class RenewableScenarioConfig:
    renewable_penetration_ratio: float = 0.2
    renewable_buses: tuple[int, ...] = (3, 7, 16)
    renewable_generator_indices: tuple[int, ...] = ()
    fluctuation_low: float = 0.6
    fluctuation_high: float = 1.1
    random_seed: int = 20260722
    balance_mode: str = "scale_generation"
    description: str = "Synthetic RTS-79 renewable output perturbation; not a real renewable dynamic model."


def apply_renewable_scenario_to_case(case: dict, config: RenewableScenarioConfig) -> dict:
    if config.renewable_penetration_ratio < 0:
        raise ValueError("renewable_penetration_ratio must be non-negative")
    if config.fluctuation_low > config.fluctuation_high:
        raise ValueError("fluctuation_low must be <= fluctuation_high")
    updated = copy_case(case)
    bus = updated["bus"].copy()
    gen = updated["gen"].copy()
    rng = np.random.default_rng(config.random_seed)

    total_load = float(np.sum(bus[:, PD]))
    target_renewable = total_load * float(config.renewable_penetration_ratio)
    fluctuation = float(rng.uniform(config.fluctuation_low, config.fluctuation_high))
    renewable_output = target_renewable * fluctuation

    renewable_buses = tuple(int(b) for b in config.renewable_buses)
    gen_indices = tuple(int(i) for i in config.renewable_generator_indices)
    if gen_indices:
        share = renewable_output / max(len(gen_indices), 1)
        for idx in gen_indices:
            gen[idx, PG] = max(float(gen[idx, PMIN]), min(float(gen[idx, PMAX]), share))
    elif renewable_buses:
        share = renewable_output / max(len(renewable_buses), 1)
        for bus_id in renewable_buses:
            row = np.where(bus[:, BUS_I].astype(int) == bus_id)[0]
            if len(row):
                bus[row[0], PD] = max(0.0, float(bus[row[0], PD]) - share)
    else:
        raise ValueError("Either renewable_buses or renewable_generator_indices must be provided")

    updated["bus"] = bus
    updated["gen"] = gen
    if config.balance_mode == "scale_generation":
        updated = _scale_online_generation_to_load(updated)
    elif config.balance_mode == "scale_load":
        updated = _scale_load_to_generation(updated)
    elif config.balance_mode == "none":
        pass
    else:
        raise ValueError(f"Unsupported balance_mode: {config.balance_mode}")
    updated["renewable_summary"] = {
        **asdict(config),
        "target_renewable_mw": target_renewable,
        "fluctuation_factor": fluctuation,
        "renewable_output_mw": renewable_output,
        "total_load_mw_before_balance": total_load,
        "total_load_mw_after_balance": float(np.sum(updated["bus"][:, PD])),
        "total_generation_mw_after_balance": float(np.sum(updated["gen"][:, PG])),
        "synthetic_renewable": True,
    }
    return updated


def make_renewable_rts79_initial_config(seed: int, renewable_config: RenewableScenarioConfig) -> dict:
    base_state = run_initial_dcopf(Rts79InitialConfig(random_seed=seed))
    scenario_config = RenewableScenarioConfig(
        **{**asdict(renewable_config), "random_seed": renewable_config.random_seed if renewable_config.random_seed is not None else seed}
    )
    return apply_renewable_scenario_to_case(base_state.case, scenario_config)


def summarize_renewable_case(case_before: dict, case_after: dict, config: RenewableScenarioConfig) -> dict:
    summary = dict(case_after.get("renewable_summary", {}))
    summary.update(
        {
            "total_load_mw_before": float(np.sum(case_before["bus"][:, PD])),
            "total_load_mw_after": float(np.sum(case_after["bus"][:, PD])),
            "total_generation_mw_before": float(np.sum(case_before["gen"][:, PG])),
            "total_generation_mw_after": float(np.sum(case_after["gen"][:, PG])),
            "net_injection_change_mw": float(
                (np.sum(case_after["gen"][:, PG]) - np.sum(case_after["bus"][:, PD]))
                - (np.sum(case_before["gen"][:, PG]) - np.sum(case_before["bus"][:, PD]))
            ),
            "config": asdict(config),
        }
    )
    return summary


def load_renewable_config_json(path: str | Path) -> RenewableScenarioConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("renewable_buses", "renewable_generator_indices"):
        if key in data and isinstance(data[key], list):
            data[key] = tuple(data[key])
    return RenewableScenarioConfig(**data)


def _scale_online_generation_to_load(case: dict) -> dict:
    updated = copy_case(case)
    gen = updated["gen"].copy()
    total_load = float(np.sum(updated["bus"][:, PD]))
    current_pg = float(np.sum(gen[:, PG]))
    if current_pg > 1e-9:
        gen[:, PG] *= total_load / current_pg
        gen[:, PG] = np.minimum(np.maximum(gen[:, PG], gen[:, PMIN]), gen[:, PMAX])
    updated["gen"] = gen
    return updated


def _scale_load_to_generation(case: dict) -> dict:
    updated = copy_case(case)
    bus = updated["bus"].copy()
    total_generation = float(np.sum(updated["gen"][:, PG]))
    total_load = float(np.sum(bus[:, PD]))
    if total_load > 1e-9:
        bus[:, PD] *= total_generation / total_load
    updated["bus"] = bus
    return updated
