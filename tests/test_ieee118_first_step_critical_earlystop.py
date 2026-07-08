from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

import generate_ieee118_ordered_n2_fulltruth as gen
from build_ieee118_step2_state_dataset import load_fulltruth as load_step2_fulltruth
from evaluate_ieee118_rts79_protocol_search import load_truth as load_protocol_truth


EARLY_FULLTRUTH = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
EARLY_STEP2 = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_step2_state_earlystop"
EARLY_GCN = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval_earlystop"
EARLY_PROTOCOL = ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_rts79_protocol_eval_earlystop"


def _fake_state(total_shed: float) -> dict:
    branch_table = pd.DataFrame({"status": [0, 1], "loading_ratio": [0.0, 0.5]})
    return {
        "case": {"fake": True},
        "final_branch_table": branch_table,
        "island_load_shed_mw": total_shed,
        "redispatch_load_shed_mw": 0.0,
        "final_outage_labels": ("L001",),
        "event_table": pd.DataFrame({"max_loading_ratio": [0.5]}),
        "relay_trip_detail_table": pd.DataFrame(columns=["line_label"]),
        "converged": True,
    }


def test_generator_has_first_step_policy_cli() -> None:
    args = gen.parse_args(
        [
            "--seeds",
            "1",
            "--first-step-critical-policy",
            "skip",
        ]
    )
    assert args.first_step_critical_policy == "skip"
    args = gen.parse_args(["--seeds", "1", "--first-step-critical-policy", "expand"])
    assert args.first_step_critical_policy == "expand"


def test_skip_policy_does_not_call_second_state_for_first_step_critical(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    adapter = SimpleNamespace(line_labels=("L001", "L002"), case={"base": True})

    monkeypatch.setattr(gen, "build_case_adapter", lambda _name: adapter)
    monkeypatch.setattr(gen, "apply_ieee118_load_scenario", lambda case, seed, load_scale: case)
    monkeypatch.setattr(gen, "apply_thermal_limit_mode", lambda case, **kwargs: case)

    def fake_run(case, adapter_arg, outages, beta, security_limit):
        calls.append(tuple(outages))
        if len(outages) > 1 or outages[0] == "L002":
            raise AssertionError("second-state simulation should not be called in this skip-policy fixture")
        return _fake_state(total_shed=5.0)

    monkeypatch.setattr(gen, "run_sequential_outages_for_case", fake_run)
    table = gen.generate_fulltruth(
        argparse.Namespace(
            output_dir=tmp_path,
            seeds=[7],
            load_scale=1.0,
            limit_mode="flow_scaled",
            flow_limit_scale=8.0,
            min_rate_a=1.0,
            max_paths=1,
            sample_mode="first",
            sample_size=None,
            sample_seed=None,
            resume=False,
            retry_errors=False,
            checkpoint_every=0,
            beta=1.2,
            security_limit=1.0,
            first_step_critical_policy="skip",
        )
    )
    assert calls == [("L001",)]
    assert table.empty
    first = pd.read_csv(tmp_path / "ieee118_first_step_summary.csv")
    assert len(first) == 1
    assert bool(first.loc[0, "first_step_critical"])
    assert first.loc[0, "skip_reason"] == "first_step_critical"


def test_resume_skip_policy_reuses_first_step_critical_summary(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, ...]] = []
    adapter = SimpleNamespace(line_labels=("L001", "L002"), case={"base": True})
    pd.DataFrame(
        [
            {
                "scenario_id": 1,
                "seed": 7,
                "first_line": "L001",
                "first_step_converged": True,
                "first_step_critical": True,
                "first_step_total_load_shed_mw": 5.0,
                "first_step_island_load_shed_mw": 5.0,
                "first_step_redispatch_load_shed_mw": 0.0,
                "first_step_final_outage_labels": "L001",
                "first_step_num_relay_trips": 0,
                "first_step_relay_trip_labels": "",
                "first_step_critical_mechanism": "island_only",
                "num_skipped_second_lines": 1,
                "skip_reason": "first_step_critical",
            }
        ]
    ).to_csv(tmp_path / "ieee118_first_step_summary.csv", index=False)

    monkeypatch.setattr(gen, "build_case_adapter", lambda _name: adapter)
    monkeypatch.setattr(gen, "apply_ieee118_load_scenario", lambda case, seed, load_scale: case)
    monkeypatch.setattr(gen, "apply_thermal_limit_mode", lambda case, **kwargs: case)

    def fake_run(case, adapter_arg, outages, beta, security_limit):
        calls.append(tuple(outages))
        if len(outages) > 1:
            raise AssertionError("resume skip must not call second-state simulation")
        return _fake_state(total_shed=5.0)

    monkeypatch.setattr(gen, "run_sequential_outages_for_case", fake_run)
    table = gen.generate_fulltruth(
        argparse.Namespace(
            output_dir=tmp_path,
            seeds=[7],
            load_scale=1.0,
            limit_mode="flow_scaled",
            flow_limit_scale=8.0,
            min_rate_a=1.0,
            max_paths=1,
            sample_mode="first",
            sample_size=None,
            sample_seed=None,
            resume=True,
            retry_errors=False,
            checkpoint_every=0,
            beta=1.2,
            security_limit=1.0,
            first_step_critical_policy="skip",
        )
    )
    assert calls == [("L001",)]
    assert table.empty


def test_earlystop_fulltruth_compact_audit_counts() -> None:
    audit = json.loads((EARLY_FULLTRUTH / "ieee118_earlystop_fulltruth_audit_summary.json").read_text(encoding="utf-8"))
    assert audit["total_possible_ordered_n2_paths_without_earlystop"] == 34410
    assert audit["num_valid_ordered_n2_paths"] <= 34410
    assert audit["num_first_step_critical_lines"] == 10
    assert audit["num_skipped_ordered_n2_paths"] == 1850


def test_step2_builder_filters_first_step_critical_rows() -> None:
    table = load_step2_fulltruth(
        EARLY_FULLTRUTH / "ieee118_fulltruth_summary.csv",
        seed=20260708,
        max_first_lines=None,
        max_samples=None,
    )
    assert len(table) == 32560
    assert "first_step_critical" in table.columns
    assert not table["first_step_critical"].astype(str).str.lower().isin({"true", "1", "yes"}).any()


def test_converter_metadata_excludes_first_step_critical_samples() -> None:
    meta = json.loads((EARLY_GCN / "ieee118_rts79_gcn_dataset_metadata.json").read_text(encoding="utf-8"))
    assert meta["feature_mode"] == "paper"
    assert meta["num_state_samples"] == 176
    assert meta["num_path_samples"] == 32560
    assert meta["num_critical_path_labels"] == 1754


def test_protocol_evaluator_uses_valid_search_space() -> None:
    truth = load_protocol_truth(EARLY_FULLTRUTH / "ieee118_fulltruth_summary.csv")
    assert len(truth) == 32560
    config = json.loads((EARLY_PROTOCOL / "ieee118_rts79_protocol_earlystop_config.json").read_text(encoding="utf-8"))
    assert config["num_valid_ordered_n2_paths"] == 32560
    assert config["num_first_step_critical_lines"] == 10


def test_earlystop_protocol_methods_and_metrics_exist() -> None:
    summary = pd.read_csv(EARLY_PROTOCOL / "ieee118_rts79_protocol_earlystop_search_summary.csv")
    methods = set(summary["method"])
    assert {
        "RTS79_GCN_path_prob_reused_on_IEEE118_earlystop",
        "RTS79_GCN_second_only_reused_on_IEEE118_earlystop",
        "RTS79_GCN_prob_reused_on_IEEE118_earlystop",
        "RTS79_GCN_prob_yP_reused_on_IEEE118_earlystop",
        "LODF_yP",
        "line_order",
        "random",
    }.issubset(methods)
    assert "captured_relay_cascade_load_shed_ratio" in summary.columns


def test_earlystop_gcn_path_prob_only_valid_paths() -> None:
    top = pd.read_csv(EARLY_PROTOCOL / "ieee118_rts79_protocol_earlystop_topk_paths.csv")
    path_prob = top.loc[top["method"] == "RTS79_GCN_path_prob_reused_on_IEEE118_earlystop"].copy()
    assert not path_prob.empty
    assert np.allclose(path_prob["p_shed_first"] * path_prob["p_shed_second"], path_prob["path_product_score"])
    first_summary = pd.read_csv(EARLY_FULLTRUTH / "ieee118_first_step_summary.csv")
    skipped = set(first_summary.loc[first_summary["first_step_critical"].astype(str).str.lower().isin({"true", "1", "yes"}), "first_line"])
    assert skipped.isdisjoint(set(path_prob["first_line"]))


def test_earlystop_curve_is_sparse() -> None:
    curve = pd.read_csv(EARLY_PROTOCOL / "ieee118_rts79_protocol_earlystop_curve_points_sparse.csv")
    assert len(curve) < 1000
    assert curve["candidate_evaluations"].max() == 32560


def test_missing_earlystop_large_file_error_is_clear(tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"
    try:
        load_protocol_truth(missing)
    except FileNotFoundError as exc:
        assert "Missing IEEE118 full-truth CSV" in str(exc)
    else:
        raise AssertionError("Expected missing full-truth error")
