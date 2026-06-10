from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_dynamic_instability_reasons import analyze_dynamic_instability_reasons


def test_instability_reason_parser_counts_frequency_rotor_relay_and_mixed(tmp_path: Path) -> None:
    dynamic = tmp_path / "dynamic.csv"
    topk = tmp_path / "topk.csv"
    event = tmp_path / "dynamic_case_event_log_case_1.csv"
    pd.DataFrame(
        [
            {"case_id": "case_1", "dynamic_unstable": True, "unstable_reason": "frequency_nadir_below_49hz;rotor_angle_separation_above_180deg", "frequency_nadir_hz": 48.0, "frequency_zenith_hz": 51.0, "max_rotor_angle_separation_deg": 200.0, "max_line_loading_ratio": 1.1, "dynamic_load_shed_mw": 0.0, "passive_relay_trip_count": 0, "security_redispatch_count": 1},
            {"case_id": "case_2", "dynamic_unstable": True, "unstable_reason": "relay_violation_not_eliminated", "frequency_nadir_hz": 49.8, "frequency_zenith_hz": 50.1, "max_rotor_angle_separation_deg": 20.0, "max_line_loading_ratio": 1.5, "dynamic_load_shed_mw": 0.0, "passive_relay_trip_count": 0, "security_redispatch_count": 0},
        ]
    ).to_csv(dynamic, index=False)
    pd.DataFrame([{"case_id": "case_1", "path": "L01->L02"}, {"case_id": "case_2", "path": "L02->L03"}]).to_csv(topk, index=False)
    pd.DataFrame([{"case_id": "case_1", "event_type": "security_redispatch_or_load_shed"}]).to_csv(event, index=False)
    result = analyze_dynamic_instability_reasons(dynamic, str(tmp_path / "dynamic_case_event_log_*.csv"), topk, tmp_path / "out")
    assert result["frequency_nadir_below_threshold"] == 1
    assert result["rotor_angle_above_threshold"] == 1
    assert result["relay_violation_not_eliminated"] == 1
    assert result["mixed_reasons"] == 1


def test_security_event_alone_is_not_counted_as_reason(tmp_path: Path) -> None:
    dynamic = tmp_path / "dynamic.csv"
    topk = tmp_path / "topk.csv"
    event = tmp_path / "dynamic_case_event_log_case_1.csv"
    pd.DataFrame([{"case_id": "case_1", "dynamic_unstable": False, "unstable_reason": "stable", "frequency_nadir_hz": 49.8, "frequency_zenith_hz": 50.1, "max_rotor_angle_separation_deg": 20.0, "max_line_loading_ratio": 1.1, "dynamic_load_shed_mw": 5.0, "passive_relay_trip_count": 0, "security_redispatch_count": 1}]).to_csv(dynamic, index=False)
    pd.DataFrame([{"case_id": "case_1", "path": "L01->L02"}]).to_csv(topk, index=False)
    pd.DataFrame([{"case_id": "case_1", "event_type": "security_redispatch_or_load_shed"}]).to_csv(event, index=False)
    result = analyze_dynamic_instability_reasons(dynamic, str(tmp_path / "dynamic_case_event_log_*.csv"), topk, tmp_path / "out")
    assert result["dynamic_unstable_count"] == 0
    assert result["security_load_shed_only"] == 0
