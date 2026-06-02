import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.ppo_clip import train_ppo_clip
from rl_mitigation.rl.rollout_buffer import RolloutBuffer


def _buffer(done_last: bool):
    buf = RolloutBuffer()
    mask = np.ones(3, dtype=bool)
    buf.add([0.0], 0, 0.0, 1.0, False, 0.5, mask)
    buf.add([0.0], 0, 0.0, 1.0, done_last, 0.5, mask)
    return buf


def test_gae_no_bootstrap_when_episode_done():
    returns, adv = _buffer(True).compute_returns_advantages(gamma=1.0, gae_lambda=0.95, last_value=10.0, last_done=True)
    assert len(returns) == 2
    assert len(adv) == 2
    assert returns[-1] < 2.0


def test_gae_bootstraps_when_rollout_truncated():
    returns, adv = _buffer(False).compute_returns_advantages(gamma=1.0, gae_lambda=0.95, last_value=10.0, last_done=False)
    assert len(returns) == 2
    assert len(adv) == 2
    assert returns[-1] > 9.0


def test_ppo_smoke_still_runs_with_bootstrap(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), seed=8, backend="pypower_ac", use_action_mask=True)
    _, rows = train_ppo_clip(env, total_steps=64, n_steps=16, batch_size=16, epochs=1, log_path=str(tmp_path / "log.csv"), seed=8)
    assert rows
