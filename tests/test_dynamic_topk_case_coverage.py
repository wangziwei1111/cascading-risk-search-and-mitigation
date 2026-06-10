from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from diagnose_dynamic_topk_case_coverage import diagnose_dynamic_topk_case_coverage
from prepare_dynamic_method_comparison_topk import prepare_dynamic_method_comparison_topk


def test_prepare_topk_fill_to_unique_paths(tmp_path: Path) -> None:
    ranking = tmp_path / "ranking.csv"
    rows = []
    for idx, path in enumerate(["L01->L02", "L01->L02", "L02->L03", "L03->L04", "L04->L05"], start=1):
        rows.append({"path": path, "first_line": path.split("->")[0], "second_line": path.split("->")[1], "reranker_score": 1.0 / idx, "pio_score": 1.0 / idx, "lodf_score": 1.0 / idx})
    pd.DataFrame(rows).to_csv(ranking, index=False)
    result = prepare_dynamic_method_comparison_topk(ranking, tmp_path / "inputs", top_k=3, ensure_unique_paths=True, fill_to_k=True)
    learned = pd.read_csv(tmp_path / "inputs" / "learned_mlp_top3_input_paths.csv")
    assert len(learned) == 3
    assert learned["path"].nunique() == 3
    assert result["coverage"]["learned_mlp"]["coverage_ratio"] == 1.0
    assert result["label_columns_used_for_sorting"] == []


def test_topk_case_coverage_detects_duplicate_shortfall(tmp_path: Path) -> None:
    ranking = tmp_path / "ranking.csv"
    pd.DataFrame([{"path": "L01->L02"}, {"path": "L01->L02"}, {"path": "L02->L03"}]).to_csv(ranking, index=False)
    input_root = tmp_path / "inputs"
    cases_root = tmp_path / "cases"
    results_root = tmp_path / "results"
    for method in ["learned_mlp", "pio_gcn", "lodf"]:
        input_root.mkdir(exist_ok=True)
        pd.DataFrame([{"case_id": "c1", "path": "L01->L02"}, {"case_id": "c2", "path": "L01->L02"}]).to_csv(input_root / f"{method}_top50_input_paths.csv", index=False)
        group = f"{method}_top50"
        (cases_root / group).mkdir(parents=True)
        (results_root / group).mkdir(parents=True)
        pd.DataFrame([{"case_id": "c1", "path": "L01->L02"}]).to_csv(cases_root / group / "simulink_dynamic_case_manifest.csv", index=False)
        pd.DataFrame([{"case_id": "c1"}, {"case_id": "c1"}]).to_csv(cases_root / group / "matlab_batch_input.csv", index=False)
        pd.DataFrame([{"case_id": "c1"}]).to_csv(results_root / group / "simulink_dynamic_simulation_results.csv", index=False)
    result = diagnose_dynamic_topk_case_coverage(ranking, input_root, cases_root, results_root, tmp_path / "out", top_k=(50,))
    table = pd.read_csv(result["csv"])
    assert (table["coverage_ratio"] < 0.95).all()
    assert "duplicate_input_paths" in table["dropped_reason_summary"].iloc[0]
