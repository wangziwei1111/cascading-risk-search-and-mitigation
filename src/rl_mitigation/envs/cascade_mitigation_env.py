from __future__ import annotations

import numpy as np

from .islanding import approximate_load_after_outages
from .observations import build_observation
from .powerflow_backend import SurrogatePowerFlowBackend
from .reward import cascade_reward
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
    ):
        self.case = case
        self.num_lines = int(case["num_lines"])
        self.initial_outages = list(initial_outages if initial_outages is not None else case.get("initial_outages", []))
        self.alpha = float(alpha)
        self.max_generations = int(max_generations)
        self.use_action_mask = bool(use_action_mask)
        self.rng = np.random.default_rng(seed)
        self.backend = SurrogatePowerFlowBackend(case["base_flows"], seed=seed or 0)
        self.base_load = float(sum(load["p"] for load in case.get("loads", [])) or 1.0)
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
        self.line_status = np.ones(self.num_lines, dtype=np.int8)
        for idx in self.initial_outages:
            if 0 <= idx < self.num_lines:
                self.line_status[idx] = 0
        self.current_load = approximate_load_after_outages(self.base_load, self.line_status)
        _, self.relative_flow = self.backend.solve(self.line_status, self.generation)
        self.done = False
        self.trace = []
        return build_observation(self.line_status, self.relative_flow), {"action_mask": self.get_action_mask()}

    def get_action_mask(self) -> np.ndarray:
        return action_mask(self.line_status)

    def step(self, action: int):
        if self.done:
            return build_observation(self.line_status, self.relative_flow), 0.0, True, False, {"cascade_trace": self.trace}
        previous_load = self.current_load
        effective_action, invalid = apply_invalid_action_policy(int(action), self.line_status, self.use_action_mask)
        proactive_line = None
        if effective_action > 0:
            proactive_line = effective_action - 1
            self.line_status[proactive_line] = 0
        converged, flows = self.backend.solve(self.line_status, self.generation)
        overloaded = [int(i) for i, rho in enumerate(flows) if self.line_status[i] and rho >= 1.0]
        tripped = []
        for idx in overloaded:
            rho = float(flows[idx])
            beta = 1.0 if rho >= 1.5 else max(0.0, 2.0 * (rho - 1.0))
            if self.rng.random() < beta:
                self.line_status[idx] = 0
                tripped.append(idx)
        self.generation += 1
        self.current_load = approximate_load_after_outages(self.base_load, self.line_status)
        converged_after, self.relative_flow = self.backend.solve(self.line_status, self.generation)
        pf_failed = not (converged and converged_after)
        terminal = pf_failed or not tripped or self.generation >= self.max_generations
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
        record = {
            "generation": self.generation,
            "outaged_lines": np.where(self.line_status == 0)[0].astype(int).tolist(),
            "proactive_action": proactive_line,
            "overloaded_lines": overloaded,
            "random_trips": tripped,
            "pf_converged": not pf_failed,
            "load_shed_MW": self.base_load - self.current_load,
            "invalid_action": bool(invalid),
        }
        self.trace.append(record)
        info = {
            "cascade_trace": self.trace,
            "num_generations": self.generation,
            "num_line_outages": int((self.line_status == 0).sum()),
            "load_shed_MW": self.base_load - self.current_load,
            "load_shed_ratio": (self.base_load - self.current_load) / self.base_load,
            "num_proactive_actions": sum(1 for row in self.trace if row["proactive_action"] is not None),
            "num_invalid_actions": sum(1 for row in self.trace if row["invalid_action"]),
            "pf_failed": pf_failed,
            "action_mask": self.get_action_mask(),
        }
        return build_observation(self.line_status, self.relative_flow), reward, terminal, False, info

    def render_cascade(self) -> str:
        return "\n".join(str(row) for row in self.trace)
