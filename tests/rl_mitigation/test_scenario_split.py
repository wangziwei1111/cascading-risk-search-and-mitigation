import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.cases import make_ieee14_case
from rl_mitigation.envs import CascadeMitigationEnv
from rl_mitigation.evaluation.scenario_split import load_or_create_scenario_split


def test_scenario_split_is_saved_and_reused(tmp_path):
    env = CascadeMitigationEnv(make_ieee14_case(), seed=0, backend="pypower_ac", initial_outage_mode="sampled")
    first, path = load_or_create_scenario_split(env, tmp_path, "train", 3, seed=0)
    second, _ = load_or_create_scenario_split(env, tmp_path, "train", 3, seed=0)
    assert path.exists()
    assert first == second
    assert {row["split"] for row in first} == {"train"}
    assert {"scenario_id", "split", "seed", "chronic_index", "load_scale", "gen_scale", "initial_outages", "initial_outage_type", "initial_outage_order"} <= set(first[0])
