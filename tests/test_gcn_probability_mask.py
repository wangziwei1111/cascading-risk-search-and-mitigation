import sys
from pathlib import Path

import numpy as np
import torch

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from gcn_physics_constraints import apply_candidate_probability_mask, make_candidate_mask
from pypower.idx_brch import BR_STATUS
from rts79_cascade import load_rts79_case


def test_probability_mask_single_and_batch_without_inplace_change():
    prob = np.array([0.1, 0.2, 0.3])
    original = prob.copy()
    mask = np.array([True, False, True])
    masked = apply_candidate_probability_mask(prob, mask)
    assert np.allclose(prob, original)
    assert np.allclose(masked, [0.1, 0.0, 0.3])

    batch = torch.tensor([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
    masked_batch = apply_candidate_probability_mask(batch, torch.tensor(mask))
    assert torch.allclose(batch, torch.tensor([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]))
    assert torch.allclose(masked_batch[:, 1], torch.zeros(2))


def test_candidate_mask_excludes_offline_and_used_lines():
    case = load_rts79_case()
    case["branch"][0, BR_STATUS] = 0
    mask = make_candidate_mask(case, used_lines=["L02"])
    assert not mask[0]
    assert not mask[1]
    assert mask[2]
