from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import pytest

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from check_simulink_dynamic_sanity_artifacts import check_simulink_dynamic_sanity_artifacts
from prepare_real_topk_for_simulink_dynamic import RealTopKPreparationConfig, prepare_real_topk_for_simulink_dynamic


def test_prepare_real_topk_requires_real_per_path_csv_without_fallback(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Real per-path ranking CSV not found"):
        prepare_real_topk_for_simulink_dynamic(
            RealTopKPreparationConfig(
                output_dir=str(tmp_path / "out"),
                search_dirs=(str(tmp_path / "missing"),),
                use_demo_fallback=False,
            )
        )


def test_prepare_real_topk_from_explicit_csv(tmp_path: Path) -> None:
    input_csv = tmp_path / "real_paths.csv"
    pd.DataFrame(
        [
            {"path_rank": 2, "path": "L27->L02", "reranker_score": 0.7, "opa_is_critical": True, "opa_total_load_shed_mw": 80.0},
            {"path_rank": 1, "path": "L10->L05", "reranker_score": 0.9, "opa_is_critical": True, "opa_total_load_shed_mw": 120.0},
        ]
    ).to_csv(input_csv, index=False)
    out = tmp_path / "real_topk"
    prepare_real_topk_for_simulink_dynamic(
        RealTopKPreparationConfig(output_dir=str(out), input_csv=str(input_csv), top_k=(20,))
    )
    paths = pd.read_csv(out / "real_topk_input_paths.csv")
    events = pd.read_csv(out / "simulink_dynamic_event_table.csv")
    assert paths["path"].tolist() == ["L10->L05", "L27->L02"]
    assert set(events["event_type"]) == {"trip_first_line", "trip_second_line"}
    assert (out / "real_topk_input_config.json").exists()


def test_sanity_artifact_checker_reads_mock_sanity_csv(tmp_path: Path) -> None:
    sanity_csv = tmp_path / "no_disturbance_sanity.csv"
    out_json = tmp_path / "sanity_summary.json"
    pd.DataFrame(
        [
            {
                "frequency_nadir_hz": 49.99,
                "frequency_zenith_hz": 50.01,
                "max_rotor_angle_separation_deg": 5.0,
                "max_line_loading_ratio": 0.8,
                "initial_power_balance_residual": 0.0,
                "final_frequency_deviation_hz": 0.01,
            }
        ]
    ).to_csv(sanity_csv, index=False)
    summary = check_simulink_dynamic_sanity_artifacts(sanity_csv, out_json)
    assert summary["passed"] is True
    assert out_json.exists()
