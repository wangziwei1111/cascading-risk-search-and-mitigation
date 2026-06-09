from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_relay_vs_security_events import analyze_relay_vs_security_events, classify_loading_action


def test_loading_above_security_limit_below_beta_is_not_relay() -> None:
    assert classify_loading_action(1.05, beta=1.2, security_limit=1.0) == "security_redispatch_or_load_shed"


def test_loading_above_beta_is_passive_relay_trip() -> None:
    assert classify_loading_action(1.25, beta=1.2, security_limit=1.0) == "passive_relay_trip"


def test_relay_vs_security_event_analysis_outputs_summary(tmp_path: Path) -> None:
    results = tmp_path / "simulink_dynamic_simulation_results.csv"
    event_log = tmp_path / "dynamic_case_event_log_c1.csv"
    out = tmp_path / "analysis"
    pd.DataFrame(
        [
            {
                "case_id": "c1",
                "passive_relay_trip_count": 1,
                "security_redispatch_count": 1,
                "dynamic_load_shed_mw": 5.0,
                "max_security_violation_loading_ratio": 1.05,
                "max_relay_violation_loading_ratio": 1.25,
            }
        ]
    ).to_csv(results, index=False)
    pd.DataFrame(
        [
            {
                "case_id": "c1",
                "time_s": 1.0,
                "event_type": "security_redispatch_or_load_shed",
                "line_label": "L06",
                "loading_ratio": 1.05,
                "relay_beta": 1.2,
                "affected_bus_id": 3,
                "load_shed_mw": 5.0,
                "cumulative_load_shed_mw": 5.0,
                "reason": "loading_ratio_above_lmax_below_relay_beta",
            },
            {
                "case_id": "c1",
                "time_s": 2.0,
                "event_type": "passive_relay_trip",
                "line_label": "L07",
                "loading_ratio": 1.25,
                "relay_beta": 1.2,
                "affected_bus_id": "",
                "load_shed_mw": 0.0,
                "cumulative_load_shed_mw": 5.0,
                "reason": "loading_ratio_above_beta",
            },
        ]
    ).to_csv(event_log, index=False)
    analyze_relay_vs_security_events(results, str(tmp_path / "dynamic_case_event_log_*.csv"), out)
    summary = pd.read_csv(out / "relay_vs_security_summary.csv")
    metrics = dict(zip(summary["metric"], summary["value"]))
    assert metrics["cases_with_security_redispatch_or_load_shed"] == 1
    assert metrics["cases_with_passive_relay_trip"] == 1
    assert (out / "security_redispatch_cases.csv").exists()
    assert (out / "passive_relay_trip_cases.csv").exists()
    assert (out / "load_shed_due_to_security_constraint.csv").exists()
