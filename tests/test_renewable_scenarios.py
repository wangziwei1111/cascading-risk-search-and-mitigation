from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from pypower.idx_bus import PD
from pypower.idx_gen import PG


REPO_ROOT = Path(__file__).resolve().parents[1]
LEGACY_DIR = REPO_ROOT / "src" / "gcn_search" / "legacy_rts79"
if str(LEGACY_DIR) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR))

from renewable_scenarios import RenewableScenarioConfig, apply_renewable_scenario_to_case, summarize_renewable_case
from rts79_cascade import Rts79InitialConfig, copy_case, run_initial_dcopf


def test_renewable_scenario_is_reproducible_and_non_destructive() -> None:
    base = run_initial_dcopf(Rts79InitialConfig(random_seed=20260722)).case
    before = copy_case(base)
    config = RenewableScenarioConfig(random_seed=1234, renewable_penetration_ratio=0.2)

    first = apply_renewable_scenario_to_case(base, config)
    second = apply_renewable_scenario_to_case(base, config)

    assert np.allclose(first["bus"][:, PD], second["bus"][:, PD])
    assert np.allclose(first["gen"][:, PG], second["gen"][:, PG])
    assert np.allclose(base["bus"][:, PD], before["bus"][:, PD])
    assert np.allclose(base["gen"][:, PG], before["gen"][:, PG])


def test_renewable_scenario_summary_is_finite_and_explains_changes() -> None:
    base = run_initial_dcopf(Rts79InitialConfig(random_seed=20260723)).case
    config = RenewableScenarioConfig(random_seed=20260723, renewable_penetration_ratio=0.3)
    after = apply_renewable_scenario_to_case(base, config)
    summary = summarize_renewable_case(base, after, config)

    assert summary["synthetic_renewable"] is True
    assert summary["renewable_penetration_ratio"] == 0.3
    assert np.isfinite(after["bus"]).all()
    assert np.isfinite(after["gen"]).all()
    assert np.isfinite(summary["total_load_mw_after"])
    assert np.isfinite(summary["total_generation_mw_after"])
    assert summary["renewable_output_mw"] > 0
