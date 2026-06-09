from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from analyze_relay_vs_security_events import analyze_relay_vs_security_events
from analyze_simulink_dynamic_results import analyze_simulink_dynamic_results
from export_path_reranker_per_path_ranking import PathRerankerPerPathExportConfig, export_path_reranker_per_path_ranking
from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases
from prepare_real_topk_for_simulink_dynamic import RealTopKPreparationConfig, prepare_real_topk_for_simulink_dynamic


@dataclass(frozen=True)
class RealTopKDynamicPipelineConfig:
    output_dir: str = "results/gcn_search/simulink_dynamic_real_pipeline"
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    model_dir: str = "results/gcn_search/path_reranker_models"
    method: str = "learned_mlp_reranker_strict"
    split: str = "test"
    top_k: tuple[int, ...] = (20, 50, 100)
    max_cases: int | None = 20
    run_matlab: bool = False
    skip_matlab: bool = True
    retrain_if_missing: bool = False
    basecase_path: str = "results/gcn_search/simulink_dynamic_basecase/rts79_simulink_basecase.json"
    options_json_path: str = "results/gcn_search/simulink_dynamic_calibration/recommended_swing_options.json"


def run_real_topk_dynamic_validation_pipeline(config: RealTopKDynamicPipelineConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    per_path_dir = out / "per_path_ranking"
    real_topk_dir = out / "real_topk"
    cases_dir = out / "dynamic_cases"
    dynamic_results_dir = out / "dynamic_results"
    analysis_dir = out / "dynamic_analysis"
    relay_analysis_dir = out / "relay_security_analysis"

    per_path = export_path_reranker_per_path_ranking(
        PathRerankerPerPathExportConfig(
            dataset_dir=config.dataset_dir,
            model_dir=config.model_dir,
            output_dir=str(per_path_dir),
            method=config.method,
            split=config.split,
            top_k=config.top_k,
            retrain_if_missing=config.retrain_if_missing,
        )
    )
    per_path_csv = Path(per_path["output_csv"])
    if config.max_cases is not None:
        limited_csv = out / "learned_mlp_per_path_ranking_limited.csv"
        pd.read_csv(per_path_csv).head(config.max_cases).to_csv(limited_csv, index=False, encoding="utf-8-sig")
        per_path_csv = limited_csv

    prepare_real_topk_for_simulink_dynamic(
        RealTopKPreparationConfig(
            output_dir=str(real_topk_dir),
            input_csv=str(per_path_csv),
            method=config.method,
            top_k=config.top_k,
            use_demo_fallback=False,
        )
    )
    export_simulink_dynamic_cases(
        SimulinkDynamicCaseExportConfig(
            input_csv=str(real_topk_dir / "real_topk_input_paths.csv"),
            output_dir=str(cases_dir),
            top_k=config.top_k,
            method=config.method,
            make_demo_cases=False,
        )
    )
    matlab_command_file = _write_matlab_command_file(config, out, cases_dir, dynamic_results_dir)
    matlab_executed = False
    matlab_returncode: int | None = None
    if config.run_matlab and not config.skip_matlab:
        matlab_exe = _find_matlab()
        if matlab_exe is None:
            raise RuntimeError("MATLAB executable not found; rerun with --skip-matlab to generate inputs only.")
        result = subprocess.run([matlab_exe, "-batch", f"run('{matlab_command_file.as_posix()}')"], check=False)
        matlab_executed = True
        matlab_returncode = int(result.returncode)
        if result.returncode != 0:
            raise RuntimeError(f"MATLAB dynamic validation failed with return code {result.returncode}.")

    analysis_outputs: dict[str, str] = {}
    dynamic_results_csv = dynamic_results_dir / "simulink_dynamic_simulation_results.csv"
    if dynamic_results_csv.exists():
        analysis_outputs.update(
            analyze_simulink_dynamic_results(dynamic_results_csv, cases_dir / "simulink_topk_paths.csv", analysis_dir)
        )
        analysis_outputs["relay_security"] = analyze_relay_vs_security_events(
            dynamic_results_csv,
            str(dynamic_results_dir / "dynamic_case_event_log_*.csv"),
            relay_analysis_dir,
        )["summary_csv"]

    payload = {
        **asdict(config),
        "per_path_csv": str(per_path_csv),
        "real_topk_input_csv": str(real_topk_dir / "real_topk_input_paths.csv"),
        "matlab_batch_input": str(cases_dir / "matlab_batch_input.csv"),
        "matlab_command_file": str(matlab_command_file),
        "matlab_executed": bool(matlab_executed),
        "matlab_returncode": matlab_returncode,
        "analysis_outputs": analysis_outputs,
        "note": "If MATLAB is skipped, this pipeline generated inputs and a command file only; no dynamic precision is available yet.",
    }
    (out / "real_topk_dynamic_pipeline_config.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _write_matlab_command_file(config: RealTopKDynamicPipelineConfig, out: Path, cases_dir: Path, dynamic_results_dir: Path) -> Path:
    command_file = out / "run_matlab_real_topk_dynamic_validation.m"
    basecase = _matlab_rel(config.basecase_path)
    batch = _matlab_rel(cases_dir / "matlab_batch_input.csv")
    result_dir = _matlab_rel(dynamic_results_dir)
    options = _matlab_rel(config.options_json_path)
    command_file.write_text(
        "\n".join(
            [
                "% Auto-generated by run_real_topk_dynamic_validation_pipeline.py.",
                "cd matlab/simulink_rts79",
                "run_real_topk_event_driven_dynamic_validation( ...",
                f'  "{basecase}", ...',
                f'  "{batch}", ...',
                f'  "{result_dir}", ...',
                f'  "{options}", ...',
                "  false ...",
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run real learned-reranker Top-K event-driven dynamic validation pipeline.")
    parser.add_argument("--output-dir", default=RealTopKDynamicPipelineConfig.output_dir)
    parser.add_argument("--dataset-dir", default=RealTopKDynamicPipelineConfig.dataset_dir)
    parser.add_argument("--model-dir", default=RealTopKDynamicPipelineConfig.model_dir)
    parser.add_argument("--method", default=RealTopKDynamicPipelineConfig.method)
    parser.add_argument("--split", default=RealTopKDynamicPipelineConfig.split)
    parser.add_argument("--top-k", nargs="+", type=int, default=[20, 50, 100])
    parser.add_argument("--max-cases", type=int, default=20)
    parser.add_argument("--run-matlab", action="store_true")
    parser.add_argument("--skip-matlab", action="store_true")
    parser.add_argument("--retrain-if-missing", action="store_true")
    parser.add_argument("--basecase-path", default=RealTopKDynamicPipelineConfig.basecase_path)
    parser.add_argument("--options-json-path", default=RealTopKDynamicPipelineConfig.options_json_path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_real_topk_dynamic_validation_pipeline(
        RealTopKDynamicPipelineConfig(
            output_dir=args.output_dir,
            dataset_dir=args.dataset_dir,
            model_dir=args.model_dir,
            method=args.method,
            split=args.split,
            top_k=tuple(args.top_k),
            max_cases=args.max_cases,
            run_matlab=args.run_matlab,
            skip_matlab=args.skip_matlab or not args.run_matlab,
            retrain_if_missing=args.retrain_if_missing,
            basecase_path=args.basecase_path,
            options_json_path=args.options_json_path,
        )
    )


if __name__ == "__main__":
    main()
