from __future__ import annotations

import numpy as np

from .backend_factory import make_backend
from .observations import build_observation
from .reward import cascade_reward, cascade_reward_terms
from ..chronics.generate_week_chronics import generate_week_chronics
from ..contingency.sampler import ContingencySampler
from ..rl.action_mask import action_mask, apply_invalid_action_policy


class CascadeMitigationEnv:
    """Gymnasium-compatible cascade mitigation environment."""

    metadata = {"render_modes": ["text"]}

    def __init__(
        self,
        case: dict,
        initial_outages: list[int] | None = None,
        alpha: float = 0.1,
        max_generations: int = 10,
        seed: int | None = 0,
        use_action_mask: bool = False,
        backend: str = "pypower_ac",
        chronics: dict[str, np.ndarray] | None = None,
        powerflow_config: dict | None = None,
        initial_outage_mode: str = "sampled",
        contingency_sampler: ContingencySampler | None = None,
        fixed_initial_outages: list[int] | None = None,
    ):
        self.case = case
        self.num_lines = int(case["num_lines"])
        self.initial_outage_mode = initial_outage_mode
        self.fixed_initial_outages = list(
            fixed_initial_outages
            if fixed_initial_outages is not None
            else initial_outages
            if initial_outages is not None
            else case.get("initial_outages", [])
        )
        self.initial_outages = list(self.fixed_initial_outages)
        self.alpha = float(alpha)
        self.max_generations = int(max_generations)
        self.use_action_mask = bool(use_action_mask)
        self.backend_name = backend
        self.rng = np.random.default_rng(seed)
        self.backend = make_backend(backend, case, seed=seed or 0, powerflow_config=powerflow_config)
        self.contingency_sampler = contingency_sampler or ContingencySampler(case, seed=seed or 0)
        self.chronics = chronics if chronics is not None else generate_week_chronics(seed=seed or 0)
        self.episode_return = 0.0
        self.num_proactive_actions = 0
        self.num_invalid_actions = 0
        self.reset(seed=seed)

    @property
    def action_space_n(self) -> int:
        return self.num_lines + 1

    @property
    def observation_space_shape(self) -> tuple[int]:
        return (2 * self.num_lines,)

    def reset(self, seed: int | None = None, options: dict | None = None):
        if seed is not None:
            self.rng = np.random.default_rng(seed)
        self.generation = 0
        self.done = False
        self.trace: list[dict] = []
        self.episode_return = 0.0
        self.num_proactive_actions = 0
        self.num_invalid_actions = 0
        scenario = (options or {}).get("scenario") if options else None
        self.line_status = np.ones(self.num_lines, dtype=np.int8)
        self._select_initial_outages(scenario)
        for idx in self.initial_outages:
            if 0 <= idx < self.num_lines:
                self.line_status[idx] = 0
        self.load_scale, self.gen_scale = self._sample_chronic_scales(scenario)
        self.last_pf = self._solve()
        self.relative_flow = self.last_pf.relative_flow
        self.current_load = self.last_pf.current_load_mw
        info = self._info(pf_failed=not self.last_pf.converged)
        return build_observation(self.line_status, self.relative_flow), info

    def get_action_mask(self) -> np.ndarray:
        return action_mask(self.line_status)

    def step(self, action: int):
        if self.done:
            return build_observation(self.line_status, self.relative_flow), 0.0, True, False, self._info(pf_failed=False)
        previous_load = self.current_load
        effective_action, invalid = apply_invalid_action_policy(int(action), self.line_status, self.use_action_mask)
        if invalid:
            self.num_invalid_actions += 1
        proactive_line = None
        if effective_action > 0:
            proactive_line = effective_action - 1
            self.line_status[proactive_line] = 0
            self.num_proactive_actions += 1

        before_trip_pf = self._solve()
        overloaded = [
            int(i)
            for i, rho in enumerate(before_trip_pf.relative_flow)
            if self.line_status[i] and rho >= 1.0
        ]
        trip_probabilities = {
            int(idx): float(self._trip_probability(float(before_trip_pf.relative_flow[idx])))
            for idx in overloaded
        }
        tripped = []
        if before_trip_pf.converged:
            for idx in overloaded:
                beta = trip_probabilities[int(idx)]
                if self.rng.random() < beta:
                    self.line_status[idx] = 0
                    tripped.append(idx)

        self.generation += 1
        after_trip_pf = self._solve()
        self.last_pf = after_trip_pf
        self.relative_flow = after_trip_pf.relative_flow
        self.current_load = after_trip_pf.current_load_mw
        pf_failed = not (before_trip_pf.converged and after_trip_pf.converged)
        terminal = pf_failed or len(tripped) == 0 or self.generation >= self.max_generations
        self.done = terminal
        reward = cascade_reward(
            terminal=terminal,
            pf_failed=pf_failed,
            alpha=self.alpha,
            action=effective_action,
            num_new_outages=len(tripped),
            previous_load=previous_load,
            current_load=self.current_load,
            generation=self.generation,
        )
        reward_terms = cascade_reward_terms(
            terminal=terminal,
            pf_failed=pf_failed,
            alpha=self.alpha,
            action=effective_action,
            num_new_outages=len(tripped),
            previous_load=previous_load,
            current_load=self.current_load,
            generation=self.generation,
        )
        self.episode_return += float(reward)
        terminal_reason = "powerflow_failed" if pf_failed else "no_new_trips" if len(tripped) == 0 else "max_generations" if self.generation >= self.max_generations else "continuing"
        record = {
            "generation": self.generation,
            "initial_outages": self.initial_outages,
            "initial_outage_order": self.initial_outage_description["order"],
            "initial_outage_type": self.initial_outage_description["type"],
            "initial_outage_mode": self.initial_outage_mode,
            "action": int(action),
            "effective_action": int(effective_action),
            "action_valid": not bool(invalid),
            "outaged_lines": np.where(self.line_status == 0)[0].astype(int).tolist(),
            "proactive_action": proactive_line,
            "proactive_opened_line": proactive_line,
            "islands": after_trip_pf.island_records,
            "load_before": float(previous_load),
            "load_after": float(after_trip_pf.current_load_mw),
            "load_shed": float(after_trip_pf.load_shed_mw),
            "overloaded_lines": overloaded,
            "trip_probabilities": trip_probabilities,
            "random_trips": tripped,
            "random_tripped_lines": tripped,
            "newly_failed_lines": tripped,
            "pf_converged": not pf_failed,
            "relative_flow": after_trip_pf.relative_flow.astype(float).tolist(),
            "load_shed_MW": after_trip_pf.load_shed_mw,
            "load_shed_ratio": after_trip_pf.load_shed_ratio,
            "invalid_action": bool(invalid),
            "island_records": after_trip_pf.island_records,
            "terminal_reason": terminal_reason,
            "reward_terms": reward_terms,
            "reward": float(reward),
        }
        self.trace.append(record)
        return build_observation(self.line_status, self.relative_flow), reward, terminal, False, self._info(pf_failed=pf_failed)

    def render_cascade(self) -> str:
        return "\n".join(str(row) for row in self.trace)

    def _solve(self):
        if self.backend_name in {"surrogate", "debug", "dc_debug_surrogate"}:
            return self.backend.solve(self.line_status, generation=self.generation, load_scale=self.load_scale, gen_scale=self.gen_scale)
        return self.backend.solve(self.line_status, load_scale=self.load_scale, gen_scale=self.gen_scale)

    def _select_initial_outages(self, scenario: dict | None = None) -> None:
        if scenario is not None and "initial_outages" in scenario:
            self.initial_outages = [int(x) for x in scenario["initial_outages"]]
            self.initial_outage_mode = scenario.get("initial_outage_mode", self.initial_outage_mode)
        elif self.initial_outage_mode == "sampled":
            self.initial_outages = list(self.contingency_sampler.sample_one())
        elif self.initial_outage_mode == "fixed":
            self.initial_outages = list(self.fixed_initial_outages)
        elif self.initial_outage_mode == "none":
            self.initial_outages = []
        else:
            raise ValueError(f"Unknown initial_outage_mode: {self.initial_outage_mode}")
        self.initial_outage_description = self.contingency_sampler.describe(tuple(self.initial_outages)) if self.initial_outages else {
            "lines": [],
            "order": 0,
            "type": "none",
            "common_bus": None,
        }

    def _sample_chronic_scales(self, scenario: dict | None = None) -> tuple[float, float]:
        if scenario is not None and "load_scale" in scenario and "gen_scale" in scenario:
            self.chronic_index = int(scenario.get("chronic_index", -1))
            return float(scenario["load_scale"]), float(scenario["gen_scale"])
        if not self.chronics:
            self.chronic_index = -1
            return 1.0, 1.0
        n = len(self.chronics.get("load_scale", [1.0]))
        idx = int(self.rng.integers(0, max(1, n)))
        self.chronic_index = idx
        load_scale = float(self.chronics.get("load_scale", np.ones(n))[idx])
        gen_scale = float(self.chronics.get("gen_scale", np.ones(n))[idx])
        return load_scale, gen_scale

    @staticmethod
    def _trip_probability(rho: float) -> float:
        if rho >= 1.5:
            return 1.0
        if 1.0 <= rho < 1.5:
            return 2.0 * (rho - 1.0)
        return 0.0

    def _info(self, pf_failed: bool) -> dict:
        load_shed_mw = getattr(self.last_pf, "load_shed_mw", 0.0)
        load_shed_ratio = getattr(self.last_pf, "load_shed_ratio", 0.0)
        return {
            "episode_return": self.episode_return,
            "negative_return": -self.episode_return,
            "num_generations": self.generation,
            "num_line_outages": int((self.line_status == 0).sum()),
            "load_shed_MW": load_shed_mw,
            "load_shed_ratio": load_shed_ratio,
            "num_proactive_actions": self.num_proactive_actions,
            "num_invalid_actions": self.num_invalid_actions,
            "pf_failed": bool(pf_failed),
            "cascade_trace": self.trace,
            "action_mask": self.get_action_mask(),
            "backend": self.backend_name,
            "initial_outages": self.initial_outages,
            "initial_outage_order": self.initial_outage_description["order"],
            "initial_outage_type": self.initial_outage_description["type"],
            "initial_outage_mode": self.initial_outage_mode,
            "chronic_index": self.chronic_index,
            "load_scale": self.load_scale,
            "gen_scale": self.gen_scale,
            "island_count": getattr(self.last_pf, "island_count", 0),
            "island_records": getattr(self.last_pf, "island_records", []),
        }
