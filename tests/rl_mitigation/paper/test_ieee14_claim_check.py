import csv
import json
from pathlib import Path


def test_claim_check_outputs_metric_table_and_overall():
    report = json.loads(Path("results/rl_mitigation/paper/ieee14/reports/ieee14_claim_check.json").read_text(encoding="utf-8"))
    assert report["overall"] in {"fully_supported", "partially_supported", "not_supported"}
    assert "metrics" in report
    table = Path("results/rl_mitigation/paper/ieee14/tables/table_ieee14_claim_metrics.csv")
    assert table.exists()
    with open(table, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert {"metric", "direction", "supported"}.issubset(rows[0])

