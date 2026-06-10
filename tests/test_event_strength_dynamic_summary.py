from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_dynamic_method_comparison import analyze_dynamic_method_comparison


def test_event_strength_summary_marks_nondegenerate_layer(tmp_path: Path) -> None:
    for group, unstable in [("learned_mlp_top100", True), ("pio_gcn_top100", False), ("lodf_top100", False)]:
        case_dir = tmp_path / "cases" / group
        result_dir = tmp_path / "results" / group
        case_dir.mkdir(parents=True)
        result_dir.mkdir(parents=True)
        pd.DataFrame([{"case_id": "c1", "path_rank": 1, "path": "L01->L02", "opa_is_critical": False}]).to_csv(case_dir / "simulink_topk_paths.csv", index=False)
        pd.DataFrame(
            [
                {
                    "case_id": "c1",
                    "dynamic_unstable": unstable,
                    "frequency_nadir_hz": 49.2,
                    "max_rotor_angle_separation_deg": 30,
                    "max_rotor_angle_separation_coi_deg": 30,
                    "max_line_loading_ratio": 0.9,
                    "dynamic_load_shed_mw": 0,
                    "passive_relay_trip_count": 0,
                    "security_redispatch_count": 0,
                    "unstable_reason": "test",
                }
            ]
        ).to_csv(result_dir / "simulink_dynamic_simulation_results.csv", index=False)
    result = analyze_dynamic_method_comparison(
        tmp_path / "cases",
        tmp_path / "results",
        tmp_path / "out",
        summary_prefix="dynamic_method_comparison_event_strength",
    )
    table = pd.read_csv(result["summary_csv"])
    assert result["nondegenerate_dynamic_layer"] is True
    assert "dynamic_recall" not in ",".join(table.columns).lower()
    assert table["nondegenerate_dynamic_layer"].astype(bool).all()
