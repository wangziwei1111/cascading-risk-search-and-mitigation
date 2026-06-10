from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from prepare_real_topk_for_simulink_dynamic import _normalize_real_topk


GROUPS = ["learned_top20", "low_score_top20", "random_top20", "line_order_top20"]


def prepare_dynamic_negative_control_inputs(
    input_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_negative_controls",
    top_k: int = 20,
    random_seed: int = 20260901,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_csv)
    table = _normalize_real_topk(raw, max(top_k, len(raw)))
    groups = {
        "learned_top20": table.sort_values(["reranker_score", "path"], ascending=[False, True]).head(top_k),
        "low_score_top20": table.sort_values(["reranker_score", "path"], ascending=[True, True]).head(top_k),
        "random_top20": table.sample(n=min(top_k, len(table)), random_state=random_seed),
        "line_order_top20": table.sort_values(["first_line", "second_line", "path"]).head(top_k),
    }
    outputs = {}
    for group, frame in groups.items():
        work = frame.reset_index(drop=True).copy()
        work["path_rank"] = range(1, len(work) + 1)
        work["case_id"] = [f"{group}_{idx:04d}" for idx in range(1, len(work) + 1)]
        path = out / f"{group}_input_paths.csv"
        work.to_csv(path, index=False, encoding="utf-8-sig")
        outputs[group] = str(path)
    config = {"input_csv": str(input_csv), "output_dir": str(out), "top_k": top_k, "random_seed": random_seed, "outputs": outputs}
    (out / "negative_control_input_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare learned/low-score/random/line-order dynamic negative-control inputs.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_negative_controls")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--random-seed", type=int, default=20260901)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_dynamic_negative_control_inputs(args.input_csv, args.output_dir, args.top_k, args.random_seed)


if __name__ == "__main__":
    main()
