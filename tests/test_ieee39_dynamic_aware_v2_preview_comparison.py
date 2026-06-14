from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_v2_preview"


def test_v2_preview_comparison_artifacts_exist() -> None:
    for filename in ["v2_preview_comparison.json", "v2_preview_comparison.md"]:
        path = OUT / filename
        assert path.exists(), f"missing {path}"
        assert path.stat().st_size > 0, f"empty {path}"


def test_v2_preview_comparison_counts_and_caveats() -> None:
    payload = json.loads((OUT / "v2_preview_comparison.json").read_text(encoding="utf-8"))
    assert payload["preview_only"] is True
    assert payload["final_performance_conclusion"] is False
    assert payload["v1_expanded_num_samples"] == 35
    assert payload["v2_include_all_num_samples"] == 40
    assert payload["v2_exclude_provenance_num_samples"] == 39
    assert payload["non_line_trip_candidate_count"] == 5
    assert payload["provenance_excluded_count"] == 1
    assert payload["duplicate_measurement_groups"]

    gap = payload["sensitivity_gap_include_vs_exclude"]
    assert gap["leave_one_out_rmse_include_all"] is not None
    assert gap["leave_one_out_rmse_exclude_provenance"] is not None
    assert gap["rmse_exclude_minus_include"] is not None
    assert gap["label_family_holdout_rmse_include_all"] is not None
    assert gap["label_family_holdout_rmse_exclude_provenance"] is not None

    joined = " ".join(payload["interpretation"] + payload["caveats"]).lower()
    for required in [
        "preview",
        "nf06",
        "label_family_holdout",
        "not a final dynamic performance conclusion",
        "phasor_rms, not emt",
        "generator_speed_proxy is not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in joined


def test_v2_preview_comparison_markdown_records_key_numbers() -> None:
    text = (OUT / "v2_preview_comparison.md").read_text(encoding="utf-8").lower()
    for required in [
        "v1_expanded_num_samples: `35`",
        "v2_include_all_num_samples: `40`",
        "v2_exclude_provenance_num_samples: `39`",
        "provenance_excluded_count: `1`",
        "label_family_holdout",
        "preview",
    ]:
        assert required in text

