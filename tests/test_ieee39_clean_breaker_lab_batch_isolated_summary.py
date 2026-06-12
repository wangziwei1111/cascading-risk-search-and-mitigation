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
    assert module.model_path_for(pattern, "L04").endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L04.slx")
    assert module.model_path_for(pattern, "L05").endswith("IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_L05.slx")
    assert module.validation_path_for("L04").endswith("ieee39_clean_breaker_lab_L04_validation_summary.csv")
