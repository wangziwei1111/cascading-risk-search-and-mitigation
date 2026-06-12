from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MATLAB_DIR = ROOT / "matlab/simulink_ieee39"
DEFAULT_MODEL = "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx"
DEFAULT_OUTPUT = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/fault_tests"
DEFAULT_VALIDATION = "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/ieee39_multi_handwired_breaker_validation_summary.csv"


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
        completed = subprocess.CompletedProcess(
            process.args,
            process.returncode,
            stdout=stdout,
            stderr=stderr,
        )
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


def run_line(line_id: str, output_dir: Path, timeout_seconds: int, simulation_stop_time: float) -> tuple[pd.Series, pd.Series, pd.Series]:
    tmp_dir = output_dir / f"_isolated_{line_id}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    command = (
        "cd('C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39'); "
        "configure_ieee39_short_filegen_paths(); "
        "run_ieee39_multi_handwired_line_trip_suite("
        f"'{DEFAULT_MODEL}',"
        f"'../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/_isolated_{line_id}',"
        f"string({{'{line_id}'}}),"
        f"{simulation_stop_time},"
        f"'{DEFAULT_VALIDATION}',"
        f"{max(5, timeout_seconds - 30)}"
        ");"
    )
    try:
        _run_with_process_tree_timeout(command, timeout_seconds)
        summary_path = tmp_dir / "ieee39_multi_handwired_line_trip_summary.csv"
        signal_path = tmp_dir / "ieee39_multi_handwired_signal_summary.csv"
        event_path = tmp_dir / "ieee39_multi_handwired_event_log.csv"
        if summary_path.exists():
            summary = pd.read_csv(summary_path).iloc[0]
            signal = pd.read_csv(signal_path).iloc[0] if signal_path.exists() else timeout_signal(line_id, "missing isolated signal summary")
            event = pd.read_csv(event_path).iloc[0] if event_path.exists() else timeout_event(line_id, "missing isolated event log")
            return summary, signal, event
        return timeout_summary(line_id, "isolated MATLAB run completed without summary"), timeout_signal(line_id, "missing isolated summary"), timeout_event(line_id, "missing isolated summary")
    except subprocess.TimeoutExpired:
        note = f"isolated MATLAB run timed out after {timeout_seconds} seconds"
        return timeout_summary(line_id, note), timeout_signal(line_id, note), timeout_event(line_id, note)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip().splitlines()
        note = "isolated MATLAB run failed: " + (stderr[-1] if stderr else str(exc))
        return timeout_summary(line_id, note), timeout_signal(line_id, note), timeout_event(line_id, note)


def timeout_summary(line_id: str, note: str) -> pd.Series:
    return pd.Series(
        {
            "test_case": f"handwired_line_trip_{line_id}",
            "simulation_success": False,
            "physical_fault_or_breaker_action_executed": False,
            "schema_only": False,
            "simulation_mode": "graphical_simulink_phasor_RMS",
            "trip_implementation": "handwired_timed_breaker",
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
        }
    )


def timeout_signal(line_id: str, note: str) -> pd.Series:
    return pd.Series(
        {
            "test_case": f"handwired_line_trip_{line_id}",
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
        }
    )


def timeout_event(line_id: str, note: str) -> pd.Series:
    return pd.Series(
        {
            "test_case": f"handwired_line_trip_{line_id}",
            "event_time_s": 0.5,
            "event_type": "pilot_line_trip",
            "physical_executed": False,
            "event_note": note,
        }
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IEEE39 handwired line trips in isolated MATLAB processes.")
    parser.add_argument("--line-ids", nargs="+", default=["L01", "L02", "L03", "L04"])
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--timeout-seconds", type=int, default=240)
    parser.add_argument("--simulation-stop-time", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []
    signals = []
    events = []
    for line_id in args.line_ids:
        summary, signal, event = run_line(line_id, output_dir, args.timeout_seconds, args.simulation_stop_time)
        summaries.append(summary)
        signals.append(signal)
        events.append(event)
        write_outputs(output_dir, summaries, signals, events)
        print(
            pd.DataFrame(
                [summary],
                columns=["test_case", "simulation_success", "training_ready_candidate", "measurement_extraction_status", "note"],
            ).to_string(index=False)
        )
    write_outputs(output_dir, summaries, signals, events)


def write_outputs(output_dir: Path, summaries: list[pd.Series], signals: list[pd.Series], events: list[pd.Series]) -> None:
    pd.DataFrame(summaries, columns=SUMMARY_COLUMNS).to_csv(output_dir / "ieee39_multi_handwired_line_trip_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(signals, columns=SIGNAL_COLUMNS).to_csv(output_dir / "ieee39_multi_handwired_signal_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(events).to_csv(output_dir / "ieee39_multi_handwired_event_log.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
