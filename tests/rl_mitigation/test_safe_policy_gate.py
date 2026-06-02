import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.evaluation.safe_policy import safe_gate_action


def test_safe_gate_returns_do_nothing_when_probability_low():
    probs = np.array([0.30, 0.34, 0.10])
    assert safe_gate_action(probs, active_prob_threshold=0.35, margin_threshold=0.05) == 0


def test_safe_gate_returns_active_action_when_probability_and_margin_pass():
    probs = np.array([0.20, 0.10, 0.55])
    assert safe_gate_action(probs, active_prob_threshold=0.35, margin_threshold=0.05) == 2
