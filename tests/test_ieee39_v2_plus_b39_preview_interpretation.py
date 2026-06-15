from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/ieee39_v2_plus_b39_preview_interpretation.md"


def test_b39_preview_interpretation_doc_exists_and_is_conservative():
    text = DOC.read_text(encoding="utf-8").lower()
    assert DOC.exists()
    assert "does not train gcn" in text
    assert "does not retrain the reranker" in text
    assert "no_dynamic_measurement_features rmse" in text
    assert "worse" in text
    assert "b39 holdout absolute error" in text
    assert "underestimates the dynamic_stress_score" in text
    assert "collect more independent bus-fault samples" in text
    assert "b26" in text
    assert "b26 is not verified" in text or "b26 is not smoke success" in text
    assert "phasor_rms`, not emt" in text
    assert "generator_speed_proxy` is not direct frequency" in text
    assert "not engineering-grade protection" in text
    for forbidden in [
        "gcn trained",
        "reranker retrained",
        "b26 smoke success",
        "b26 candidate label has been exported",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
    ]:
        assert forbidden not in text
