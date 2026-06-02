import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.action_value import scan_scenario_actions
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.pretrain_oracle_bc import pretrain_oracle_bc


def test_oracle_bc_writes_requested_diagnostics(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), seed=4, backend="pypower_ac", initial_outage_mode="sampled")
    scenarios = generate_eval_scenarios(env, episodes=2, seed=4)
    scan_rows = []
    for scenario in scenarios:
        scan_rows.extend(scan_scenario_actions(env, scenario))
    diagnostics = pretrain_oracle_bc(env, scenarios, scan_rows, str(tmp_path), min_improvement=0.0, epochs=1)
    assert (tmp_path / "oracle_bc_policy.pt").exists()
    assert (tmp_path / "oracle_bc_full_policy.pt").exists()
    assert (tmp_path / "oracle_bc_full_dataset.csv").exists()
    assert (tmp_path / "oracle_bc_diagnostics.json").exists()
    assert {"num_train_scenarios", "num_bc_samples", "action_distribution", "mean_train_improvement", "mean_prob_best_action_after_bc", "mean_entropy_after_bc", "mean_prob_do_nothing_on_non_improvable"} <= set(diagnostics)
