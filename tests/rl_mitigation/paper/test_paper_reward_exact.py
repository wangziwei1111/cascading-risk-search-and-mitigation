import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rl_mitigation.envs.reward import cascade_reward, cascade_reward_terms


def test_generation_zero_initial_faults_do_not_count_in_reward():
    assert cascade_reward(
        terminal=False,
        pf_failed=True,
        alpha=0.1,
        action=1,
        num_new_outages=5,
        previous_load=100.0,
        current_load=0.0,
        generation=0,
    ) == 0.0


def test_reward_terms_can_be_triggered_individually():
    terms = cascade_reward_terms(
        terminal=False,
        pf_failed=True,
        alpha=0.1,
        action=3,
        num_new_outages=2,
        previous_load=100.0,
        current_load=80.0,
        generation=1,
    )
    assert terms["nonterminal_penalty"] == -1.0
    assert terms["pf_failure_penalty"] == -100.0
    assert terms["proactive_action_penalty"] == -0.1
    assert math.isclose(terms["new_outage_penalty"], -100.0 * (1.0 - math.exp(-0.02)))
    assert terms["load_shed_penalty"] == -0.2
    assert math.isclose(sum(terms.values()), cascade_reward(
        terminal=False,
        pf_failed=True,
        alpha=0.1,
        action=3,
        num_new_outages=2,
        previous_load=100.0,
        current_load=80.0,
        generation=1,
    ))


def test_powerflow_failure_reward_contains_minus_100():
    terms = cascade_reward_terms(
        terminal=True,
        pf_failed=True,
        alpha=0.1,
        action=0,
        num_new_outages=0,
        previous_load=100.0,
        current_load=100.0,
        generation=1,
    )
    assert terms["pf_failure_penalty"] == -100.0

