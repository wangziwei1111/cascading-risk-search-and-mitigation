import json
import sys
from pathlib import Path

import numpy as np
import pytest
from pypower.idx_brch import BR_STATUS, PF
from pypower.idx_bus import PD

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from online_state_update import apply_measured_state_to_case, load_measured_state_json, make_online_gcn_input
from rts79_cascade import load_rts79_case


def test_online_state_json_updates_case_without_inplace_modification(tmp_path):
    path = tmp_path / "measured.json"
    path.write_text(
        json.dumps(
            {
                "branch_status": {"L01": 0},
                "branch_flow_mw": {"L02": 12.5},
                "bus_load_mw": {"3": 123.0},
                "generator_output_mw": {"1": 80.0},
            }
        ),
        encoding="utf-8",
    )
    measured = load_measured_state_json(path)
    case = load_rts79_case()
    original_status = case["branch"][0, BR_STATUS]
    updated = apply_measured_state_to_case(case, measured)
    assert case["branch"][0, BR_STATUS] == original_status
    assert updated["branch"][0, BR_STATUS] == 0
    assert updated["branch"][1, PF] == 12.5
    assert np.any(updated["bus"][:, PD] == 123.0)
    x = make_online_gcn_input(case, measured, feature_mode="physics")
    assert x.shape == (38, 9)
    assert np.isfinite(x).all()


def test_online_state_rejects_invalid_inputs(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"branch_status": {"L99": 0}}), encoding="utf-8")
    measured = load_measured_state_json(path)
    with pytest.raises(ValueError):
        apply_measured_state_to_case(load_rts79_case(), measured)

    path.write_text(json.dumps({"branch_status": {"L01": 3}}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_measured_state_json(path)
