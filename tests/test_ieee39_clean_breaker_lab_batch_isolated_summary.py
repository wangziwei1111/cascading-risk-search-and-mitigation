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
    assert module.model_path_for(pattern, "L06").endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L06.slx")
    assert module.model_path_for(pattern, "L08").endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L08.slx")
    assert module.validation_path_for("L06").endswith("ieee39_clean_breaker_lab_batch_validation_summary.csv")


def test_batch_isolated_summary_contains_training_ready_l06_l07_l08() -> None:
    import pandas as pd

    root = Path(__file__).resolve().parents[1]
    path = root / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_clean_breaker_lab_batch_line_trip_summary.csv"
    assert path.exists()
    table = pd.read_csv(path)
    assert set(table["tripped_line"].astype(str)) == {"L06", "L07", "L08"}
    for line_id in ["L06", "L07", "L08"]:
        row = table[table["tripped_line"].astype(str) == line_id].iloc[0]
        assert str(row["simulation_success"]).lower() in {"1", "true"}
        assert str(row["physical_fault_or_breaker_action_executed"]).lower() in {"1", "true"}
        assert str(row["breaker_opened"]).lower() in {"1", "true"}
        assert str(row["training_ready_candidate"]).lower() in {"1", "true"}
        assert row["measurement_extraction_status"] == "voltage_speed_angle"
        assert row["source_model"] == f"clean_breaker_lab_{line_id}"
        assert "frequency=generator_speed_proxy" in row["signal_source_summary"]
