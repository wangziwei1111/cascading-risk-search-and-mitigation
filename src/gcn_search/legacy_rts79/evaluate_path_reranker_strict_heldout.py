from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from train_path_reranker import _predict_table


@dataclass(frozen=True)
class StrictHeldoutConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    model_dir: str = "results/gcn_search/path_reranker_models"
    output_dir: str = "results/gcn_search/path_reranker_strict_heldout_eval"
    split: str = "test"
    method: str = "learned_mlp_reranker_strict"
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    export_per_path_ranking: bool = True
    per_path_ranking_output_csv: str | None = None


def evaluate_strict_heldout(config: StrictHeldoutConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "strict_heldout_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    with (Path(config.model_dir) / "path_reranker_model.pkl").open("rb") as handle:
        model = pickle.load(handle)
    table = pd.read_csv(Path(config.dataset_dir) / f"path_reranker_{config.split}.csv")
    pred = _predict_table(model, table, config.split)
    ranking = _make_per_path_ranking(pred, config)
    comparison = _make_comparison(ranking, config)
    comparison.to_csv(out / "strict_heldout_method_comparison.csv", index=False, encoding="utf-8-sig")
    if config.export_per_path_ranking:
        target = Path(config.per_path_ranking_output_csv) if config.per_path_ranking_output_csv else out / "learned_mlp_per_path_ranking.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        ranking.to_csv(target, index=False, encoding="utf-8-sig")
    return {"output_dir": str(out), "per_path_ranking": str(out / "learned_mlp_per_path_ranking.csv")}


def _make_per_path_ranking(pred: pd.DataFrame, config: StrictHeldoutConfig) -> pd.DataFrame:
    work = pred.copy()
    work = work.sort_values(["learned_score", "path"], ascending=[False, True]).reset_index(drop=True)
    work["path_rank"] = np.arange(1, len(work) + 1)
    work["case_id"] = [f"reranker_{idx:04d}" for idx in range(1, len(work) + 1)]
    work["method"] = config.method
    work["reranker_score"] = work["learned_score"]
    for col in ["source_seed", "pio_score", "paper_score", "lodf_score", "opa_is_critical", "opa_total_load_shed_mw"]:
        if col not in work.columns:
            work[col] = np.nan
    return work[
        [
            "case_id",
            "source_seed",
            "split",
            "method",
            "path_rank",
            "path",
            "first_line",
            "second_line",
            "pio_score",
            "paper_score",
            "lodf_score",
            "reranker_score",
            "opa_is_critical",
            "opa_total_load_shed_mw",
        ]
    ]


def _make_comparison(ranking: pd.DataFrame, config: StrictHeldoutConfig) -> pd.DataFrame:
    total = max(int(pd.to_numeric(ranking["opa_is_critical"], errors="coerce").fillna(0).sum()), 1)
    rows = []
    for k in config.top_k:
        subset = ranking.head(k)
        found = int(pd.to_numeric(subset["opa_is_critical"], errors="coerce").fillna(0).sum())
        rows.append(
            {
                "method": config.method,
                "top_k": int(k),
                "critical_found": found,
                "critical_path_recall": float(found / total),
                "notes": "minimal strict heldout smoke when dataset is smoke; not a formal large-scale reranker result",
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate minimal learned path reranker on held-out split.")
    parser.add_argument("--dataset-dir", default=StrictHeldoutConfig.dataset_dir)
    parser.add_argument("--model-dir", default=StrictHeldoutConfig.model_dir)
    parser.add_argument("--output-dir", default=StrictHeldoutConfig.output_dir)
    parser.add_argument("--split", default=StrictHeldoutConfig.split)
    parser.add_argument("--method", default=StrictHeldoutConfig.method)
    parser.add_argument("--top-k", nargs="+", type=int, default=[20, 50, 100, 200])
    parser.add_argument("--export-per-path-ranking", action="store_true")
    parser.add_argument("--per-path-ranking-output-csv", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_strict_heldout(
        StrictHeldoutConfig(
            dataset_dir=args.dataset_dir,
            model_dir=args.model_dir,
            output_dir=args.output_dir,
            split=args.split,
            method=args.method,
            top_k=tuple(args.top_k),
            export_per_path_ranking=args.export_per_path_ranking or True,
            per_path_ranking_output_csv=args.per_path_ranking_output_csv,
        )
    )


if __name__ == "__main__":
    main()
