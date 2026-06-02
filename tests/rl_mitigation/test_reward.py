import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.envs.reward import cascade_reward


def test_reward_terms_ordering():
    terminal = cascade_reward(terminal=True, pf_failed=False, alpha=0.1, action=0, num_new_outages=0, previous_load=100, current_load=100, generation=1)
    continuing = cascade_reward(terminal=False, pf_failed=False, alpha=0.1, action=0, num_new_outages=0, previous_load=100, current_load=100, generation=1)
    failed = cascade_reward(terminal=True, pf_failed=True, alpha=0.1, action=0, num_new_outages=0, previous_load=100, current_load=100, generation=1)
    proactive = cascade_reward(terminal=True, pf_failed=False, alpha=0.1, action=3, num_new_outages=0, previous_load=100, current_load=100, generation=1)
    more_outages = cascade_reward(terminal=True, pf_failed=False, alpha=0.1, action=0, num_new_outages=3, previous_load=100, current_load=100, generation=1)
    load_shed = cascade_reward(terminal=True, pf_failed=False, alpha=0.1, action=0, num_new_outages=0, previous_load=100, current_load=80, generation=1)
    assert terminal == 0
    assert continuing < terminal
    assert failed <= terminal - 100
    assert proactive < terminal
    assert more_outages < terminal
    assert load_shed < terminal
