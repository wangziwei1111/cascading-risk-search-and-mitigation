from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_opa_dynamic_disagreement import analyze_opa_dynamic_disagreement


def test_analyze_opa_dynamic_disagreement_outputs_summary(tmp_path: Path) -> None:
    topk = tmp_path / "topk.csv"
    dynamic = tmp_path / "dynamic.csv"
    out = tmp_path / "disagreement"
    pd.DataFrame(
        [
            {"case_id": "c1", "path": "L10->L05", "path_rank": 1, "opa_is_critical": True, "opa_total_load_shed_mw": 100.0},
            {"case_id": "c2", "path": "L16->L17", "path_rank": 2, "opa_is_critical": False, "opa_total_load_shed_mw": 0.0},
        ]
    ).to_csv(topk, index=False)
    pd.DataFrame(
        [
            {
                "case_id": "c1",
                "dynamic_unstable": False,
                "unstable_reason": "stable",
                "frequency_nadir_hz": 49.5,
                "max_rotor_angle_separation_deg": 20.0,
                "max_line_loading_ratio": 0.9,
            },
            {
                "case_id": "c2",
                "dynamic_unstable": True,
                "unstable_reason": "frequency_nadir_below_49hz",
                "frequency_nadir_hz": 48.5,
                "max_rotor_angle_separation_deg": 190.0,
                "max_line_loading_ratio": 1.7,
            },
        ]
    ).to_csv(dynamic, index=False)
    analyze_opa_dynamic_disagreement(topk, dynamic, out)
    summary = pd.read_csv(out / "opa_dynamic_disagreement_summary.csv")
    assert (summary["metric"] == "opa_critical_dynamic_stable_count").any()
    assert (out / "opa_critical_dynamic_stable_cases.csv").exists()
    assert (out / "opa_noncritical_dynamic_unstable_cases.csv").exists()
    assert (out / "high_dynamic_risk_low_opa_shed_cases.csv").exists()
