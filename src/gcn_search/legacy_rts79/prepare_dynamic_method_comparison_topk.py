from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from prepare_real_topk_for_simulink_dynamic import _normalize_real_topk


METHOD_SCORES = {
    "learned_mlp": ["reranker_score", "learned_score", "score", "path_score"],
    "pio_gcn": ["pio_score"],
    "lodf": ["lodf_score"],
}


def prepare_dynamic_method_comparison_topk(input_csv: str | Path, output_dir: str | Path, top_k: int = 100) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(input_csv)
    outputs: dict[str, str] = {}
    warnings: list[str] = []
    for method, score_names in METHOD_SCORES.items():
        score_col = _first_existing(table, score_names)
        if score_col is None:
            warnings.append(f"Skipped {method}: missing score column from {score_names}.")
            continue
        ranked = table.copy()
        ranked[score_col] = pd.to_numeric(ranked[score_col], errors="coerce")
        ranked = ranked.sort_values(score_col, ascending=False).copy()
        ranked["path_rank"] = np.arange(1, len(ranked) + 1)
        normalized = _normalize_real_topk(ranked, top_k)
        output_name = {
            "learned_mlp": "learned_mlp_topk_input_paths.csv",
            "pio_gcn": "pio_gcn_topk_input_paths.csv",
            "lodf": "lodf_topk_input_paths.csv",
        }[method]
        output_path = out / output_name
        normalized.to_csv(output_path, index=False, encoding="utf-8-sig")
        outputs[method] = str(output_path)
    config = {"input_csv": str(input_csv), "output_dir": str(out), "top_k": top_k, "outputs": outputs, "warnings": warnings}
    (out / "dynamic_method_comparison_input_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def _first_existing(table: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {col.lower(): col for col in table.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare learned/Pio/LODF Top-K inputs for dynamic method comparison.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_method_comparison_inputs")
    parser.add_argument("--top-k", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_dynamic_method_comparison_topk(args.input_csv, args.output_dir, args.top_k)


if __name__ == "__main__":
    main()
