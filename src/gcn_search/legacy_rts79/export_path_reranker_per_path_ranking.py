from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from prepare_real_topk_for_simulink_dynamic import _normalize_real_topk


REQUIRED_OUTPUT_COLUMNS = [
    "case_id",
    "source_seed",
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
    "split",
    "method",
]

FORBIDDEN_LABEL_FEATURE_COLUMNS = {
    "is_critical",
    "critical",
    "opa_is_critical",
    "total_load_shed_mw",
    "opa_total_load_shed_mw",
    "oracle_rank",
    "truth_rank",
    "y_critical",
    "y_load_shed",
}


@dataclass(frozen=True)
class PathRerankerPerPathExportConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    model_dir: str = "results/gcn_search/path_reranker_models"
    output_dir: str = "results/gcn_search/simulink_dynamic_real_per_path_ranking"
    method: str = "learned_mlp_reranker_strict"
    split: str = "test"
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    retrain_if_missing: bool = False


def export_path_reranker_per_path_ranking(config: PathRerankerPerPathExportConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    source_csv = _find_source_ranking_csv(config)
    retrained = False
    if source_csv is None and config.retrain_if_missing:
        retrained = _try_retrain(config)
        source_csv = _find_source_ranking_csv(config)

    if source_csv is None:
        raise RuntimeError(
            "path reranker dataset/model artifacts not available; run build_path_reranker_dataset.py "
            "and train_path_reranker.py first."
        )

    source = pd.read_csv(source_csv)
    normalized = _normalize_ranking_table(source, config)
    ranking_csv = out / "learned_mlp_per_path_ranking.csv"
    config_json = out / "learned_mlp_per_path_ranking_config.json"
    preview_csv = out / "learned_mlp_topk_preview.csv"
    normalized.to_csv(ranking_csv, index=False, encoding="utf-8-sig")
    normalized.head(max(config.top_k)).to_csv(preview_csv, index=False, encoding="utf-8-sig")
    payload = {
        **asdict(config),
        "source_csv": str(source_csv),
        "retrained": bool(retrained),
        "num_paths": int(len(normalized)),
        "output_csv": str(ranking_csv),
        "topk_preview_csv": str(preview_csv),
        "forbidden_label_feature_columns_excluded": sorted(FORBIDDEN_LABEL_FEATURE_COLUMNS),
        "note": "This per-path ranking CSV is a local ignored runtime artifact; do not commit the full ranking file.",
    }
    config_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _find_source_ranking_csv(config: PathRerankerPerPathExportConfig) -> Path | None:
    roots = [Path(config.dataset_dir), Path(config.model_dir)]
    patterns = [
        f"**/*{config.split}*per_path*.csv",
        f"**/*{config.split}*rank*.csv",
        f"**/*{config.split}*score*.csv",
        "**/per_path*.csv",
        "**/*rank*.csv",
        "**/*score*.csv",
        "**/*.csv",
    ]
    candidates: list[tuple[int, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            for csv_path in root.glob(pattern):
                lower = str(csv_path).lower()
                if "simulink_dynamic" in lower or "ieee14" in lower:
                    continue
                try:
                    table = pd.read_csv(csv_path, nrows=50)
                except Exception:
                    continue
                cols = {col.lower() for col in table.columns}
                has_path = "path" in cols or {"first_line", "second_line"}.issubset(cols)
                has_score = bool(cols & {"reranker_score", "learned_score", "score", "path_score"})
                has_rank = bool(cols & {"path_rank", "rank", "learned_rank", "rank_in_pio"})
                if not has_path or not (has_score or has_rank):
                    continue
                priority = 0
                if config.split.lower() in lower:
                    priority += 10
                if config.method.lower() in lower:
                    priority += 8
                if "per_path" in lower:
                    priority += 6
                if "reranker" in lower or "learned" in lower:
                    priority += 5
                if has_score:
                    priority += 3
                candidates.append((priority, csv_path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    return candidates[0][1]


def _try_retrain(config: PathRerankerPerPathExportConfig) -> bool:
    train_script = Path(__file__).with_name("train_path_reranker.py")
    if not train_script.exists():
        return False
    subprocess.run(
        [
            sys.executable,
            str(train_script),
            "--dataset-dir",
            config.dataset_dir,
            "--model-dir",
            config.model_dir,
        ],
        check=True,
    )
    return True


def _normalize_ranking_table(table: pd.DataFrame, config: PathRerankerPerPathExportConfig) -> pd.DataFrame:
    work = table.copy()
    if "split" in work.columns:
        split_mask = work["split"].astype(str).str.lower() == config.split.lower()
        if split_mask.any():
            work = work[split_mask].copy()
    if "method" in work.columns:
        method_mask = work["method"].astype(str) == config.method
        if method_mask.any():
            work = work[method_mask].copy()
    normalized = _normalize_real_topk(work, max(len(work), max(config.top_k)))
    normalized["split"] = config.split
    normalized["method"] = config.method
    if normalized["path_rank"].isna().any():
        normalized = normalized.sort_values(["reranker_score", "path"], ascending=[False, True]).copy()
        normalized["path_rank"] = np.arange(1, len(normalized) + 1)
    return normalized[REQUIRED_OUTPUT_COLUMNS].sort_values(["path_rank", "path"]).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export learned path-reranker per-path rankings for Simulink dynamic validation.")
    parser.add_argument("--dataset-dir", default=PathRerankerPerPathExportConfig.dataset_dir)
    parser.add_argument("--model-dir", default=PathRerankerPerPathExportConfig.model_dir)
    parser.add_argument("--output-dir", default=PathRerankerPerPathExportConfig.output_dir)
    parser.add_argument("--method", default=PathRerankerPerPathExportConfig.method)
    parser.add_argument("--split", default=PathRerankerPerPathExportConfig.split)
    parser.add_argument("--top-k", nargs="+", type=int, default=[20, 50, 100, 200])
    parser.add_argument("--retrain-if-missing", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_path_reranker_per_path_ranking(
        PathRerankerPerPathExportConfig(
            dataset_dir=args.dataset_dir,
            model_dir=args.model_dir,
            output_dir=args.output_dir,
            method=args.method,
            split=args.split,
            top_k=tuple(args.top_k),
            retrain_if_missing=args.retrain_if_missing,
        )
    )


if __name__ == "__main__":
    main()
