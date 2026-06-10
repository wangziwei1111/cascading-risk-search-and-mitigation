from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_non_smoke_label_dynamic_alignment import analyze_non_smoke_label_dynamic_alignment


def test_non_smoke_label_dynamic_alignment_outputs_correlations(tmp_path: Path) -> None:
    ranking_csv = tmp_path / "ranking.csv"
    pd.DataFrame(
        [
            {"case_id": "r1", "path_rank": 1, "path": "L01->L02", "first_line": "L01", "second_line": "L02", "reranker_score": 0.9, "pio_score": 0.8, "lodf_score": 0.7, "opa_is_critical": 1, "opa_total_load_shed_mw": 100},
            {"case_id": "r2", "path_rank": 2, "path": "L02->L03", "first_line": "L02", "second_line": "L03", "reranker_score": 0.1, "pio_score": 0.2, "lodf_score": 0.3, "opa_is_critical": 0, "opa_total_load_shed_mw": 0},
        ]
    ).to_csv(ranking_csv, index=False)
    cases_root = tmp_path / "cases"
    group_dir = cases_root / "learned_mlp_top100"
    group_dir.mkdir(parents=True)
    pd.DataFrame(
        [
            {"case_id": "c1", "path_rank": 1, "path": "L01->L02", "reranker_score": 0.9, "pio_score": 0.8, "lodf_score": 0.7, "opa_is_critical": 1, "opa_total_load_shed_mw": 100},
            {"case_id": "c2", "path_rank": 2, "path": "L02->L03", "reranker_score": 0.1, "pio_score": 0.2, "lodf_score": 0.3, "opa_is_critical": 0, "opa_total_load_shed_mw": 0},
        ]
    ).to_csv(group_dir / "simulink_topk_paths.csv", index=False)
    summary_csv = tmp_path / "dynamic_method_comparison_non_smoke_summary.csv"
    pd.DataFrame([{"method": "learned_mlp", "top_k": 100, "dynamic_precision_at_k": 0.5}]).to_csv(summary_csv, index=False)
    rank_depth_csv = tmp_path / "dynamic_rank_depth_curve_non_smoke.csv"
    pd.DataFrame([{"method": "learned_mlp", "k": 100, "mean_dynamic_stress_score_at_k": 0.6}]).to_csv(rank_depth_csv, index=False)
    stress_csv = tmp_path / "dynamic_method_comparison_non_smoke_stress_ranks.csv"
    pd.DataFrame(
        [
            {"group": "learned_mlp_top100", "case_id": "c1", "dynamic_unstable": True, "dynamic_stress_score": 0.8},
            {"group": "learned_mlp_top100", "case_id": "c2", "dynamic_unstable": False, "dynamic_stress_score": 0.2},
        ]
    ).to_csv(stress_csv, index=False)
    result = analyze_non_smoke_label_dynamic_alignment(ranking_csv, summary_csv, rank_depth_csv, tmp_path / "out", cases_root, stress_csv)
    table = pd.read_csv(result["csv"])
    assert "stress_corr_with_opa_total_load_shed_mw" in table.columns
    row = table[(table["method"] == "learned_mlp") & (table["top_k"] == 100)].iloc[0]
    assert float(row["stress_corr_with_opa_total_load_shed_mw"]) > 0.0
    assert not any("dynamic_recall" in col.lower() for col in table.columns)
