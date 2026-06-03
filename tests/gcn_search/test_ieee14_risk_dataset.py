import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from gcn_search.ieee14.risk_dataset import build_split_dataset
from rl_mitigation.cases import make_ieee14_case


def test_build_split_dataset_from_same_system_action_scan(tmp_path):
    scan_path = tmp_path / "test_action_value_scan.csv"
    fields = [
        "scenario_id", "initial_outages", "initial_outage_type", "initial_outage_order",
        "chronic_index", "load_scale", "gen_scale", "action", "action_type", "action_line",
        "is_valid_action", "episode_return", "negative_return", "num_generations",
        "num_line_outages", "load_shed_MW", "load_shed_ratio", "num_proactive_actions",
        "num_invalid_actions", "pf_failed", "cascade_trace_json",
    ]
    rows = [
        _row(0, "0,2", 0, "", True, 100.0),
        _row(0, "0,2", 1, 4, True, 90.0),
        _row(1, "10", 0, "", True, 5.0),
        _row(1, "10", 2, 1, False, 6.0),
    ]
    with open(scan_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    dataset, scenario_rows = build_split_dataset(make_ieee14_case(), "test", scan_path)
    assert dataset.features.shape == (2, 20, 9)
    assert dataset.targets.shape == (2, 20)
    assert dataset.outage_masks[0, 0] == 1.0
    assert dataset.outage_masks[0, 2] == 1.0
    assert dataset.true_risk.tolist() == [100.0, 5.0]
    assert scenario_rows[0]["best_improvement"] == 10.0


def _row(scenario_id, outages, action, action_line, valid, negative_return):
    return {
        "scenario_id": scenario_id,
        "initial_outages": outages,
        "initial_outage_type": "common_bus_N-2",
        "initial_outage_order": len(outages.split(",")),
        "chronic_index": 0,
        "load_scale": 1.0,
        "gen_scale": 1.0,
        "action": action,
        "action_type": "do_nothing" if action == 0 else "open_line",
        "action_line": action_line,
        "is_valid_action": valid,
        "episode_return": -negative_return,
        "negative_return": negative_return,
        "num_generations": 1,
        "num_line_outages": 2,
        "load_shed_MW": 0.0,
        "load_shed_ratio": 0.0,
        "num_proactive_actions": 0 if action == 0 else 1,
        "num_invalid_actions": 0,
        "pf_failed": False,
        "cascade_trace_json": "[]",
    }

