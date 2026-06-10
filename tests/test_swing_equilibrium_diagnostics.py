from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_swing_equilibrium_diagnostics import analyze_swing_equilibrium_diagnostics


def test_no_trip_stable_mock_passes_sanity(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "no_trip_dynamic_unstable": False,
                "no_trip_frequency_nadir_hz": 49.95,
                "no_trip_frequency_zenith_hz": 50.03,
                "no_trip_final_mean_frequency_hz": 50.0,
                "no_trip_max_rotor_angle_separation_coi_deg": 5.0,
                "initial_pm_pe_max_abs_residual": 0.0,
            }
        )
    )
    result = analyze_swing_equilibrium_diagnostics(summary_json=summary, output_dir=tmp_path / "out")
    assert result["sanity_passed"] is True
    assert result["dynamic_model_equilibrium_failed"] is False


def test_no_trip_unstable_mock_fails_sanity(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(
        json.dumps(
            {
                "no_trip_dynamic_unstable": True,
                "no_trip_frequency_nadir_hz": 48.5,
                "no_trip_frequency_zenith_hz": 51.0,
                "no_trip_max_rotor_angle_separation_coi_deg": 90.0,
                "initial_pm_pe_max_abs_residual": 0.1,
            }
        )
    )
    result = analyze_swing_equilibrium_diagnostics(summary_json=summary, output_dir=tmp_path / "out")
    assert result["sanity_passed"] is False
    assert result["dynamic_model_equilibrium_failed"] is True


def test_coi_angle_field_from_result_csv_is_used(tmp_path: Path) -> None:
    result_csv = tmp_path / "dynamic_case_result_no_trip.csv"
    pd.DataFrame(
        [
            {
                "dynamic_unstable": False,
                "frequency_nadir_hz": 49.99,
                "frequency_zenith_hz": 50.01,
                "final_mean_frequency_hz": 50.0,
                "max_rotor_angle_separation_deg": 100.0,
                "max_rotor_angle_separation_coi_deg": 10.0,
                "initial_pm_pe_max_abs_residual": 0.0,
            }
        ]
    ).to_csv(result_csv, index=False)
    result = analyze_swing_equilibrium_diagnostics(dynamic_result_csv=result_csv, output_dir=tmp_path / "out")
    assert result["no_trip_max_rotor_angle_separation_coi_deg"] == 10.0
    assert result["sanity_passed"] is True
