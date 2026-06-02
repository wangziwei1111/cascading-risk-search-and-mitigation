import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.ppo_clip import load_checkpoint, train_ppo_clip


def test_ppo_clip_runs_512_steps_and_saves_checkpoint(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), seed=4, use_action_mask=True, backend="pypower_ac")
    log_path = tmp_path / "ppo_clip_train.csv"
    checkpoint_dir = tmp_path / "checkpoints"
    model, rows = train_ppo_clip(
        env,
        total_steps=512,
        n_steps=64,
        batch_size=64,
        epochs=1,
        log_path=str(log_path),
        checkpoint_dir=str(checkpoint_dir),
        seed=4,
    )
    assert rows
    assert log_path.exists()
    assert (checkpoint_dir / "latest.pt").exists()
    assert (checkpoint_dir / "best.pt").exists()
    reloaded = load_checkpoint(str(checkpoint_dir / "latest.pt"))
    assert reloaded.action_dim == model.action_dim
    assert all(row["num_invalid_actions"] == 0 for row in rows)
