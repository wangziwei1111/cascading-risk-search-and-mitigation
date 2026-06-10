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
    low_risk_mode: str = "low_reranker_score",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_csv)
    table = _normalize_real_topk(raw, max(top_k, len(raw)))
    low_score = _select_low_risk(table, top_k, low_risk_mode)
    groups = {
        "learned_top20": table.sort_values(["reranker_score", "path"], ascending=[False, True]).head(top_k),
        "low_score_top20": low_score,
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
    config = {
        "input_csv": str(input_csv),
        "output_dir": str(out),
        "top_k": top_k,
        "random_seed": random_seed,
        "low_risk_mode": low_risk_mode,
        "label_columns_used_for_low_risk_selection": [],
        "outputs": outputs,
    }
    (out / "negative_control_input_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "low_risk_selection_config.json").write_text(
        json.dumps(
            {
                "low_risk_mode": low_risk_mode,
                "label_columns_used": [],
                "note": "Low-risk selection uses ranking/physics score columns only and does not use OPA labels.",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return config


def _select_low_risk(table: pd.DataFrame, top_k: int, mode: str) -> pd.DataFrame:
    if mode != "combined_low_stress":
        return table.sort_values(["reranker_score", "path"], ascending=[True, True]).head(top_k)
    work = table.copy()
    score_cols = [col for col in ["reranker_score", "pio_score", "lodf_score", "paper_score"] if col in work.columns]
    if not score_cols:
        return work.sort_values("path").head(top_k)
    combined = pd.Series(0.0, index=work.index)
    for col in score_cols:
        values = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
        span = max(float(values.max() - values.min()), 1e-9)
        combined = combined + (values - values.min()) / span
    work["_combined_low_stress_score"] = combined / len(score_cols)
    return work.sort_values(["_combined_low_stress_score", "path"], ascending=[True, True]).drop(columns=["_combined_low_stress_score"]).head(top_k)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare learned/low-score/random/line-order dynamic negative-control inputs.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_negative_controls")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--random-seed", type=int, default=20260901)
    parser.add_argument("--low-risk-mode", choices=["low_reranker_score", "combined_low_stress"], default="low_reranker_score")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_dynamic_negative_control_inputs(args.input_csv, args.output_dir, args.top_k, args.random_seed, args.low_risk_mode)


if __name__ == "__main__":
    main()
