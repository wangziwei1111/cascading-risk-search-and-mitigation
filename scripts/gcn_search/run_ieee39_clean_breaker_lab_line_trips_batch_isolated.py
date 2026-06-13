from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from run_ieee39_clean_breaker_lab_line_trip_isolated import (
    SIGNAL_COLUMNS,
    SUMMARY_COLUMNS,
    ROOT,
    run_line,
)


DEFAULT_OUTPUT = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests"
DEFAULT_PATTERN = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab_{line_id}.slx"


def model_path_for(pattern: str, line_id: str) -> str:
    return pattern.format(line_id=line_id)


def validation_path_for(line_id: str) -> str:
    return "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_batch_validation_summary.csv"


def run_batch(line_ids: list[str], model_path_pattern: str, output_dir: Path, timeout_seconds: int, simulation_stop_time: float) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summaries = []
    signals = []
    events = []
    for line_id in line_ids:
        summary, signal, event = run_line(
            line_id=line_id,
            output_dir=output_dir,
            timeout_seconds=timeout_seconds,
            simulation_stop_time=simulation_stop_time,
            model_path=model_path_for(model_path_pattern, line_id),
            validation_summary_csv=validation_path_for(line_id),
        )
        summaries.append(summary)
        signals.append(signal)
        events.append(event)
        pd.DataFrame(summaries, columns=SUMMARY_COLUMNS).to_csv(output_dir / "ieee39_clean_breaker_lab_batch_line_trip_summary.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(signals, columns=SIGNAL_COLUMNS).to_csv(output_dir / "ieee39_clean_breaker_lab_batch_signal_summary.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(events).to_csv(output_dir / "ieee39_clean_breaker_lab_batch_event_log.csv", index=False, encoding="utf-8-sig")
    return (
        pd.DataFrame(summaries, columns=SUMMARY_COLUMNS),
        pd.DataFrame(signals, columns=SIGNAL_COLUMNS),
        pd.DataFrame(events),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run per-line IEEE39 clean lab trips in isolated MATLAB processes.")
    parser.add_argument("--line-ids", nargs="+", default=["L04", "L05"])
    parser.add_argument("--model-path-pattern", default=DEFAULT_PATTERN)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary, _, _ = run_batch(
        [line_id.upper() for line_id in args.line_ids],
        args.model_path_pattern,
        output_dir,
        args.timeout_seconds,
        args.simulation_stop_time,
    )
    print(summary[["test_case", "simulation_success", "training_ready_candidate", "measurement_extraction_status", "note"]].to_string(index=False))


if __name__ == "__main__":
    main()
