from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trip_isolated.py"
    spec = importlib.util.spec_from_file_location("clean_lab_runner", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clean_lab_timeout_summary_has_required_fields() -> None:
    module = _load_module()
    row = module.timeout_summary("L02", "isolated MATLAB run timed out after 240 seconds")
    assert row["test_case"] == "clean_lab_handwired_line_trip_L02"
    assert row["simulation_success"] is False
    assert row["physical_fault_or_breaker_action_executed"] is False
    assert row["training_ready_candidate"] is False
    assert row["measurement_extraction_status"] == "simulation_timeout"
    assert row["source_model"] == "clean_breaker_lab"


def test_clean_lab_adapt_row_only_marks_voltage_speed_angle_success_ready() -> None:
    module = _load_module()
    success = pd.Series(
        {
            "test_case": "handwired_line_trip_L02",
            "simulation_success": 1,
            "measurement_extraction_status": "voltage_speed_angle",
            "training_ready_candidate": 0,
        }
    )
    adapted_success = module.adapt_row(success, "L02")
    assert adapted_success["test_case"] == "clean_lab_handwired_line_trip_L02"
    assert adapted_success["training_ready_candidate"] is True
    assert adapted_success["source_model"] == "clean_breaker_lab"

    failed = pd.Series(
        {
            "test_case": "handwired_line_trip_L02",
            "simulation_success": 1,
            "measurement_extraction_status": "none",
            "training_ready_candidate": 1,
        }
    )
    adapted_failed = module.adapt_row(failed, "L02")
    assert adapted_failed["training_ready_candidate"] is False


def test_clean_lab_l02_compact_simulation_summary_is_training_ready() -> None:
    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_line_trip_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    row = table[table["test_case"].astype(str) == "clean_lab_handwired_line_trip_L02"].iloc[0]
    assert str(row["simulation_success"]).lower() in {"1", "true"}
    assert str(row["physical_fault_or_breaker_action_executed"]).lower() in {"1", "true"}
    assert row["trip_implementation"] in {"handwired_timed_breaker", "handwired_timed_controlled_switch"}
    assert row["measurement_extraction_status"] == "voltage_speed_angle"
    assert str(row["training_ready_candidate"]).lower() in {"1", "true"}
    assert str(row["breaker_opened"]).lower() in {"1", "true"}
    assert "frequency=generator_speed_proxy" in str(row["signal_source_summary"])
    assert str(row.get("timeout_or_error_message", "")).lower() in {"", "nan"}
    assert row["source_model"] == "clean_breaker_lab"
