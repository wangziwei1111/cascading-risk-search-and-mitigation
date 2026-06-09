from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from run_real_topk_dynamic_validation_pipeline import RealTopKDynamicPipelineConfig, run_real_topk_dynamic_validation_pipeline


def test_real_topk_dynamic_pipeline_skip_matlab_generates_command_file(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    model = tmp_path / "model"
    out = tmp_path / "pipeline"
    dataset.mkdir()
    model.mkdir()
    pd.DataFrame(
        [
            {"split": "test", "path": "L10->L05", "reranker_score": 0.9, "pio_score": 0.4, "lodf_score": 0.2, "opa_is_critical": True},
            {"split": "test", "path": "L27->L02", "reranker_score": 0.8, "pio_score": 0.3, "lodf_score": 0.1, "opa_is_critical": False},
        ]
    ).to_csv(dataset / "test_per_path_scores.csv", index=False)

    result = run_real_topk_dynamic_validation_pipeline(
        RealTopKDynamicPipelineConfig(
            output_dir=str(out),
            dataset_dir=str(dataset),
            model_dir=str(model),
            top_k=(20,),
            max_cases=20,
            run_matlab=False,
            skip_matlab=True,
        )
    )

    assert result["matlab_executed"] is False
    assert Path(result["matlab_command_file"]).exists()
    assert (out / "real_topk" / "real_topk_input_paths.csv").exists()
    assert (out / "dynamic_cases" / "matlab_batch_input.csv").exists()
