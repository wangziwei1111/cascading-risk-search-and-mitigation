from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation"
OUT_PATH = OUT_DIR / "handwired_breaker_checklist.txt"


CHECKLIST = """IEEE39 handwired timed breaker checklist

1. Open the generated wrapper:
   results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper.slx

   In MATLAB, first redirect Simulink generated-code files to a short path:
   cd("C:/Users/24186/Documents/New project 7/simulink-dynamic-validation-worktree/matlab/simulink_ieee39")
   configure_ieee39_short_filegen_paths()

2. Save a local handwired copy as:
   results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx

3. Navigate to L01:
   IEEE39BusSystem_dynamic_experiment_wrapper/Grid/B1 to B2

4. Insert a three-phase breaker or timed controlled switch around the L01 line.
   Suggested block name:
   L01_HandwiredTimedBreaker

5. Add a trip command signal that is closed before 0.5 s and open after 0.5 s.
   Suggested signal/source name:
   L01_TripCommand

6. Save the handwired .slx locally. Do not commit generated or handwired .slx files.

7. Validate the handwired model in MATLAB:
   validate_ieee39_handwired_breaker_model( ...
     "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
     "../../results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation", ...
     "L01", ...
     "L01_HandwiredTimedBreaker", ...
     "L01_TripCommand" ...
   )

8. If validation_passed=true, run compact fault suite with handwired mode:
   run_ieee39_fault_test_suite( ...
     "../../results/gcn_search/ieee39_graphical_dynamic_model/generated_models/IEEE39BusSystem_dynamic_experiment_wrapper_handwired_breaker.slx", ...
     "../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests", ...
     true, ...
     ["no_fault_sanity", "three_phase_fault_clear", "single_line_trip", "relay_trip_test"], ...
     0.5, ...
     true ...
   )

9. Re-export the label gate:
   python ../../src/gcn_search/legacy_rts79/export_ieee39_dynamic_labels.py ^
     --fault-summary-csv ../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_fault_test_summary.csv ^
     --event-log-csv ../../results/gcn_search/ieee39_graphical_dynamic_model/fault_tests/ieee39_event_log.csv ^
     --output-dir ../../results/gcn_search/ieee39_dynamic_labels

10. Confirm:
    single_line_trip trip_implementation = handwired_timed_breaker or handwired_timed_controlled_switch
    physical_fault_or_breaker_action_executed = true
    training_ready_candidate = true
    allowed_for_dynamic_aware_training remains false if num_training_ready_labels < 10.

Boundaries:
- Handwired breaker is a pilot breaker-like validation path, not engineering-grade protection.
- The IEEE39 model remains phasor_RMS, not EMT.
- generator_speed_proxy is not direct frequency.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(CHECKLIST, encoding="utf-8")
    print(CHECKLIST)
    print(f"\nSaved checklist to: {OUT_PATH}")


if __name__ == "__main__":
    main()
