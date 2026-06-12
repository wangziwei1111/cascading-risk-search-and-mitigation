from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODEL = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_clean_breaker_lab.slx"
DEFAULT_OUTPUT = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests"
DEFAULT_VALIDATION = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_validation_summary.csv"


SUMMARY_COLUMNS = [
    "test_case",
    "simulation_success",
    "physical_fault_or_breaker_action_executed",
    "schema_only",
    "simulation_mode",
    "trip_implementation",
    "fault_configuration_status",
    "measurement_extraction_status",
    "training_ready_candidate",
    "timeout_or_error_message",
    "fault_type",
    "fault_start_s",
    "fault_clear_s",
    "tripped_line",
    "relay_operated",
    "breaker_opened",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "signal_source_summary",
    "unstable_flag",
    "trip_time_s",
    "note",
    "source_model",
]

SIGNAL_COLUMNS = [
    "test_case",
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "measurement_extraction_status",
    "missing_signal_list",
    "voltage_source",
    "frequency_source",
    "speed_source",
    "rotor_angle_source",
    "num_voltage_signals_found",
    "num_speed_signals_found",
    "num_rotor_angle_signals_found",
    "signal_source_summary",
    "signal_note",
    "source_model",
]


def _run_with_process_tree_timeout(command: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    process = subprocess.Popen(
        ["matlab", "-batch", command],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
        completed = subprocess.CompletedProcess(process.args, process.returncode, stdout=stdout, stderr=stderr)
        if completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode,
                completed.args,
                output=completed.stdout,
                stderr=completed.stderr,
            )
        return completed
    except subprocess.TimeoutExpired:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        process.communicate()
        raise


def source_model_name(model_path: str, line_id: str) -> str:
    stem = Path(model_path).stem.lower()
    suffix = f"clean_breaker_lab_{line_id.lower()}"
    if suffix in stem:
        return f"clean_breaker_lab_{line_id.upper()}"
    return "clean_breaker_lab"


def timeout_summary(line_id: str, note: str, source_model: str = "clean_breaker_lab") -> pd.Series:
    return pd.Series(
        {
            "test_case": f"clean_lab_handwired_line_trip_{line_id}",
            "simulation_success": False,
            "physical_fault_or_breaker_action_executed": False,
            "schema_only": False,
            "simulation_mode": "graphical_simulink_phasor_RMS",
            "trip_implementation": "clean_lab_handwired_timed_breaker",
            "fault_configuration_status": "not_applicable",
            "measurement_extraction_status": "simulation_timeout",
            "training_ready_candidate": False,
            "timeout_or_error_message": note,
            "fault_type": "pilot_line_trip",
            "fault_start_s": 0.5,
            "fault_clear_s": 0.0,
            "tripped_line": line_id,
            "relay_operated": False,
            "breaker_opened": False,
            "min_voltage_pu": float("nan"),
            "max_voltage_pu": float("nan"),
            "min_frequency_hz": float("nan"),
            "max_frequency_hz": float("nan"),
            "max_speed_deviation": float("nan"),
            "max_rotor_angle_separation_deg": float("nan"),
            "signal_source_summary": "not_available; generator_speed_proxy not extracted because compact simulation did not complete",
            "unstable_flag": False,
            "trip_time_s": 0.5,
            "note": note,
            "source_model": source_model,
        }
    )


def timeout_signal(line_id: str, note: str, source_model: str = "clean_breaker_lab") -> pd.Series:
    return pd.Series(
        {
            "test_case": f"clean_lab_handwired_line_trip_{line_id}",
            "min_voltage_pu": float("nan"),
            "max_voltage_pu": float("nan"),
            "min_frequency_hz": float("nan"),
            "max_frequency_hz": float("nan"),
            "max_speed_deviation": float("nan"),
            "max_rotor_angle_separation_deg": float("nan"),
            "measurement_extraction_status": "simulation_timeout",
            "missing_signal_list": "simulation did not complete",
            "voltage_source": "not_available",
            "frequency_source": "generator_speed_proxy_not_extracted",
            "speed_source": "not_available",
            "rotor_angle_source": "not_available",
            "num_voltage_signals_found": 0,
            "num_speed_signals_found": 0,
            "num_rotor_angle_signals_found": 0,
            "signal_source_summary": "not_available; generator_speed_proxy not extracted because compact simulation did not complete",
            "signal_note": note,
            "source_model": source_model,
        }
    )


def timeout_event(line_id: str, note: str, source_model: str = "clean_breaker_lab") -> pd.Series:
    return pd.Series(
        {
            "test_case": f"clean_lab_handwired_line_trip_{line_id}",
            "event_time_s": 0.5,
            "event_type": "pilot_line_trip",
            "physical_executed": False,
            "event_note": note,
            "source_model": source_model,
        }
    )


def adapt_row(row: pd.Series, line_id: str, source_model: str = "clean_breaker_lab") -> pd.Series:
    adapted = row.copy()
    adapted["test_case"] = f"clean_lab_handwired_line_trip_{line_id}"
    adapted["source_model"] = source_model
    if boolish(adapted.get("simulation_success")) and adapted.get("measurement_extraction_status") == "voltage_speed_angle":
        adapted["training_ready_candidate"] = True
    else:
        adapted["training_ready_candidate"] = False
    return adapted


def boolish(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def run_line(
    line_id: str,
    output_dir: Path,
    timeout_seconds: int,
    simulation_stop_time: float,
    model_path: str = DEFAULT_MODEL,
    validation_summary_csv: str | None = None,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    source_model = source_model_name(model_path, line_id)
    if validation_summary_csv is None:
        validation_summary_csv = (
            f"../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_clean_breaker_lab_{line_id}_validation_summary.csv"
            if source_model != "clean_breaker_lab"
            else DEFAULT_VALIDATION
        )
    tmp_dir = output_dir / f"_clean_lab_isolated_{line_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_rel = tmp_dir.relative_to(ROOT).as_posix()
    command = (
        "cd('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); "
        "configure_ieee39_short_filegen_paths(); "
        "run_ieee39_multi_handwired_line_trip_suite("
        f"'{model_path}',"
        f"'../../{tmp_rel}',"
        f"string({{'{line_id}'}}),"
        f"{simulation_stop_time},"
        f"'{validation_summary_csv}',"
        f"{max(5, timeout_seconds - 30)}"
        ");"
    )
    try:
        _run_with_process_tree_timeout(command, timeout_seconds)
        summary_path = tmp_dir / "ieee39_multi_handwired_line_trip_summary.csv"
        signal_path = tmp_dir / "ieee39_multi_handwired_signal_summary.csv"
        event_path = tmp_dir / "ieee39_multi_handwired_event_log.csv"
        if not summary_path.exists():
            note = "isolated MATLAB run completed without summary"
            return timeout_summary(line_id, note, source_model), timeout_signal(line_id, note, source_model), timeout_event(line_id, note, source_model)
        summary = adapt_row(pd.read_csv(summary_path).iloc[0], line_id, source_model)
        signal = pd.read_csv(signal_path).iloc[0] if signal_path.exists() else timeout_signal(line_id, "missing isolated signal summary", source_model)
        signal["test_case"] = f"clean_lab_handwired_line_trip_{line_id}"
        signal["source_model"] = source_model
        event = pd.read_csv(event_path).iloc[0] if event_path.exists() else timeout_event(line_id, "missing isolated event log", source_model)
        event["test_case"] = f"clean_lab_handwired_line_trip_{line_id}"
        event["source_model"] = source_model
        return summary, signal, event
    except subprocess.TimeoutExpired:
        note = f"isolated MATLAB run timed out after {timeout_seconds} seconds; check {line_id} series wiring, bypass paths, short circuits, TripCommand target, Step direction, and abnormal Simscape islands"
        return timeout_summary(line_id, note, source_model), timeout_signal(line_id, note, source_model), timeout_event(line_id, note, source_model)
    except subprocess.CalledProcessError as exc:
        lines = (exc.stderr or exc.stdout or "").strip().splitlines()
        note = "isolated MATLAB run failed: " + (lines[-1] if lines else str(exc))
        return timeout_summary(line_id, note, source_model), timeout_signal(line_id, note, source_model), timeout_event(line_id, note, source_model)


def output_prefix(line_id: str, source_model: str) -> str:
    if source_model == "clean_breaker_lab":
        return "ieee39_clean_breaker_lab"
    return f"ieee39_clean_breaker_lab_{line_id}"


def write_outputs(output_dir: Path, summary: pd.Series, signal: pd.Series, event: pd.Series) -> None:
    line_id = str(summary.get("tripped_line", "L02"))
    prefix = output_prefix(line_id, str(summary.get("source_model", "clean_breaker_lab")))
    pd.DataFrame([summary], columns=SUMMARY_COLUMNS).to_csv(output_dir / f"{prefix}_line_trip_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([signal], columns=SIGNAL_COLUMNS).to_csv(output_dir / f"{prefix}_signal_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([event]).to_csv(output_dir / f"{prefix}_event_log.csv", index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one IEEE39 clean lab handwired line trip in an isolated MATLAB process.")
    parser.add_argument("--line-id", default="L02")
    parser.add_argument("--model-path", default=DEFAULT_MODEL)
    parser.add_argument("--validation-summary-csv", default=None)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary, signal, event = run_line(
        args.line_id,
        output_dir,
        args.timeout_seconds,
        args.simulation_stop_time,
        args.model_path,
        args.validation_summary_csv,
    )
    write_outputs(output_dir, summary, signal, event)
    print(
        pd.DataFrame(
            [summary],
            columns=["test_case", "simulation_success", "training_ready_candidate", "measurement_extraction_status", "note"],
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()
