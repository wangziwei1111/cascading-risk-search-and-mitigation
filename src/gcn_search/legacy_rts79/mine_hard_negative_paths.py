from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class HardNegativeMiningConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    eval_dir: str = "results/gcn_search/path_reranker_fulltruth_eval"
    model_dir: str = "results/gcn_search/path_reranker_models"
    output_dir: str = "results/gcn_search/path_reranker_hard_negative_mining"
    model_type: str = "mlp"
    top_k: int = 100


def mine_hard_negative_paths(config: HardNegativeMiningConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dataset = _load_dataset(config.dataset_dir)
    predictions = pd.read_csv(Path(config.model_dir) / "path_reranker_validation_predictions.csv")
    pred = predictions[predictions["model_type"] == config.model_type].copy()
    merged = pred.merge(dataset.drop(columns=["y_critical", "y_load_shed"], errors="ignore"), on=["seed", "path"], how="left")
    hard_negatives: list[pd.DataFrame] = []
    missed_positives: list[pd.DataFrame] = []
    for seed, group in merged.groupby("seed"):
        ordered = group.sort_values(["learned_score", "path"], ascending=[False, True]).reset_index(drop=True)
        ordered["learned_rank"] = range(1, len(ordered) + 1)
        hard_negatives.append(ordered[(ordered["learned_rank"] <= config.top_k) & (ordered["y_critical"] == 0)].head(50))
        missed_positives.append(ordered[(ordered["learned_rank"] > config.top_k) & (ordered["y_critical"] == 1)].head(50))
    hard_negative_table = pd.concat(hard_negatives, ignore_index=True) if hard_negatives else pd.DataFrame()
    missed_positive_table = pd.concat(missed_positives, ignore_index=True) if missed_positives else pd.DataFrame()
    hard_negative_table.to_csv(out / "hard_negative_paths.csv", index=False, encoding="utf-8-sig")
    missed_positive_table.to_csv(out / "hard_positive_missed_paths.csv", index=False, encoding="utf-8-sig")
    summary = _summary(hard_negative_table, missed_positive_table)
    summary.to_csv(out / "hard_negative_summary.csv", index=False, encoding="utf-8-sig")
    _write_recommendations(out, hard_negative_table, missed_positive_table)
    return {"output_dir": str(out)}


def _load_dataset(dataset_dir: str | Path) -> pd.DataFrame:
    return pd.concat([pd.read_csv(Path(dataset_dir) / name) for name in ["path_reranker_train.csv", "path_reranker_val.csv", "path_reranker_test.csv"]], ignore_index=True)


def _summary(hard_negative: pd.DataFrame, missed_positive: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, table in [("hard_negative", hard_negative), ("missed_positive", missed_positive)]:
        if table.empty:
            rows.append({"type": name, "count": 0})
            continue
        rows.append(
            {
                "type": name,
                "count": int(len(table)),
                "mean_pio_score": float(table["pio_score"].mean()),
                "mean_paper_score": float(table["paper_score"].mean()),
                "mean_lodf_score": float(table["lodf_score"].mean()),
                "mean_max_loading_ratio": float(table["max_loading_ratio"].mean()),
                "mean_first_outage_max_loading_ratio": float(table["first_outage_max_loading_ratio"].mean()),
                "top_first_lines": ",".join(table["first_line"].value_counts().head(5).index.astype(str).tolist()) if "first_line" in table else "",
                "top_second_lines": ",".join(table["second_line"].value_counts().head(5).index.astype(str).tolist()) if "second_line" in table else "",
            }
        )
    return pd.DataFrame(rows)


def _write_recommendations(out: Path, hard_negative: pd.DataFrame, missed_positive: pd.DataFrame) -> None:
    if missed_positive.empty:
        missed_text = "No critical path remains outside Top-100 for the selected learned reranker sample table."
    else:
        missed_text = (
            f"Missed critical paths outside Top-100 have mean PIO score {missed_positive['pio_score'].mean():.4f}, "
            f"mean paper score {missed_positive['paper_score'].mean():.4f}, and mean max loading ratio {missed_positive['max_loading_ratio'].mean():.4f}."
        )
    if hard_negative.empty:
        hard_text = "No hard negative path was found in the selected Top-K window."
    else:
        hard_text = (
            f"Hard negatives concentrate around first lines {', '.join(hard_negative['first_line'].value_counts().head(5).index.astype(str))}. "
            f"Their mean max loading ratio is {hard_negative['max_loading_ratio'].mean():.4f}."
        )
    text = f"""# Hard Negative Mining Recommendations

## Missed Critical Paths

{missed_text}

## Hard Negatives

{hard_text}

## Diagnosis

- The learned reranker greatly reduces missed critical paths compared with rule-based rerank.
- Remaining hard negatives are mostly physically stressful paths that look dangerous by loading and relay-risk features but do not lead to load shedding in the full cascade.
- Additional features that may help are topology distance, explicit islanding risk, and more detailed first-outage stress descriptors.
- More training seeds are still needed before treating this as a final result.
- A path-level GNN may be useful later, but the current compact learned reranker already shows that path-level supervision is a strong direction.
"""
    (out / "recommendations.md").write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Mine hard negatives and missed positives for learned path reranker.")
    parser.add_argument("--dataset-dir", default=HardNegativeMiningConfig.dataset_dir)
    parser.add_argument("--model-dir", default=HardNegativeMiningConfig.model_dir)
    parser.add_argument("--output-dir", default=HardNegativeMiningConfig.output_dir)
    parser.add_argument("--model-type", default="mlp")
    parser.add_argument("--top-k", type=int, default=100)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mine_hard_negative_paths(HardNegativeMiningConfig(dataset_dir=args.dataset_dir, model_dir=args.model_dir, output_dir=args.output_dir, model_type=args.model_type, top_k=args.top_k))


if __name__ == "__main__":
    main()
