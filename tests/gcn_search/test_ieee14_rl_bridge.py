import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from gcn_search.ieee14.rl_bridge import summarize_policy_on_gcn_subset


def test_rl_bridge_summarizes_gcn_topk_subset(tmp_path):
    ranking = tmp_path / "test_risk_ranking.csv"
    _write_csv(
        ranking,
        ["rank", "scenario_id", "gcn_score", "true_do_nothing_negative_return", "best_improvement", "initial_outages"],
        [
            {"rank": 1, "scenario_id": 2, "gcn_score": 0.9, "true_do_nothing_negative_return": 10, "best_improvement": 1, "initial_outages": "0,1"},
            {"rank": 2, "scenario_id": 1, "gcn_score": 0.7, "true_do_nothing_negative_return": 5, "best_improvement": 0, "initial_outages": "2"},
        ],
    )
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir()
    _write_csv(
        eval_dir / "policy.csv",
        ["scenario_id", "negative_return", "num_line_outages", "load_shed_MW", "pf_failed"],
        [
            {"scenario_id": 1, "negative_return": 5, "num_line_outages": 2, "load_shed_MW": 0, "pf_failed": "False"},
            {"scenario_id": 2, "negative_return": 10, "num_line_outages": 4, "load_shed_MW": 3, "pf_failed": "True"},
        ],
    )
    summaries = summarize_policy_on_gcn_subset(
        ranking_csv=ranking,
        rl_eval_dir=eval_dir,
        policy_files={"demo": "policy.csv"},
        output_dir=tmp_path / "bridge",
        top_k=1,
    )
    assert summaries[0]["subset"] == "all_test"
    assert summaries[0]["mean_negative_return"] == 7.5
    assert summaries[1]["subset"] == "gcn_top_1"
    assert summaries[1]["mean_negative_return"] == 10.0
    assert (tmp_path / "bridge" / "gcn_rl_bridge_report.md").exists()


def _write_csv(path, fields, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

