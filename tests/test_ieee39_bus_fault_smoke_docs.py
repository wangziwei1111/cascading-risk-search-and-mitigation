from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/gcn_pio_validation_log.md",
    "docs/ieee39_non_line_trip_fault_type_expansion.md",
    "docs/ieee39_non_line_trip_fault_smoke_tests.md",
    "docs/ieee39_non_line_trip_label_export.md",
    "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md",
]


def test_bus_fault_docs_record_conservative_scope() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for required in [
        "different-bus three-phase fault",
        "bf01",
        "bf02",
        "does not train gcn",
        "does not retrain",
        "does not update the label gate",
        "does not export",
        "l12 remains excluded",
        "phasor_rms, not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in joined


def test_bus_fault_docs_do_not_overclaim() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for forbidden in [
        "returned to the full gcn pipeline",
        "trained gcn",
        "reranker was retrained",
        "updated the formal label gate",
        "is a final dynamic performance conclusion",
        "emt validation completed",
        "is direct frequency",
        "engineering-grade protection completed",
    ]:
        assert forbidden not in joined
