import sys
from pathlib import Path

import pytest

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from rts79_cascade import Rts79InitialConfig, run_initial_dcopf, simulate_cascade_path
from rts79_cascade_from_case import simulate_cascade_path_from_case


@pytest.mark.parametrize(
    "path",
    [
        ("L10", "L05"),
        ("L27", "L02"),
        ("L01", "L02"),
        ("L04", "L08"),
        ("L16", "L17"),
    ],
)
def test_simulate_cascade_path_from_case_matches_original_seed_case(path):
    config = Rts79InitialConfig(random_seed=20260722)
    root_case = run_initial_dcopf(config).case

    original = simulate_cascade_path(path, config=config, relay_threshold_beta=1.2, security_limit=1.0)
    from_case = simulate_cascade_path_from_case(root_case, path, beta=1.2, security_limit=1.0)

    assert from_case.critical == original.critical
    assert from_case.final_outage_labels == original.final_outage_labels
    assert from_case.total_load_shed_mw == pytest.approx(original.total_load_shed_mw, abs=1e-6)
    assert from_case.final_max_loading_ratio == pytest.approx(original.final_max_loading_ratio, abs=1e-6)
