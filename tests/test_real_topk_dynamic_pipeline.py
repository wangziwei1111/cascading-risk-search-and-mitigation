from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_relay_vs_security_events import analyze_relay_vs_security_events
from analyze_simulink_dynamic_results import analyze_simulink_dynamic_results
from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases
from prepare_real_topk_for_simulink_dynamic import RealTopKPreparationConfig, prepare_real_topk_for_simulink_dynamic


def test_real_topk_prepare_errors_without_per_path_csv(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Real per-path ranking CSV not found"):
        prepare_real_topk_for_simulink_dynamic(
            RealTopKPreparationConfig(output_dir=str(tmp_path / "out"), search_dirs=(str(tmp_path / "empty"),))
        )


def test_real_topk_input_csv_exports_events_and_no_recall_without_truth(tmp_path: Path) -> None:
    input_csv = tmp_path / "ranking.csv"
    pd.DataFrame(
        [
            {"path": "L10->L05", "reranker_score": 0.9, "pio_score": 0.4, "lodf_score": 0.2, "opa_is_critical": True},
            {"path": "L27->L02", "reranker_score": 0.8, "pio_score": 0.3, "lodf_score": 0.1, "opa_is_critical": False},
        ]
    ).to_csv(input_csv, index=False)
    topk_dir = tmp_path / "real_topk"
    prepare_real_topk_for_simulink_dynamic(
        RealTopKPreparationConfig(output_dir=str(topk_dir), input_csv=str(input_csv), top_k=(20,))
    )
    real_paths = pd.read_csv(topk_dir / "real_topk_input_paths.csv")
    assert {"first_line", "second_line"}.issubset(real_paths.columns)
    cases_dir = tmp_path / "cases"
    export_simulink_dynamic_cases(
        SimulinkDynamicCaseExportConfig(input_csv=str(topk_dir / "real_topk_input_paths.csv"), output_dir=str(cases_dir), top_k=(20,))
    )
    assert (cases_dir / "matlab_batch_input.csv").exists()
    results_csv = tmp_path / "dynamic_results.csv"
    pd.DataFrame(
        [
            {"case_id": "dyn_case_0001", "dynamic_unstable": True, "frequency_nadir_hz": 48.9, "max_rotor_angle_separation_deg": 10.0},
            {"case_id": "dyn_case_0002", "dynamic_unstable": False, "frequency_nadir_hz": 49.9, "max_rotor_angle_separation_deg": 5.0},
        ]
    ).to_csv(results_csv, index=False)
    analysis_dir = tmp_path / "analysis"
    analyze_simulink_dynamic_results(results_csv, cases_dir / "simulink_topk_paths.csv", analysis_dir)
    precision = pd.read_csv(analysis_dir / "simulink_dynamic_precision_at_k.csv")
    assert "dynamic_precision_at_k" in precision.columns
    assert "dynamic_recall_at_k" not in precision.columns


def test_real_topk_relay_security_summary_from_mock_logs(tmp_path: Path) -> None:
    results_csv = tmp_path / "results.csv"
    event_log = tmp_path / "dynamic_case_event_log_dyn_case_0001.csv"
    pd.DataFrame([{"case_id": "dyn_case_0001", "dynamic_load_shed_mw": 3.0, "max_security_violation_loading_ratio": 1.1, "max_relay_violation_loading_ratio": 1.3}]).to_csv(results_csv, index=False)
    pd.DataFrame(
        [
            {"case_id": "dyn_case_0001", "time_s": 1.0, "event_type": "active_trip_first_line", "line_label": "L10", "offlineLines": "L10", "load_shed_mw": 0.0, "loading_ratio": 0.0},
            {"case_id": "dyn_case_0001", "time_s": 1.2, "event_type": "security_redispatch_or_load_shed", "line_label": "L06", "offlineLines": "L10", "load_shed_mw": 3.0, "loading_ratio": 1.1},
        ]
    ).to_csv(event_log, index=False)
    out = tmp_path / "relay_security"
    analyze_relay_vs_security_events(results_csv, str(tmp_path / "dynamic_case_event_log_*.csv"), out)
    assert (out / "relay_vs_security_summary.csv").exists()
