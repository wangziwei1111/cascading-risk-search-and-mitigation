from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases


def test_demo_simulink_dynamic_case_export(tmp_path: Path) -> None:
    out = tmp_path / "simulink_dynamic_cases"
    export_simulink_dynamic_cases(
        SimulinkDynamicCaseExportConfig(
            output_dir=str(out),
            make_demo_cases=True,
            top_k=(20, 50, 100),
            event_1_time=1.0,
            event_2_time=5.0,
            simulation_end_time=20.0,
        )
    )
    event_table = pd.read_csv(out / "simulink_dynamic_event_table.csv")
    manifest = pd.read_csv(out / "simulink_dynamic_case_manifest.csv")
    matlab_input = pd.read_csv(out / "matlab_batch_input.csv")
    assert not matlab_input.empty
    assert set(event_table.groupby("case_id").size()) == {2}
    for _, group in event_table.groupby("case_id"):
        assert group["event_time"].tolist() == [1.0, 5.0]
        assert group["event_type"].tolist() == ["trip_first_line", "trip_second_line"]
    assert (manifest["first_line"] != manifest["second_line"]).all()
    assert "total_load_shed_mw" not in event_table.columns
    assert "opa_total_load_shed_mw" in event_table.columns
    assert "reranker_score" in event_table.columns
