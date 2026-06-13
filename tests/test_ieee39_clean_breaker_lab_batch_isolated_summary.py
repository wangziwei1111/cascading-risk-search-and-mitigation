from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/gcn_search/run_ieee39_clean_breaker_lab_line_trips_batch_isolated.py"
    sys.path.insert(0, str(script.parent))
    spec = importlib.util.spec_from_file_location("batch_clean_lab_runner", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_batch_isolated_runner_builds_per_line_model_paths() -> None:
    module = _load_module()
    pattern = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx"
    assert module.model_path_for(pattern, "L11").endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L11.slx")
    assert module.model_path_for(pattern, "L34").endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L34.slx")
    assert module.validation_path_for("L11").endswith("ieee39_clean_breaker_lab_batch_validation_summary.csv")


def test_batch_isolated_summary_contains_training_ready_l11_l34_except_l12_timeout() -> None:
    import pandas as pd

    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    expected_lines = {f"L{i:02d}" for i in range(11, 35)}
    assert set(table["tripped_line"].astype(str)) == expected_lines
    for line_id in sorted(expected_lines - {"L12"}):
        row = table[table["tripped_line"].astype(str) == line_id].iloc[0]
        assert str(row["simulation_success"]).lower() in {"1", "true"}
        assert str(row["physical_fault_or_breaker_action_executed"]).lower() in {"1", "true"}
        assert str(row["breaker_opened"]).lower() in {"1", "true"}
        assert str(row["training_ready_candidate"]).lower() in {"1", "true"}
        assert row["measurement_extraction_status"] == "voltage_speed_angle"
        assert row["source_model"] == f"clean_breaker_lab_{line_id}"
        assert "frequency=generator_speed_proxy" in row["signal_source_summary"]
    l12 = table[table["tripped_line"].astype(str) == "L12"].iloc[0]
    assert str(l12["simulation_success"]).lower() in {"0", "false"}
    assert l12["measurement_extraction_status"] == "simulation_timeout"
    assert str(l12["training_ready_candidate"]).lower() in {"0", "false"}
