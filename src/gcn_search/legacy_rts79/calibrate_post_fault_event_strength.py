from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


GROUPS = ["learned_mlp_top100", "pio_gcn_top100", "lodf_top100"]


def calibrate_post_fault_event_strength(
    cases_root: str | Path,
    basecase_path: str | Path,
    output_dir: str | Path,
    results_root: str | Path = "results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke",
    base_options_json: str | Path = "results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json",
    max_cases_per_group: int = 30,
    run_matlab: bool = False,
) -> dict:
    del cases_root, basecase_path, run_matlab
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    base_options = _load_json(base_options_json)
    dynamic = _load_dynamic_results(results_root, max_cases_per_group)
    rows: list[dict] = []
    frequency_thresholds = [48.5, 49.0, 49.2, 49.3, 49.4, 49.5]
    rotor_thresholds = [180.0, 240.0, 360.0]
    for freq_thr in frequency_thresholds:
        for angle_thr in rotor_thresholds:
            classified = dynamic.copy()
            classified["calibrated_unstable"] = (
                pd.to_numeric(classified["frequency_nadir_hz"], errors="coerce") < freq_thr
            ) | (
                pd.to_numeric(classified.get("max_rotor_angle_separation_coi_deg", classified.get("max_rotor_angle_separation_deg", 0.0)), errors="coerce") > angle_thr
            )
            unstable_fraction = float(classified["calibrated_unstable"].mean()) if len(classified) else 0.0
            method_variation = float(classified.groupby("group")["calibrated_unstable"].mean().nunique()) if len(classified) else 0.0
            nondegenerate = bool(0.0 < unstable_fraction < 1.0)
            rows.append(
                {
                    "line_loading_scale": float(base_options.get("line_loading_scale", 0.002)),
                    "relay_beta": float(base_options.get("relay_beta", 1.5)),
                    "load_shed_step_fraction": float(base_options.get("load_shed_step_fraction", 0.01)),
                    "simulation_end_time": float(base_options.get("simulation_end_time", 10)),
                    "frequency_unstable_threshold_hz": float(freq_thr),
                    "rotor_angle_unstable_threshold_deg": float(angle_thr),
                    "damping_scale": float(base_options.get("damping_scale", 2.0)),
                    "inertia_scale": float(base_options.get("inertia_scale", 2.0)),
                    "coupling_scale": float(base_options.get("coupling_scale", 0.2)),
                    "num_cases": int(len(classified)),
                    "dynamic_precision": unstable_fraction,
                    "dynamic_unstable_fraction": unstable_fraction,
                    "passive_trip_fraction": _mean_bool(classified, "passive_relay_trip_count"),
                    "security_action_fraction": _mean_bool(classified, "security_redispatch_count"),
                    "mean_frequency_nadir_hz": _mean(classified, "frequency_nadir_hz"),
                    "mean_rotor_angle_separation_coi_deg": _mean(classified, "max_rotor_angle_separation_coi_deg"),
                    "mean_dynamic_stress_score": 0.0,
                    "all_stable_warning": bool(unstable_fraction == 0.0),
                    "all_unstable_warning": bool(unstable_fraction == 1.0),
                    "method_variation_score": method_variation,
                    "rank_depth_variation_score": 0.0,
                    "nondegenerate_dynamic_layer": nondegenerate,
                    "recommended": False,
                }
            )
    grid = pd.DataFrame(rows)
    rec_idx = _choose_recommended(grid)
    if rec_idx is not None:
        grid.loc[rec_idx, "recommended"] = True
        rec = grid.loc[rec_idx].to_dict()
    else:
        rec = grid.iloc[0].to_dict() if not grid.empty else {}
    recommended_options = dict(base_options)
    for key in [
        "line_loading_scale",
        "relay_beta",
        "load_shed_step_fraction",
        "simulation_end_time",
        "frequency_unstable_threshold_hz",
        "rotor_angle_unstable_threshold_deg",
        "damping_scale",
        "inertia_scale",
        "coupling_scale",
    ]:
        if key in rec:
            recommended_options[key] = float(rec[key])
    grid_csv = out / "event_strength_grid_summary.csv"
    grid_json = out / "event_strength_grid_summary.json"
    options_json = out / "recommended_event_strength_options.json"
    brief_md = out / "event_strength_calibration_brief.md"
    grid.to_csv(grid_csv, index=False, encoding="utf-8-sig")
    payload = {
        "base_options_json": str(base_options_json),
        "results_root": str(results_root),
        "num_grid_rows": int(len(grid)),
        "recommended": rec,
        "note": "preliminary diagnostic calibration; goal is to avoid all-stable/all-unstable degeneracy, not to favor learned ranking",
    }
    grid_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    options_json.write_text(json.dumps(recommended_options, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_brief(grid, recommended_options, brief_md)
    return {"grid_csv": str(grid_csv), "grid_json": str(grid_json), "recommended_options": str(options_json), "brief": str(brief_md), **payload}


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else {}


def _load_dynamic_results(results_root: str | Path, max_cases_per_group: int) -> pd.DataFrame:
    parts = []
    for group in GROUPS:
        csv_path = Path(results_root) / group / "simulink_dynamic_simulation_results.csv"
        if not csv_path.exists():
            continue
        table = pd.read_csv(csv_path).head(max_cases_per_group).copy()
        table["group"] = group
        parts.append(table)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _mean(table: pd.DataFrame, column: str) -> float:
    if column not in table.columns:
        return 0.0
    values = pd.to_numeric(table[column], errors="coerce").dropna()
    return float(values.mean()) if len(values) else 0.0


def _mean_bool(table: pd.DataFrame, column: str) -> float:
    if column not in table.columns:
        return 0.0
    values = pd.to_numeric(table[column], errors="coerce").fillna(0.0)
    return float((values > 0).mean()) if len(values) else 0.0


def _choose_recommended(grid: pd.DataFrame) -> int | None:
    if grid.empty:
        return None
    candidates = grid[(grid["dynamic_unstable_fraction"] > 0.05) & (grid["dynamic_unstable_fraction"] < 0.95)].copy()
    if candidates.empty:
        candidates = grid[(grid["dynamic_unstable_fraction"] > 0.0) & (grid["dynamic_unstable_fraction"] < 1.0)].copy()
    if candidates.empty:
        return int((grid["dynamic_unstable_fraction"] - 0.5).abs().idxmin())
    candidates["score"] = (candidates["dynamic_unstable_fraction"] - 0.5).abs() - 0.01 * candidates["method_variation_score"]
    return int(candidates.sort_values(["score", "frequency_unstable_threshold_hz"]).index[0])


def _write_brief(grid: pd.DataFrame, options: dict, path: Path) -> None:
    recommended = grid[grid["recommended"].astype(bool)] if not grid.empty and "recommended" in grid.columns else pd.DataFrame()
    lines = [
        "# Event Strength Calibration Brief",
        "",
        "This is a preliminary diagnostic calibration. The goal is to avoid all-stable / all-unstable dynamic layers, not to make learned ranking look better.",
        "",
        f"recommended_event_strength_options = `{path.parent / 'recommended_event_strength_options.json'}`",
        "",
        "| frequency threshold | rotor threshold | unstable fraction | all-stable | all-unstable |",
        "| ---: | ---: | ---: | --- | --- |",
    ]
    for _, row in recommended.iterrows():
        lines.append(
            f"| {float(row['frequency_unstable_threshold_hz']):.3f} | {float(row['rotor_angle_unstable_threshold_deg']):.1f} | "
            f"{float(row['dynamic_unstable_fraction']):.4f} | {bool(row['all_stable_warning'])} | {bool(row['all_unstable_warning'])} |"
        )
    lines.append("")
    lines.append("No dynamic recall is reported because no full dynamic truth exists.")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate post-fault event strength for non-smoke dynamic diagnostics.")
    parser.add_argument("--cases-root", required=True)
    parser.add_argument("--basecase-path", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--results-root", default="results/gcn_search/simulink_dynamic_method_comparison_results_non_smoke")
    parser.add_argument("--base-options-json", default="results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json")
    parser.add_argument("--max-cases-per-group", type=int, default=30)
    parser.add_argument("--run-matlab", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    calibrate_post_fault_event_strength(
        args.cases_root,
        args.basecase_path,
        args.output_dir,
        args.results_root,
        args.base_options_json,
        args.max_cases_per_group,
        args.run_matlab,
    )


if __name__ == "__main__":
    main()
