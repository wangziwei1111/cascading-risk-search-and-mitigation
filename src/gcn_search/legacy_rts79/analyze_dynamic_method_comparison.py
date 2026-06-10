from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from analyze_dynamic_instability_reasons import analyze_dynamic_instability_reasons
from analyze_relay_vs_security_events import analyze_relay_vs_security_events
from analyze_simulink_dynamic_results import analyze_simulink_dynamic_results
from compute_dynamic_stress_score import compute_dynamic_stress_score


GROUPS = ["learned_mlp_top50", "learned_mlp_top100", "pio_gcn_top50", "pio_gcn_top100", "lodf_top50", "lodf_top100"]


def analyze_dynamic_method_comparison(
    cases_root: str | Path,
    results_root: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_method_comparison_summary",
    options_json: str | Path | None = None,
    summary_prefix: str = "dynamic_method_comparison",
    dataset_stats_json: str | Path | None = None,
    model_summary_json: str | Path | None = None,
) -> dict:
    cases_root = Path(cases_root)
    results_root = Path(results_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    stress_parts: list[pd.DataFrame] = []
    for group in GROUPS:
        case_dir = cases_root / group
        result_dir = results_root / group
        dynamic_csv = result_dir / "simulink_dynamic_simulation_results.csv"
        topk_csv = case_dir / "simulink_topk_paths.csv"
        if not dynamic_csv.exists() or not topk_csv.exists():
            continue
        analysis_dir = result_dir / "dynamic_analysis"
        relay_dir = result_dir / "relay_security_analysis"
        reason_dir = result_dir / "instability_reasons"
        stress_csv = result_dir / "dynamic_stress_score.csv"
        analyze_simulink_dynamic_results(dynamic_csv, topk_csv, analysis_dir)
        relay_summary_csv = analyze_relay_vs_security_events(dynamic_csv, str(result_dir / "dynamic_case_event_log_*.csv"), relay_dir)["summary_csv"]
        reason = analyze_dynamic_instability_reasons(dynamic_csv, str(result_dir / "dynamic_case_event_log_*.csv"), topk_csv, reason_dir)
        stress = compute_dynamic_stress_score(dynamic_csv, stress_csv)
        stress["group"] = group
        stress_parts.append(stress)
        precision = pd.read_csv(analysis_dir / "simulink_dynamic_precision_at_k.csv")
        method, top_k = _parse_group(group)
        p_row = precision[precision["top_k"] == top_k]
        if p_row.empty:
            p_row = precision.iloc[[0]]
        p = p_row.iloc[0]
        relay = _metric_table(pd.read_csv(relay_summary_csv))
        overlap = _metric_table(pd.read_csv(analysis_dir / "simulink_opa_dynamic_overlap.csv"))
        rows.append(
            {
                "method": method,
                "top_k": top_k,
                "num_cases": int(p["num_simulated"]),
                "dynamic_unstable_count": int(p["dynamic_unstable_count"]),
                "dynamic_precision_at_k": float(p["dynamic_precision_at_k"]),
                "mean_frequency_nadir_hz": float(reason["frequency_nadir_hz_mean"]),
                "min_frequency_nadir_hz": float(reason["frequency_nadir_hz_min"]),
                "mean_rotor_angle_separation_coi_deg": float(reason["max_rotor_angle_separation_deg_mean"]),
                "max_rotor_angle_separation_coi_deg": float(reason["max_rotor_angle_separation_deg_max"]),
                "mean_dynamic_stress_score": float(stress["dynamic_stress_score"].mean()),
                "median_dynamic_stress_score": float(stress["dynamic_stress_score"].median()),
                "cases_with_security_redispatch_or_load_shed": int(relay.get("cases_with_security_redispatch_or_load_shed", 0)),
                "cases_with_passive_relay_trip": int(relay.get("cases_with_passive_relay_trip", 0)),
                "total_dynamic_load_shed_mw": float(relay.get("total_dynamic_load_shed_mw", 0.0)),
                "opa_critical_and_dynamic_unstable_count": int(overlap.get("opa_critical_and_dynamic_unstable_count", 0)),
                "opa_noncritical_but_dynamic_unstable_count": int(overlap.get("opa_noncritical_but_dynamic_unstable_count", 0)),
            }
        )
    summary = pd.DataFrame(rows)
    calibration_warning = _calibration_warning(summary)
    signal = _diagnostic_signal(summary)
    extra = _load_extra_metadata(dataset_stats_json, model_summary_json)
    if not summary.empty:
        summary["calibration_warning"] = calibration_warning
        summary["dynamic_discrimination_signal"] = signal
        for key, value in extra.items():
            summary[key] = value
    summary_csv = out / f"{summary_prefix}_summary.csv"
    summary_json = out / f"{summary_prefix}_summary.json"
    brief_md = out / f"{summary_prefix}_brief.md"
    stress_rank_csv = out / f"{summary_prefix}_stress_ranks.csv"
    summary.to_csv(summary_csv, index=False, encoding="utf-8-sig")
    payload = {
        "options_json": str(options_json) if options_json else None,
        "num_rows": int(len(summary)),
        "calibration_warning": calibration_warning,
        "dynamic_discrimination_signal": signal,
        **extra,
        "note": "preliminary diagnostic comparison only; no dynamic recall is reported",
    }
    summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _brief(summary, payload, brief_md)
    if stress_parts:
        stress_all = pd.concat(stress_parts, ignore_index=True)
        stress_all.sort_values(["group", "dynamic_stress_score"], ascending=[True, False]).to_csv(stress_rank_csv, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame().to_csv(stress_rank_csv, index=False)
    return {"summary_csv": str(summary_csv), "summary_json": str(summary_json), "brief": str(brief_md), "stress_ranks": str(stress_rank_csv), **payload}


def _parse_group(group: str) -> tuple[str, int]:
    if group.endswith("_top50"):
        return group.removesuffix("_top50"), 50
    if group.endswith("_top100"):
        return group.removesuffix("_top100"), 100
    return group, 0


def _metric_table(table: pd.DataFrame) -> dict[str, float]:
    return {str(row["metric"]): float(row["value"]) for _, row in table.iterrows()} if {"metric", "value"}.issubset(table.columns) else {}


def _calibration_warning(summary: pd.DataFrame) -> bool:
    top100 = summary[summary["top_k"] == 100] if not summary.empty else summary
    if top100.empty:
        return True
    precision = top100["dynamic_precision_at_k"].astype(float)
    return bool((precision == 0.0).all() or (precision == 1.0).all())


def _diagnostic_signal(summary: pd.DataFrame) -> bool:
    top100 = summary[summary["top_k"] == 100] if not summary.empty else summary
    if top100.empty or "learned_mlp" not in set(top100["method"]):
        return False
    learned = float(top100.loc[top100["method"] == "learned_mlp", "mean_dynamic_stress_score"].iloc[0])
    controls = top100.loc[top100["method"] != "learned_mlp", "mean_dynamic_stress_score"].astype(float)
    return bool(len(controls) and learned > controls.max() * 1.05)


def _load_json(path: str | Path | None) -> dict:
    if path is None or not Path(path).exists():
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _load_extra_metadata(dataset_stats_json: str | Path | None, model_summary_json: str | Path | None) -> dict:
    dataset = _load_json(dataset_stats_json)
    model = _load_json(model_summary_json)
    extra: dict[str, object] = {}
    mapping = {
        "dataset_source": dataset.get("dataset_source"),
        "dataset_scale": dataset.get("dataset_scale"),
        "num_dataset_samples": dataset.get("num_samples"),
        "num_dataset_positives": dataset.get("num_critical"),
        "positive_ratio": dataset.get("positive_ratio"),
        "model_auc": model.get("test_auc"),
        "model_ap": model.get("test_average_precision"),
    }
    for key, value in mapping.items():
        if value is not None:
            extra[key] = value
    return extra


def _brief(summary: pd.DataFrame, payload: dict, path: Path) -> None:
    lines = [
        "# Dynamic Method Comparison Brief",
        "",
        "This is a preliminary diagnostic comparison only, not a formal dynamic stability conclusion.",
        f"calibration_warning = {payload['calibration_warning']}",
        f"dynamic_discrimination_signal = {payload['dynamic_discrimination_signal']}",
        "",
        "| method | top_k | dynamic_precision | mean stress | passive trips | security actions |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['method']} | {int(row['top_k'])} | {float(row['dynamic_precision_at_k']):.4f} | "
            f"{float(row['mean_dynamic_stress_score']):.4f} | {int(row['cases_with_passive_relay_trip'])} | "
            f"{int(row['cases_with_security_redispatch_or_load_shed'])} |"
        )
    lines.append("")
    lines.append("No dynamic recall is reported because no full dynamic truth is available.")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze dynamic method comparison batches.")
    parser.add_argument("--cases-root", required=True)
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_method_comparison_summary")
    parser.add_argument("--options-json")
    parser.add_argument("--summary-prefix", default="dynamic_method_comparison")
    parser.add_argument("--dataset-stats-json")
    parser.add_argument("--model-summary-json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_dynamic_method_comparison(
        args.cases_root,
        args.results_root,
        args.output_dir,
        args.options_json,
        args.summary_prefix,
        args.dataset_stats_json,
        args.model_summary_json,
    )


if __name__ == "__main__":
    main()
