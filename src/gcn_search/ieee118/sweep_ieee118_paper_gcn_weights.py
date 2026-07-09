from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from train_ieee118_paper_aligned_gcn import train


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Positive-weight sensitivity for IEEE118 paper-aligned RTS-79 GCN.")
    parser.add_argument("--dataset-npz", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_paper_aligned_training_scaleup" / "pilot_2000_weight_sweep",
    )
    parser.add_argument("--positive-weights", type=float, nargs="+", default=[20, 50, 100, 200, 800])
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument("--random-seed", type=int, default=20260708)
    return parser.parse_args()


def _metric(metrics: dict[str, Any], subset: str, key: str) -> float:
    return float(metrics["classification_metrics"].get(subset, {}).get(key, 0.0))


def run_sweep(args: argparse.Namespace) -> pd.DataFrame:
    if not args.dataset_npz.exists():
        raise FileNotFoundError(
            f"Missing paper-aligned IEEE118 GCN dataset: {args.dataset_npz}. "
            "Run build_ieee118_paper_gcn_training_dataset.py first; the sweep will not regenerate large data."
        )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for weight in args.positive_weights:
        run_dir = args.output_dir / f"positive_weight_{weight:g}"
        train_args = argparse.Namespace(
            dataset_npz=args.dataset_npz,
            output_dir=run_dir,
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            positive_weight=float(weight),
            random_seed=args.random_seed,
            config_sweep_positive_weights=args.positive_weights,
            config_sweep_epochs=[args.epochs],
            config_sweep_batch_sizes=[args.batch_size],
        )
        metrics = train(train_args)
        row = {
            "positive_weight": float(weight),
            "setting_role": "original_paper_default" if float(weight) == 20.0 else "sensitivity",
            "epochs": int(args.epochs),
            "batch_size": int(args.batch_size),
            "learning_rate": float(args.learning_rate),
            "overall_hit_rate": _metric(metrics, "overall", "hit_rate"),
            "overall_cover_rate": _metric(metrics, "overall", "cover_rate"),
            "overall_f1": _metric(metrics, "overall", "f1"),
            "overall_average_precision": _metric(metrics, "overall", "average_precision"),
            "S0_hit_rate": _metric(metrics, "S0", "hit_rate"),
            "S0_cover_rate": _metric(metrics, "S0", "cover_rate"),
            "S0_average_precision": _metric(metrics, "S0", "average_precision"),
            "S1_hit_rate": _metric(metrics, "S1", "hit_rate"),
            "S1_cover_rate": _metric(metrics, "S1", "cover_rate"),
            "S1_average_precision": _metric(metrics, "S1", "average_precision"),
            "positive_prediction_rate_at_0.5": _metric(metrics, "overall", "positive_prediction_rate_at_0.5"),
            "positive_prediction_rate_at_0.8": _metric(metrics, "overall", "positive_prediction_rate_at_0.8"),
            "metrics_json": str(run_dir / "ieee118_paper_gcn_metrics.json"),
            "model_checkpoint_local_only": str(run_dir / "ieee118_paper_gcn_model.pt"),
        }
        rows.append(row)
    table = pd.DataFrame(rows)
    sort_cols = ["overall_average_precision", "S0_average_precision", "S1_average_precision"]
    best = table.sort_values(sort_cols, ascending=[False, False, False]).iloc[0].to_dict()
    table["is_best_sensitivity_by_average_precision"] = table["positive_weight"].eq(float(best["positive_weight"]))
    table.to_csv(args.output_dir / "ieee118_paper_gcn_weight_sweep_summary.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_paper_gcn_weight_sweep_summary.json").write_text(
        json.dumps(
            {
                "original_paper_default_positive_weight": 20.0,
                "best_sensitivity_by_average_precision": best,
                "rows": table.to_dict("records"),
                "note": "The best sensitivity setting is reported separately and must not overwrite the original-paper default baseline.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (args.output_dir / "ieee118_paper_gcn_weight_sweep_readme.md").write_text(
        "# IEEE118 Paper-Aligned Positive-Weight Sweep\n\n"
        "This sweep retrains the original RTS-79 `PaperStyleRts79Gcn` with different positive class weights. "
        "`positive_weight=20` is the original RTS-79 default and remains the main paper-aligned baseline. "
        "Higher weights are IEEE118 sensitivity checks and should be reported separately.\n\n"
        f"- Dataset: `{args.dataset_npz}`\n"
        f"- Epochs: {args.epochs}\n"
        f"- Batch size: {args.batch_size}\n"
        f"- Best sensitivity by average precision: positive_weight={best['positive_weight']}\n"
        "- Model checkpoints are local-only and should not be committed.\n",
        encoding="utf-8",
    )
    return table


def main() -> None:
    args = parse_args()
    print(run_sweep(args).to_string(index=False))


if __name__ == "__main__":
    main()
