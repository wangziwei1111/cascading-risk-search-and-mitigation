"""Compare IEEE39 v1/v2 dynamic-aware preview runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rmse(metrics: dict[str, Any], split: str = "leave_one_out") -> float | None:
    if "metrics_by_split" in metrics:
        return metrics["metrics_by_split"].get(split, {}).get("regression", {}).get("rmse")
    return metrics.get("regression_metrics", {}).get("rmse")


def _provenance_count(metrics: dict[str, Any]) -> int:
    return int(metrics.get("provenance_check_required_rows", metrics.get("num_provenance_check_required_rows", 0)))


def build_comparison(
    v1: dict[str, Any],
    include_all: dict[str, Any],
    exclude: dict[str, Any],
    stricter: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    include_rmse = _rmse(include_all)
    exclude_rmse = _rmse(exclude)
    label_include = include_all.get("label_family_holdout_metrics", {})
    label_exclude = exclude.get("label_family_holdout_metrics", {})
    return {
        "preview_only": True,
        "final_performance_conclusion": False,
        "v1_expanded_num_samples": int(v1.get("num_samples", 0)),
        "v2_include_all_num_samples": int(include_all.get("num_samples", 0)),
        "v2_exclude_provenance_num_samples": int(exclude.get("num_samples", 0)),
        "non_line_trip_candidate_count": int(include_all.get("num_non_line_trip_candidate_rows", 0)),
        "provenance_excluded_count": int(_provenance_count(include_all) - _provenance_count(exclude)),
        "duplicate_measurement_groups": provenance.get("duplicate_measurement_groups", []),
        "v1_metrics": {
            "regression": v1.get("regression_metrics", {}),
            "classification": v1.get("classification_metrics", {}),
        },
        "v2_include_all_metrics": {
            "regression": include_all.get("regression_metrics", {}),
            "classification": include_all.get("classification_metrics", {}),
        },
        "v2_exclude_provenance_metrics": {
            "regression": exclude.get("regression_metrics", {}),
            "classification": exclude.get("classification_metrics", {}),
        },
        "label_family_holdout_metrics": {
            "include_all_candidates": label_include,
            "exclude_provenance_required": label_exclude,
        },
        "sensitivity_gap_include_vs_exclude": {
            "leave_one_out_rmse_include_all": include_rmse,
            "leave_one_out_rmse_exclude_provenance": exclude_rmse,
            "rmse_exclude_minus_include": None if include_rmse is None or exclude_rmse is None else float(exclude_rmse - include_rmse),
            "label_family_holdout_rmse_include_all": label_include.get("regression", {}).get("rmse"),
            "label_family_holdout_rmse_exclude_provenance": label_exclude.get("regression", {}).get("rmse"),
        },
        "stricter_comparison_reference": {
            "best_leaky_result": stricter.get("best_leaky_result", {}),
            "best_no_leakage_result": stricter.get("best_no_leakage_result", {}),
            "leakage_gap_summary": stricter.get("leakage_gap_summary", {}),
        },
        "interpretation": [
            "The v2 preview is a candidate schema sanity check only.",
            "include_all_candidates may be affected by NF06 duplicate/provenance risk.",
            "exclude_provenance_required is a sensitivity check that removes NF06.",
            "label_family_holdout is the closest current smoke check to training on line-trip labels and testing on non-line-trip labels.",
            "This is not a final dynamic performance conclusion.",
            "More independent non-line-trip fault types are needed, especially different-bus faults, load step, and generator trip.",
            "phasor_RMS, not EMT.",
            "generator_speed_proxy is not direct frequency.",
            "relay proxy is not engineering-grade protection.",
        ],
        "caveats": [
            "duplicate smoke candidates are not necessarily independent physical samples",
            "dynamic_stress_score is a compact proxy target",
            "measurement-derived features may be optimistic",
            "small sample preview only",
        ],
    }


def render_markdown(comparison: dict[str, Any]) -> str:
    interp = "\n".join(f"- {item}" for item in comparison["interpretation"])
    caveats = "\n".join(f"- {item}" for item in comparison["caveats"])
    return f"""# IEEE39 v2 Dynamic-Aware Preview Comparison

This comparison is preview-only and final_performance_conclusion=false.

```text
v1_expanded_num_samples: `{comparison['v1_expanded_num_samples']}`
v2_include_all_num_samples: `{comparison['v2_include_all_num_samples']}`
v2_exclude_provenance_num_samples: `{comparison['v2_exclude_provenance_num_samples']}`
provenance_excluded_count: `{comparison['provenance_excluded_count']}`
```

| item | value |
| --- | ---: |
| v1 expanded samples | {comparison['v1_expanded_num_samples']} |
| v2 include_all samples | {comparison['v2_include_all_num_samples']} |
| v2 exclude_provenance samples | {comparison['v2_exclude_provenance_num_samples']} |
| non-line-trip candidates | {comparison['non_line_trip_candidate_count']} |
| provenance excluded count | {comparison['provenance_excluded_count']} |

## Sensitivity Gap

```json
{json.dumps(comparison['sensitivity_gap_include_vs_exclude'], ensure_ascii=False, indent=2)}
```

## Label-Family Holdout Metrics

```json
{json.dumps(comparison['label_family_holdout_metrics'], ensure_ascii=False, indent=2)}
```

## Interpretation

{interp}

## Caveats

{caveats}
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1-expanded-metrics", type=Path, required=True)
    parser.add_argument("--v2-include-all-metrics", type=Path, required=True)
    parser.add_argument("--v2-exclude-provenance-metrics", type=Path, required=True)
    parser.add_argument("--stricter-comparison-metrics", type=Path, required=True)
    parser.add_argument("--duplicate-provenance-report", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comparison = build_comparison(
        _read_json(args.v1_expanded_metrics),
        _read_json(args.v2_include_all_metrics),
        _read_json(args.v2_exclude_provenance_metrics),
        _read_json(args.stricter_comparison_metrics),
        _read_json(args.duplicate_provenance_report),
    )
    out_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "v2_preview_comparison.json", comparison)
    (out_dir / "v2_preview_comparison.md").write_text(render_markdown(comparison), encoding="utf-8")
    print(json.dumps({"comparison_json": str(out_dir / "v2_preview_comparison.json"), "comparison_md": str(out_dir / "v2_preview_comparison.md")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
