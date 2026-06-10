from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import pandas as pd

from analyze_dynamic_instability_reasons import analyze_dynamic_instability_reasons
from analyze_relay_vs_security_events import analyze_relay_vs_security_events
from analyze_simulink_dynamic_results import analyze_simulink_dynamic_results
from compute_dynamic_stress_score import compute_dynamic_stress_score
from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases
from prepare_dynamic_negative_control_inputs import GROUPS, prepare_dynamic_negative_control_inputs


def run_dynamic_negative_control_pipeline(
    input_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_negative_controls",
    top_k: int = 20,
    run_matlab: bool = False,
    skip_matlab: bool = True,
    options_json_path: str = "results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json",
    basecase_path: str = "results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json",
    post_fault_options_json: str | None = None,
    low_risk_mode: str = "low_reranker_score",
) -> dict:
    out = Path(output_dir)
    input_dir = out / "inputs"
    cases_root = out / "cases"
    results_root = out / "results"
    options_json_path = _resolve_options_path(options_json_path, post_fault_options_json)
    is_post_fault = "recommended_post_fault_options" in str(options_json_path)
    summary_dir = Path("results/gcn_search/simulink_dynamic_negative_control_v3_summary") if is_post_fault else Path("results/gcn_search/simulink_dynamic_negative_control_summary")
    input_config = prepare_dynamic_negative_control_inputs(input_csv, input_dir, top_k=top_k, low_risk_mode=low_risk_mode)
    cases = {}
    for group, csv_path in input_config["outputs"].items():
        case_dir = cases_root / group
        export_simulink_dynamic_cases(SimulinkDynamicCaseExportConfig(input_csv=csv_path, output_dir=str(case_dir), top_k=(top_k,), method=group))
        cases[group] = str(case_dir)
    command_file = _write_matlab_command(out, basecase_path, cases_root, results_root, options_json_path)
    matlab_executed = False
    if run_matlab and not skip_matlab:
        matlab_exe = _find_matlab()
        if matlab_exe is None:
            raise RuntimeError("MATLAB executable not found; rerun with --skip-matlab.")
        result = subprocess.run([matlab_exe, "-batch", f"run('{command_file.as_posix()}')"], check=False)
        matlab_executed = True
        if result.returncode != 0:
            raise RuntimeError(f"MATLAB negative-control batch failed with return code {result.returncode}.")
    comparison_rows = []
    for group in GROUPS:
        group_cases = cases_root / group
        group_results = results_root / group
        dynamic_csv = group_results / "simulink_dynamic_simulation_results.csv"
        if not dynamic_csv.exists():
            continue
        analysis_dir = group_results / "dynamic_analysis"
        relay_dir = group_results / "relay_security_analysis"
        reason_dir = group_results / "instability_reasons"
        stress_csv = group_results / "dynamic_stress_score.csv"
        analyze_simulink_dynamic_results(dynamic_csv, group_cases / "simulink_topk_paths.csv", analysis_dir)
        relay_summary = analyze_relay_vs_security_events(dynamic_csv, str(group_results / "dynamic_case_event_log_*.csv"), relay_dir)["summary_csv"]
        reason = analyze_dynamic_instability_reasons(dynamic_csv, str(group_results / "dynamic_case_event_log_*.csv"), group_cases / "simulink_topk_paths.csv", reason_dir)
        stress = compute_dynamic_stress_score(dynamic_csv, stress_csv)
        precision = pd.read_csv(analysis_dir / "simulink_dynamic_precision_at_k.csv")
        p20 = precision[precision["top_k"] == 20].iloc[0]
        relay_table = _metric_table(pd.read_csv(relay_summary))
        comparison_rows.append(
            {
                "group": group,
                "num_cases": int(p20["num_simulated"]),
                "dynamic_precision_at_20": float(p20["dynamic_precision_at_k"]),
                "dynamic_unstable_count": int(p20["dynamic_unstable_count"]),
                "mean_frequency_nadir_hz": float(reason["frequency_nadir_hz_mean"]),
                "min_frequency_nadir_hz": float(reason["frequency_nadir_hz_min"]),
                "mean_rotor_angle_separation_deg": float(reason["max_rotor_angle_separation_deg_mean"]),
                "max_rotor_angle_separation_deg": float(reason["max_rotor_angle_separation_deg_max"]),
                "mean_dynamic_stress_score": float(stress["dynamic_stress_score"].mean()),
                "cases_with_security_redispatch_or_load_shed": int(relay_table.get("cases_with_security_redispatch_or_load_shed", 0)),
                "cases_with_passive_relay_trip": int(relay_table.get("cases_with_passive_relay_trip", 0)),
                "total_dynamic_load_shed_mw": float(relay_table.get("total_dynamic_load_shed_mw", 0.0)),
                "degeneracy_warning": bool(float(p20["dynamic_precision_at_k"]) in {0.0, 1.0}),
            }
        )
    summary = _write_summary(comparison_rows, summary_dir, matlab_executed, is_post_fault=is_post_fault)
    config = {"input_csv": str(input_csv), "output_dir": str(out), "top_k": top_k, "matlab_executed": matlab_executed, "command_file": str(command_file), "options_json_path": str(options_json_path), "low_risk_mode": low_risk_mode, "summary": summary}
    (out / "negative_control_pipeline_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def _write_summary(rows: list[dict], summary_dir: Path, matlab_executed: bool, is_post_fault: bool = False) -> dict:
    summary_dir.mkdir(parents=True, exist_ok=True)
    table = pd.DataFrame(rows)
    global_warning = bool(not table.empty and (table.loc[table["group"] != "learned_top20", "dynamic_precision_at_20"].astype(float) == 1.0).all())
    signal = False
    if not table.empty and "learned_top20" in set(table["group"]):
        learned = float(table.loc[table["group"] == "learned_top20", "mean_dynamic_stress_score"].iloc[0])
        controls = table[table["group"] != "learned_top20"]["mean_dynamic_stress_score"].astype(float)
        signal = bool(len(controls) and learned > controls.max())
    if not table.empty:
        table["global_degeneracy_warning"] = global_warning
        table["dynamic_discrimination_signal"] = signal
        table["matlab_executed"] = matlab_executed
    if is_post_fault and not table.empty:
        table = _v3_table(table)
        csv_path = summary_dir / "dynamic_negative_control_v3_comparison.csv"
        json_path = summary_dir / "dynamic_negative_control_v3_summary.json"
        brief_path = summary_dir / "dynamic_negative_control_v3_brief.md"
    else:
        csv_path = summary_dir / "dynamic_negative_control_comparison.csv"
        json_path = summary_dir / "dynamic_negative_control_comparison.json"
        brief_path = summary_dir / "dynamic_negative_control_brief.md"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    payload = {"global_degeneracy_warning": global_warning, "dynamic_discrimination_signal": signal, "matlab_executed": matlab_executed, "num_groups": int(len(table))}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    brief_path.write_text(_brief(table, payload), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), "brief": str(brief_path), **payload}


def _v3_table(table: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()
    out["group"] = table["group"]
    out["num_cases"] = table["num_cases"]
    out["unstable_fraction_default_threshold"] = table["dynamic_precision_at_20"]
    out["unstable_fraction_post_fault_calibrated"] = table["dynamic_precision_at_20"]
    out["mean_frequency_nadir_hz"] = table["mean_frequency_nadir_hz"]
    out["mean_rotor_angle_separation_coi_deg"] = table["mean_rotor_angle_separation_deg"]
    out["mean_dynamic_stress_score"] = table["mean_dynamic_stress_score"]
    out["passive_trip_fraction"] = table["cases_with_passive_relay_trip"] / table["num_cases"].clip(lower=1)
    out["security_action_fraction"] = table["cases_with_security_redispatch_or_load_shed"] / table["num_cases"].clip(lower=1)
    learned_stress = float(table.loc[table["group"] == "learned_top20", "mean_dynamic_stress_score"].iloc[0]) if "learned_top20" in set(table["group"]) else 0.0
    out["learned_vs_control_stress_delta"] = [0.0 if group == "learned_top20" else learned_stress - float(stress) for group, stress in zip(table["group"], table["mean_dynamic_stress_score"])]
    controls = out[out["group"] != "learned_top20"]
    global_warning = bool(not controls.empty and (controls["unstable_fraction_post_fault_calibrated"].astype(float) == 1.0).all())
    out["global_degeneracy_warning"] = global_warning
    out["sanity_ladder_passed"] = not global_warning
    out["dynamic_discrimination_signal"] = bool((not global_warning) and len(controls) and learned_stress > float(controls["mean_dynamic_stress_score"].max()))
    return out


def _resolve_options_path(options_json_path: str, post_fault_options_json: str | None) -> str:
    if post_fault_options_json and Path(post_fault_options_json).exists():
        return post_fault_options_json
    default_post = Path("results/gcn_search/simulink_dynamic_calibration/recommended_post_fault_options.json")
    if default_post.exists():
        return str(default_post)
    return options_json_path


def _brief(table: pd.DataFrame, payload: dict) -> str:
    lines = ["# Dynamic Negative Control Brief", "", f"global_degeneracy_warning = {payload['global_degeneracy_warning']}", f"dynamic_discrimination_signal = {payload['dynamic_discrimination_signal']}", "", "| group | unstable fraction | passive fraction/trips | security fraction/actions | mean stress |", "| --- | ---: | ---: | ---: | ---: |"]
    for _, row in table.iterrows():
        unstable = float(row.get("dynamic_precision_at_20", row.get("unstable_fraction_post_fault_calibrated", 0.0)))
        passive = float(row.get("cases_with_passive_relay_trip", row.get("passive_trip_fraction", 0.0)))
        security = float(row.get("cases_with_security_redispatch_or_load_shed", row.get("security_action_fraction", 0.0)))
        lines.append(f"| {row['group']} | {unstable:.4f} | {passive:.4f} | {security:.4f} | {float(row['mean_dynamic_stress_score']):.4f} |")
    lines.append("")
    lines.append("No dynamic recall is reported because no full dynamic truth is available.")
    return "\n".join(lines)


def _write_matlab_command(out: Path, basecase_path: str, cases_root: Path, results_root: Path, options_json_path: str) -> Path:
    command_file = out / "run_matlab_negative_controls.m"
    matlab_dir = Path(__file__).resolve().parents[3] / "matlab" / "simulink_rts79"
    command_file.parent.mkdir(parents=True, exist_ok=True)
    command_file.write_text(
        "\n".join(
            [
                "% Auto-generated negative-control dynamic validation command.",
                f'cd("{matlab_dir.as_posix()}")',
                "run_dynamic_negative_control_batch( ...",
                f'  "{_matlab_rel(basecase_path)}", ...',
                f'  "{_matlab_rel(cases_root)}", ...',
                f'  "{_matlab_rel(results_root)}", ...',
                f'  "{_matlab_rel(options_json_path)}", ...',
                "  20 ...",
                ");",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return command_file


def _matlab_rel(path_like: str | Path) -> str:
    path = Path(path_like)
    if path.is_absolute():
        return path.as_posix()
    return (Path("..") / ".." / path).as_posix()


def _find_matlab() -> str | None:
    for candidate in ["matlab", r"E:\matlab2025a\bin\matlab.exe"]:
        found = shutil.which(candidate) if candidate == "matlab" else candidate
        if found and Path(found).exists():
            return found
    return None


def _metric_table(table: pd.DataFrame) -> dict[str, float]:
    return {str(row["metric"]): float(row["value"]) for _, row in table.iterrows()} if {"metric", "value"}.issubset(table.columns) else {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run dynamic negative-control pipeline.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_negative_controls")
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--run-matlab", action="store_true")
    parser.add_argument("--skip-matlab", action="store_true")
    parser.add_argument("--options-json-path", default="results/gcn_search/simulink_dynamic_calibration/recommended_event_driven_options.json")
    parser.add_argument("--post-fault-options-json")
    parser.add_argument("--low-risk-mode", choices=["low_reranker_score", "combined_low_stress"], default="low_reranker_score")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dynamic_negative_control_pipeline(args.input_csv, args.output_dir, args.top_k, args.run_matlab, args.skip_matlab or not args.run_matlab, args.options_json_path, post_fault_options_json=args.post_fault_options_json, low_risk_mode=args.low_risk_mode)


if __name__ == "__main__":
    main()
