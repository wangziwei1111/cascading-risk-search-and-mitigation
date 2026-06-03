import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.rl.paper_do_nothing_pretrain import pretrain_paper_do_nothing_actor


def test_paper_do_nothing_pretrain_writes_diagnostics(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), initial_outage_mode="fixed", fixed_initial_outages=[0], max_generations=1)
    _, diagnostics = pretrain_paper_do_nothing_actor(env, str(tmp_path), n_states=8, epochs=1, seed=0)
    assert (tmp_path / "policy_pretrained_torch.pt").exists()
    assert (tmp_path / "pretrain_diagnostics.json").exists()
    assert "mean_prob_do_nothing" in diagnostics["after"]

