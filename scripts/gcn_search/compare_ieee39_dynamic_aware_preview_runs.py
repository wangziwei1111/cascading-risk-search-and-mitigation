from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_OLD_METRICS = "results/gcn_search/ieee39_dynamic_aware_reranker_preview/preview_training_metrics.json"
DEFAULT_NEW_METRICS = "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_metrics.json"
DEFAULT_OUTPUT_DIR = "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded"


def main() -> None:
    args = parse_args()
    old_metrics = _read_json(Path(args.old_metrics))
    new_metrics = _read_json(Path(args.new_metrics))
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    comparison = build_comparison(old_metrics, new_metrics)
    json_path = out_dir / "preview_training_comparison.json"
    md_path = out_dir / "preview_training_comparison.md"
    json_path.write_text(json.dumps(comparison, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(comparison), encoding="utf-8")
    print(json.dumps({"comparison_json": str(json_path), "comparison_md": str(md_path)}, ensure_ascii=False, indent=2))


def build_comparison(old_metrics: dict[str, Any], new_metrics: dict[str, Any]) -> dict[str, Any]:
    interpretation = [
        "The expanded run uses more samples than the historical 10-sample preview and is therefore a more complete workflow sanity check.",
        "The result is still a compact phasor_RMS preview, not EMT and not a final dynamic performance conclusion.",
        "dynamic_stress_score is still a synthetic proxy target derived from compact dynamic measurements.",
        "Because the feature set also contains compact dynamic measurement quantities, the reported metrics can be optimistic and should not be treated as independent generalization evidence.",
        "A stricter next step should use an independent test set, more fault types, and target-feature leakage checks.",
    ]
    caveats = [
        "preview_only comparison",
        "phasor_RMS, not EMT",
        "generator_speed_proxy is not direct frequency",
        "handwired breaker is pilot breaker-like validation, not engineering-grade protection",
        "L12 remains excluded because it is a simulation_timeout / suspected islanding special case",
    ]
    return {
        "original_num_samples": int(old_metrics.get("num_samples", 0)),
        "expanded_num_samples": int(new_metrics.get("num_samples", 0)),
        "original_preview_only": bool(old_metrics.get("preview_only")),
        "expanded_preview_only": bool(new_metrics.get("preview_only")),
        "original_regression_metrics": old_metrics.get("regression_metrics", {}),
        "expanded_regression_metrics": new_metrics.get("regression_metrics", {}),
        "original_classification_metrics": old_metrics.get("classification_metrics", {}),
        "expanded_classification_metrics": new_metrics.get("classification_metrics", {}),
        "original_skipped_metrics_reason": old_metrics.get("skipped_metrics_reason", ""),
        "expanded_skipped_metrics_reason": new_metrics.get("skipped_metrics_reason", ""),
        "original_feature_columns": old_metrics.get("feature_columns", []),
        "expanded_feature_columns": new_metrics.get("feature_columns", []),
        "target_columns": new_metrics.get("target_columns", []),
        "cv_strategy": new_metrics.get("cv_strategy"),
        "random_seed": new_metrics.get("random_seed"),
        "interpretation": interpretation,
        "caveats": caveats,
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    old_reg = comparison["original_regression_metrics"]
    new_reg = comparison["expanded_regression_metrics"]
    old_cls = comparison["original_classification_metrics"] or {"skipped": comparison["original_skipped_metrics_reason"]}
    new_cls = comparison["expanded_classification_metrics"] or {"skipped": comparison["expanded_skipped_metrics_reason"]}
    interpretation = "\n".join(f"- {item}" for item in comparison["interpretation"])
    caveats = "\n".join(f"- {item}" for item in comparison["caveats"])
    return f"""# IEEE39 Expanded Preview Training Comparison

This comparison is preview-only. It is not a final dynamic performance conclusion.

| item | historical preview | expanded preview |
| --- | ---: | ---: |
| num_samples | {comparison['original_num_samples']} | {comparison['expanded_num_samples']} |
| preview_only | {comparison['original_preview_only']} | {comparison['expanded_preview_only']} |

## Regression Metrics

```json
{json.dumps({'historical': old_reg, 'expanded': new_reg}, ensure_ascii=False, indent=2)}
```

## Classification Metrics

```json
{json.dumps({'historical': old_cls, 'expanded': new_cls}, ensure_ascii=False, indent=2)}
```

## Interpretation

{interpretation}

## Caveats

{caveats}
"""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare historical and expanded IEEE39 preview reranker runs.")
    parser.add_argument("--old-metrics", default=DEFAULT_OLD_METRICS)
    parser.add_argument("--new-metrics", default=DEFAULT_NEW_METRICS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


if __name__ == "__main__":
    main()
