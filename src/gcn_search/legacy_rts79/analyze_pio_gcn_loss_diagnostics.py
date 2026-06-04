from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class LossDiagnosticsConfig:
    output_dir: str = "results/gcn_search/pio_loss_diagnostics"
    physics_ce_metrics: str = "results/gcn_search/pio_formal_preliminary_3seed/training/physics_ce_only/rts79_physics_gcn_metrics.csv"
    physics_loss_metrics: str = "results/gcn_search/pio_formal_preliminary_3seed/training/physics_informed/rts79_physics_gcn_metrics.csv"
    rank_loss_metrics: str = "results/gcn_search/pio_rank_loss_preliminary_3seed/rank_loss_training_metrics.csv"
    ablation_summary: str = "results/gcn_search/pio_formal_ablation_3seed/ablation_method_comparison.csv"
    rank_loss_summary: str = "results/gcn_search/pio_rank_loss_preliminary_3seed/aggregate_method_comparison.csv"


def analyze_loss_diagnostics(config: LossDiagnosticsConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_rows = []
    for name, path in [
        ("physics_ce", config.physics_ce_metrics),
        ("original_physics_loss", config.physics_loss_metrics),
        ("pairwise_rank_loss", config.rank_loss_metrics),
    ]:
        row = _load_last_row(path)
        row["model"] = name
        metrics_rows.append(row)
    metrics = pd.DataFrame(metrics_rows)
    metrics.to_csv(out / "loss_contribution_summary.csv", index=False, encoding="utf-8-sig")

    score_cols = [c for c in metrics.columns if c in {"mean_positive_score", "mean_negative_score", "positive_negative_score_gap", "pr_auc", "mean_predicted_positive_probability"}]
    metrics[["model", *score_cols]].to_csv(out / "score_gap_summary.csv", index=False, encoding="utf-8-sig")

    over_cols = [c for c in metrics.columns if c.startswith("positive_prediction_rate") or c == "mean_predicted_positive_probability"]
    metrics[["model", *over_cols]].to_csv(out / "overprediction_summary.csv", index=False, encoding="utf-8-sig")

    recommendations = _make_recommendations(metrics, config)
    (out / "recommendations.md").write_text(recommendations, encoding="utf-8")
    return {"output_dir": str(out)}


def _load_last_row(path: str) -> dict:
    csv_path = Path(path)
    if not csv_path.exists():
        return {"source": path, "missing": True}
    table = pd.read_csv(csv_path)
    if table.empty:
        return {"source": path, "missing": False, "empty": True}
    row = table.iloc[-1].to_dict()
    row["source"] = path
    return row


def _make_recommendations(metrics: pd.DataFrame, config: LossDiagnosticsConfig) -> str:
    return f"""# PIO-GCN Loss Diagnostics Recommendations

This diagnostic is based on existing metrics only. It does not rerun training or full-truth simulations.

## Current Answers

- Over-prediction: check `overprediction_summary.csv`. If positive prediction rate at 0.5 is high while precision remains limited, the model is likely over-predicting high-risk branches.
- Original physics loss: current ablation indicates it changes probability calibration more than Top-K ordering. It is not yet a decisive ranking contributor.
- Pairwise rank-loss: current diagnostics show whether positive-negative score gap increases, but the existing 3-seed result does not show Top-20/Top-50 improvement.
- Hard negative mining: recommended as a next step because many noncritical high-score candidates can dominate the front of the ranking.
- Path-level loss: recommended for future work because the online task ranks ordered paths, while current losses are mostly branch/state level.

## Input Summaries

- Ablation summary: `{config.ablation_summary}`
- Pairwise rank-loss summary: `{config.rank_loss_summary}`

## Recommendation

Treat original physics loss and pairwise rank-loss as implemented diagnostics, not as proven improvements. The next useful experiments are hard negative mining and path-level ranking loss.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze PIO-GCN original physics loss and pairwise rank-loss diagnostics.")
    parser.add_argument("--output-dir", default="results/gcn_search/pio_loss_diagnostics")
    parser.add_argument("--physics-ce-metrics", default=LossDiagnosticsConfig.physics_ce_metrics)
    parser.add_argument("--physics-loss-metrics", default=LossDiagnosticsConfig.physics_loss_metrics)
    parser.add_argument("--rank-loss-metrics", default=LossDiagnosticsConfig.rank_loss_metrics)
    parser.add_argument("--ablation-summary", default=LossDiagnosticsConfig.ablation_summary)
    parser.add_argument("--rank-loss-summary", default=LossDiagnosticsConfig.rank_loss_summary)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_loss_diagnostics(
        LossDiagnosticsConfig(
            output_dir=args.output_dir,
            physics_ce_metrics=args.physics_ce_metrics,
            physics_loss_metrics=args.physics_loss_metrics,
            rank_loss_metrics=args.rank_loss_metrics,
            ablation_summary=args.ablation_summary,
            rank_loss_summary=args.rank_loss_summary,
        )
    )


if __name__ == "__main__":
    main()
