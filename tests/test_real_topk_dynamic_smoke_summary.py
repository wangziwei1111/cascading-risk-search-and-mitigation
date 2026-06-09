from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from summarize_real_topk_dynamic_validation import summarize_real_topk_dynamic_validation


def test_smoke_summary_scope_and_no_recall(tmp_path: Path) -> None:
    precision = tmp_path / "precision.csv"
    overlap = tmp_path / "overlap.csv"
    relay = tmp_path / "relay.csv"
    out = tmp_path / "summary"
    pd.DataFrame(
        [
            {"top_k": 20, "num_simulated": 20, "dynamic_precision_at_k": 0.5},
            {"top_k": 50, "num_simulated": 20, "dynamic_precision_at_k": 0.5},
        ]
    ).to_csv(precision, index=False)
    pd.DataFrame([{"metric": "opa_noncritical_but_dynamic_unstable_count", "value": 10}]).to_csv(overlap, index=False)
    pd.DataFrame([{"metric": "cases_with_passive_relay_trip", "value": 4}]).to_csv(relay, index=False)
    result = summarize_real_topk_dynamic_validation(
        precision,
        overlap,
        relay,
        out,
        result_scope="top20_preliminary_dynamic_smoke",
        run_status="completed",
        smoke_mode=True,
        matlab_executed=True,
    )
    table = pd.read_csv(result["smoke_summary_csv"])
    assert table["top_k"].tolist() == [20]
    assert table.loc[0, "result_scope"] == "top20_preliminary_dynamic_smoke"
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
