from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from summarize_real_topk_dynamic_validation import summarize_real_topk_dynamic_validation


def test_real_topk_dynamic_summary_without_recall(tmp_path: Path) -> None:
    precision = tmp_path / "precision.csv"
    overlap = tmp_path / "overlap.csv"
    relay = tmp_path / "relay.csv"
    out = tmp_path / "summary"
    pd.DataFrame(
        [
            {"top_k": 20, "num_simulated": 20, "dynamic_unstable_count": 5, "dynamic_precision_at_k": 0.25},
        ]
    ).to_csv(precision, index=False)
    pd.DataFrame(
        [
            {"metric": "opa_critical_and_dynamic_unstable_count", "value": 3},
            {"metric": "opa_critical_but_dynamic_stable_count", "value": 2},
            {"metric": "opa_noncritical_but_dynamic_unstable_count", "value": 1},
        ]
    ).to_csv(overlap, index=False)
    pd.DataFrame(
        [
            {"metric": "cases_with_security_redispatch_or_load_shed", "value": 4},
            {"metric": "cases_with_passive_relay_trip", "value": 2},
            {"metric": "total_dynamic_load_shed_mw", "value": 12.5},
        ]
    ).to_csv(relay, index=False)

    result = summarize_real_topk_dynamic_validation(precision, overlap, relay, out, result_scope="top20_preliminary_smoke")
    summary = pd.read_csv(result["summary_csv"])
    assert "dynamic_recall_at_k" not in summary.columns
    assert summary.loc[0, "result_scope"] == "top20_preliminary_smoke"
    brief = Path(result["brief_md"]).read_text(encoding="utf-8")
    assert "No dynamic recall is reported" in brief
