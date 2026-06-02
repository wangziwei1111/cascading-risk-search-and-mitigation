import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv


def test_env_reset_step_smoke():
    env = CascadeMitigationEnv(make_ieee14_case(), seed=3)
    obs, info = env.reset()
    assert len(obs) == 40
    assert "action_mask" in info
    obs, reward, done, truncated, info = env.step(0)
    assert len(obs) == 40
    assert isinstance(reward, float)
    assert isinstance(done, bool)
    assert truncated is False
    assert "cascade_trace" in info
