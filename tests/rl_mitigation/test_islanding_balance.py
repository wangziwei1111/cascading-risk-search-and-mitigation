import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from rl_mitigation.envs.islanding import approximate_load_after_outages
from rl_mitigation.envs.islanding import build_island_records


def test_load_decreases_with_outages():
    full = approximate_load_after_outages(100.0, np.array([1, 1, 1, 1]))
    partial = approximate_load_after_outages(100.0, np.array([1, 0, 0, 1]))
    assert full == 100.0
    assert partial < full


def test_no_generation_island_sheds_all_load():
    case = {
        "num_buses": 3,
        "num_lines": 1,
        "lines": [(0, 1)],
        "generators": [{"bus": 0, "pmax": 50.0}],
        "loads": [{"bus": 2, "p": 20.0}],
    }
    records = build_island_records(case, np.array([1], dtype=np.int8))
    load_island = next(record for record in records if record["buses"] == [2])
    assert load_island["load_after_mw"] == 0.0
    assert load_island["load_shed_mw"] == 20.0


def test_generation_deficit_sheds_proportionally():
    case = {
        "num_buses": 2,
        "num_lines": 1,
        "lines": [(0, 1)],
        "generators": [{"bus": 0, "pmax": 30.0}],
        "loads": [{"bus": 1, "p": 50.0}],
    }
    record = build_island_records(case, np.array([1], dtype=np.int8))[0]
    assert record["load_after_mw"] == 30.0
    assert record["load_shed_mw"] == 20.0


def test_generation_surplus_down_regulates_generation():
    case = {
        "num_buses": 2,
        "num_lines": 1,
        "lines": [(0, 1)],
        "generators": [{"bus": 0, "pmax": 80.0}],
        "loads": [{"bus": 1, "p": 50.0}],
    }
    record = build_island_records(case, np.array([1], dtype=np.int8))[0]
    assert record["load_after_mw"] == 50.0
    assert record["gen_after_mw"] == 50.0
