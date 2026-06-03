import csv
import json
import re
from pathlib import Path


KEY_METRICS = ["mean_negative_return", "mean_num_line_outages", "mean_load_shed_MW", "pf_failed_ratio"]


def test_ieee14_pipeline_report_claim_and_table_are_consistent():
    report_path = _latest("results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_report*.md")
    claim_path = _latest("results/rl_mitigation/paper/ieee14/reports/ieee14_claim_check*.json")
    table_path = _latest("results/rl_mitigation/paper/ieee14/tables/table_ieee14_claim_metrics*.csv")
    report = report_path.read_text(encoding="utf-8")
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    with open(table_path, newline="", encoding="utf-8") as f:
        table = {row["metric"]: row for row in csv.DictReader(f)}
    assert claim["source_eval_csv"] in report
    for metric in KEY_METRICS:
        assert metric in claim["metrics"]
        assert metric in table
        claim_row = claim["metrics"][metric]
        table_row = table[metric]
        assert claim_row["direction"] == table_row["direction"]
        assert claim_row["direction"] in report
        assert abs(float(claim_row["do_nothing_mean"]) - float(table_row["do_nothing_mean"])) < 1e-9
        assert abs(float(claim_row["proposed_mean"]) - float(table_row["proposed_mean"])) < 1e-9
        pattern = rf"\| {re.escape(metric)} \| ([0-9.\-]+) \| ([0-9.\-]+) \| ([0-9.\-]+) \| {claim_row['direction']} \|"
        assert re.search(pattern, report), metric


def _latest(pattern: str) -> Path:
    matches = sorted(Path().glob(pattern))
    assert matches, pattern
    return matches[-1]

