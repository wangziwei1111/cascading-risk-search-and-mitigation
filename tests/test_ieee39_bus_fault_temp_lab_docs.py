from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/gcn_pio_validation_log.md",
    "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md",
]


def test_temp_lab_docs_record_scope_and_results() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for required in [
        "temporary lab",
        "b39",
        "b26",
        "injection_point_found = false",
        "safe_to_run_smoke = false",
        "source `.slx`",
        "temporary `.slx`",
        "no gcn was trained",
        "reranker was not retrained",
        "no labels were exported",
        "old formal gate remains `35 / 33 / 33`",
        "v2 candidate count remains `40`",
        "l12",
        "phasor_rms, not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in joined


def test_temp_lab_docs_do_not_overclaim() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for forbidden in [
        "returned to the full gcn pipeline",
        "trained gcn",
        "reranker was retrained",
        "updated the formal label gate",
        "exported bus-fault labels",
        "is a final dynamic performance conclusion",
        "emt validation completed",
        "is direct frequency",
        "engineering-grade protection completed",
        "source `.slx` was modified and committed",
        "temporary `.slx` is committed",
    ]:
        assert forbidden not in joined
