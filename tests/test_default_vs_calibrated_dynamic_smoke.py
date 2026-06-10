from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from compare_default_vs_calibrated_dynamic_smoke import compare_default_vs_calibrated_dynamic_smoke
from summarize_real_topk_dynamic_validation import summarize_real_topk_dynamic_validation


def test_compare_default_vs_calibrated_outputs_two_rows(tmp_path: Path) -> None:
    default_summary = tmp_path / "default.csv"
    calibrated_summary = tmp_path / "calibrated.csv"
    default_deg = tmp_path / "default.json"
    calibrated_deg = tmp_path / "calibrated.json"
    out = tmp_path / "out"
    base = {
        "top_k": 20,
        "dynamic_precision_at_k": 1.0,
        "cases_with_passive_relay_trip": 20,
        "cases_with_security_redispatch_or_load_shed": 0,
        "opa_critical_and_dynamic_unstable_count": 1,
        "opa_critical_but_dynamic_stable_count": 0,
        "opa_noncritical_but_dynamic_unstable_count": 19,
        "total_dynamic_load_shed_mw": 0.0,
        "result_scope": "default_top20_preliminary_dynamic_smoke",
    }
    pd.DataFrame([base]).to_csv(default_summary, index=False)
    calibrated = {**base, "cases_with_passive_relay_trip": 0, "cases_with_security_redispatch_or_load_shed": 20, "result_scope": "calibrated_top20_preliminary_dynamic_smoke"}
    pd.DataFrame([calibrated]).to_csv(calibrated_summary, index=False)
    default_deg.write_text(json.dumps({"degeneracy_warning": True}), encoding="utf-8")
    calibrated_deg.write_text(json.dumps({"degeneracy_warning": True}), encoding="utf-8")
    result = compare_default_vs_calibrated_dynamic_smoke(default_summary, calibrated_summary, default_deg, calibrated_deg, out)
    comparison = pd.read_csv(result["csv"])
    assert comparison["variant"].tolist() == ["default", "calibrated"]
    assert (out / "default_vs_calibrated_dynamic_smoke_comparison.md").exists()


def test_calibrated_summary_has_scope_and_no_recall(tmp_path: Path) -> None:
    precision = tmp_path / "precision.csv"
    overlap = tmp_path / "overlap.csv"
    relay = tmp_path / "relay.csv"
    out = tmp_path / "summary"
    deg = tmp_path / "deg.json"
    pd.DataFrame([{"top_k": 20, "num_simulated": 20, "dynamic_precision_at_k": 1.0}]).to_csv(precision, index=False)
    pd.DataFrame([{"metric": "opa_noncritical_but_dynamic_unstable_count", "value": 19}]).to_csv(overlap, index=False)
    pd.DataFrame([{"metric": "cases_with_security_redispatch_or_load_shed", "value": 20}]).to_csv(relay, index=False)
    deg.write_text(json.dumps({"degeneracy_warning": True}), encoding="utf-8")
    result = summarize_real_topk_dynamic_validation(
        precision,
        overlap,
        relay,
        out,
        result_scope="calibrated_top20_preliminary_dynamic_smoke",
        calibrated=True,
        degeneracy_check_json=str(deg),
    )
    table = pd.read_csv(result["scoped_summary_csv"])
    assert table.loc[0, "result_scope"] == "calibrated_top20_preliminary_dynamic_smoke"
    assert bool(table.loc[0, "degeneracy_warning"]) is True
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
