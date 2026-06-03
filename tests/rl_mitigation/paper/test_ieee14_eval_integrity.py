import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from scripts.rl_mitigation.paper.check_ieee14_eval_integrity import check_rows


def test_eval_integrity_detects_missing_policy():
    rows = [
        {
            "scenario_id": "0",
            "policy": "do_nothing",
            "initial_outages": "0",
            "initial_outage_type": "N-1",
            "chronic_index": "1",
            "load_scale": "1.0",
            "gen_scale": "1.0",
            "negative_return": "1",
            "num_generations": "1",
            "num_line_outages": "1",
            "load_shed_MW": "0",
            "pf_failed": "False",
            "num_invalid_actions": "0",
            "num_proactive_actions": "0",
        }
    ]
    result = check_rows(rows)
    assert result["passed"] is False
    assert result["errors"][0]["type"] == "missing_policy"


def test_current_ieee14_eval_integrity_output_passes():
    path = Path("results/rl_mitigation/paper/ieee14/reports/ieee14_eval_integrity_check.json")
    assert path.exists()

