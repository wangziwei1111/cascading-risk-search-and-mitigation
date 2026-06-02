import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.action_value import scan_scenario_actions
from rl_mitigation.evaluation.scenarios import generate_eval_scenarios
from rl_mitigation.rl.pretrain_oracle_bc import pretrain_oracle_bc


def test_oracle_bc_full_dataset_contains_all_scenarios_and_do_nothing_negatives(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), seed=5, backend="pypower_ac", initial_outage_mode="sampled")
    scenarios = generate_eval_scenarios(env, episodes=3, seed=5)
    scan_rows = []
    for scenario in scenarios:
        scan_rows.extend(scan_scenario_actions(env, scenario))
    diagnostics = pretrain_oracle_bc(env, scenarios, scan_rows, str(tmp_path), min_improvement=999.0, epochs=1, mode="full")
    with open(tmp_path / "oracle_bc_full_dataset.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(scenarios)
    assert diagnostics["num_non_improvable"] == len(scenarios)
    assert {row["label_action"] for row in rows} == {"0"}
    assert {row["label_type"] for row in rows} == {"do_nothing"}
