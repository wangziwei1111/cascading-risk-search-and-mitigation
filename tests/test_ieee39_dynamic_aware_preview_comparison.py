from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded"


def test_preview_comparison_artifacts_and_counts() -> None:
    comparison_path = OUT_DIR / "preview_training_comparison.json"
    comparison_md = OUT_DIR / "preview_training_comparison.md"
    assert comparison_path.exists()
    assert comparison_md.exists()

    comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert comparison["original_num_samples"] == 10
    assert comparison["expanded_num_samples"] == 35
    assert comparison["original_preview_only"] is True
    assert comparison["expanded_preview_only"] is True
    assert comparison["expanded_regression_metrics"]
    assert comparison["expanded_classification_metrics"] or comparison["expanded_skipped_metrics_reason"]
    assert comparison["target_columns"] == ["dynamic_stress_score", "unstable_flag"]
    assert comparison["cv_strategy"] == "leave_one_out"
    assert comparison["random_seed"] == 42


def test_preview_comparison_writes_cautious_interpretation() -> None:
    comparison = json.loads((OUT_DIR / "preview_training_comparison.json").read_text(encoding="utf-8"))
    text = "\n".join(comparison["interpretation"] + comparison["caveats"]).lower()
    for required in [
        "more samples",
        "compact phasor_rms preview",
        "not emt",
        "not a final dynamic performance conclusion",
        "synthetic proxy target",
        "metrics can be optimistic",
        "independent test set",
        "l12 remains excluded",
        "generator_speed_proxy is not direct frequency",
        "pilot breaker-like validation",
    ]:
        assert required in text

    md_text = (OUT_DIR / "preview_training_comparison.md").read_text(encoding="utf-8").lower()
    assert "preview-only" in md_text
    assert "not a final dynamic performance conclusion" in md_text
    assert "metrics can be optimistic" in md_text
