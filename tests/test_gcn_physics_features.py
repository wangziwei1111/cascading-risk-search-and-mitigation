import sys
from pathlib import Path

import numpy as np

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from pypower.idx_brch import BR_STATUS
from rts79_cascade import load_rts79_case
from train_rts79_paper_gcn import _make_x_gcn, _make_x_gcn_physics, _x_gcn_physics_feature_names


def test_physics_features_have_expected_shape_and_values():
    case = load_rts79_case()
    x_paper = _make_x_gcn(case, 1.2)
    x_physics = _make_x_gcn_physics(case, 1.2, security_limit=1.0)
    assert x_paper.shape == (38, 4)
    assert x_physics.shape[0] == 38
    assert x_physics.shape[1] == len(_x_gcn_physics_feature_names())
    assert x_physics.shape[1] > 4
    assert np.isfinite(x_physics).all()
    for idx in (0, 7, 8):
        assert set(np.unique(x_physics[:, idx])).issubset({0.0, 1.0})


def test_offline_branch_updates_online_candidate_features():
    case = load_rts79_case()
    case["branch"][0, BR_STATUS] = 0
    x = _make_x_gcn_physics(case, 1.2, security_limit=1.0)
    assert x[0, 0] == 1.0
    assert x[0, 7] == 0.0
    assert x[0, 8] == 0.0
