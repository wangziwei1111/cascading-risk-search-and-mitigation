from __future__ import annotations

from pathlib import Path
import sys
import json

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from make_dynamic_method_comparison_figures import make_dynamic_method_comparison_figures


def test_dynamic_method_figures_manifest(tmp_path: Path) -> None:
    summary = tmp_path / "summary.csv"
    pd.DataFrame(
        [
            {"method": method, "top_k": k, "dynamic_precision_at_k": 0.2, "mean_dynamic_stress_score": 0.1}
            for method in ["learned_mlp", "pio_gcn", "lodf"]
            for k in [50, 100]
        ]
    ).to_csv(summary, index=False)
    rank = tmp_path / "rank.csv"
    pd.DataFrame(
        [{"method": method, "k": k, "mean_dynamic_stress_score_at_k": 0.1 + 0.001 * k} for method in ["learned_mlp", "pio_gcn", "lodf"] for k in [10, 20, 50, 100]]
    ).to_csv(rank, index=False)
    align = tmp_path / "align.csv"
    pd.DataFrame([{"method": method, "top_k": 100, "stress_corr_with_opa_total_load_shed_mw": 0.1} for method in ["learned_mlp", "pio_gcn", "lodf"]]).to_csv(align, index=False)
    boot = tmp_path / "boot.csv"
    pd.DataFrame([{"method": "learned_mlp", "top_k": 100, "metric": "dynamic_precision_at_k", "estimate": 0.2, "ci_low": 0.1, "ci_high": 0.3, "bootstrap_n": 10, "random_seed": 1}]).to_csv(boot, index=False)
    result = make_dynamic_method_comparison_figures(summary, rank, align, boot, tmp_path / "figs")
    manifest = json.loads(Path(result["manifest"]).read_text(encoding="utf-8"))
    assert Path(manifest["figures"]["precision"]).exists()
    assert "no dynamic recall" in manifest["caption"].lower()
