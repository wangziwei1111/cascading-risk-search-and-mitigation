from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_simulink_dynamic_results import analyze_simulink_dynamic_results
from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases
from make_mock_simulink_dynamic_results import make_mock_simulink_dynamic_results


def test_mock_dynamic_results_analysis_without_recall(tmp_path: Path) -> None:
    cases_dir = tmp_path / "cases"
    results_dir = tmp_path / "results"
    analysis_dir = tmp_path / "analysis"
    export_simulink_dynamic_cases(SimulinkDynamicCaseExportConfig(output_dir=str(cases_dir), make_demo_cases=True))
    mock_csv = results_dir / "simulink_dynamic_simulation_results.csv"
    make_mock_simulink_dynamic_results(cases_dir / "simulink_dynamic_case_manifest.csv", mock_csv)
    analyze_simulink_dynamic_results(mock_csv, cases_dir / "simulink_topk_paths.csv", analysis_dir)
    precision = pd.read_csv(analysis_dir / "simulink_dynamic_precision_at_k.csv")
    overlap = pd.read_csv(analysis_dir / "simulink_opa_dynamic_overlap.csv")
    failures_path = analysis_dir / "simulink_dynamic_failure_cases.csv"
    failures = pd.read_csv(failures_path)
    assert "dynamic_precision_at_k" in precision.columns
    assert "dynamic_recall_at_k" not in precision.columns
    assert (analysis_dir / "simulink_dynamic_summary.json").exists()
    assert (overlap["metric"] == "opa_critical_and_dynamic_unstable_count").any()
    assert failures_path.exists()
    assert len(failures) >= 0
