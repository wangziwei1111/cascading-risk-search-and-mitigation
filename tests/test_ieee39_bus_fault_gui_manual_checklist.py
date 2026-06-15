from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = [
    "docs/ieee39_bus_fault_gui_manual_checklist.md",
    "docs/ieee39_bus_fault_temp_lab_injection.md",
    "docs/ieee39_bus_fault_smoke_tests.md",
    "docs/ieee39_dynamic_aware_reranker_v2_preview_training.md",
    "docs/gcn_pio_validation_log.md",
]


def test_gui_manual_checklist_exists_and_contains_candidate_blocks() -> None:
    path = ROOT / "docs/ieee39_bus_fault_gui_manual_checklist.md"
    assert path.exists()
    assert path.stat().st_size > 0
    text = path.read_text(encoding="utf-8")
    for required in [
        "Grid/Bus39",
        "Grid/B39 to B1",
        "Grid/B9 to B39",
        "Generators/Gen1@Bus39",
        "Grid/GB39B1F",
        "Grid/GB39B1T",
        "Grid/GB9B39F",
        "Grid/GB9B39T",
        "Grid/Bus26_1",
        "Grid/Bus26_2",
        "Grid/B25 to B26",
        "Grid/B26 to B28",
        "Grid/B26 to B29",
        "Grid/B27 to B26",
        "Grid/GB25B26F",
        "Grid/GB25B26T",
        "Grid/GB26B28F",
        "Grid/GB26B28T",
        "Grid/GB26B29F",
        "Grid/GB26B29T",
        "Grid/GB27B26F",
        "Grid/GB27B26T",
    ]:
        assert required in text


def test_gui_manual_docs_record_boundaries() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for required in [
        "gui manual",
        "temporary `.slx`",
        "do_not_run_smoke",
        "b39/b26 are not smoke success",
        "does not run simulink",
        "does not modify `.slx`",
        "does not train gcn",
        "does not retrain",
        "does not export labels",
        "old formal gate remains `35 / 33 / 33`",
        "v2 candidate count remains `40`",
        "phasor_rms, not emt",
        "generator_speed_proxy",
        "not direct frequency",
        "not engineering-grade protection",
    ]:
        assert required in joined


def test_gui_manual_docs_do_not_overclaim() -> None:
    joined = "\n".join((ROOT / rel).read_text(encoding="utf-8").lower() for rel in DOCS)
    for forbidden in [
        "b39 smoke success",
        "b26 smoke success",
        "smoke success completed",
        "trained gcn model",
        "reranker was retrained",
        "exported bus-fault labels",
        "is a final dynamic performance conclusion",
        "emt validation completed",
        "generator_speed_proxy is direct frequency",
        "engineering-grade protection completed",
    ]:
        assert forbidden not in joined
