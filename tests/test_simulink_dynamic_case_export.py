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


def test_input_csv_export_uses_explicit_ranking_and_not_label_score(tmp_path: Path) -> None:
    input_csv = tmp_path / "ranked_paths.csv"
    pd.DataFrame(
        [
            {
                "path": "L27->L02",
                "rank": 2,
                "score": 0.2,
                "total_load_shed_mw": 999.0,
                "opa_total_load_shed_mw": 80.0,
            },
            {
                "first_line": "L10",
                "second_line": "L05",
                "rank": 1,
                "score": 0.8,
                "total_load_shed_mw": 1.0,
                "opa_total_load_shed_mw": 120.0,
            },
        ]
    ).to_csv(input_csv, index=False)
    out = tmp_path / "cases_from_csv"
    export_simulink_dynamic_cases(
        SimulinkDynamicCaseExportConfig(
            input_csv=str(input_csv),
            input_dir=str(tmp_path / "does_not_matter"),
            output_dir=str(out),
            top_k=(20,),
            event_1_time=1.25,
            event_2_time=4.75,
        )
    )
    paths = pd.read_csv(out / "simulink_topk_paths.csv")
    event_table = pd.read_csv(out / "simulink_dynamic_event_table.csv")
    assert paths["path"].tolist() == ["L10->L05", "L27->L02"]
    assert paths["reranker_score"].tolist() == [0.8, 0.2]
    assert event_table["event_time"].tolist() == [1.25, 4.75, 1.25, 4.75]
    assert "total_load_shed_mw" not in event_table.columns
    assert "opa_total_load_shed_mw" in event_table.columns
