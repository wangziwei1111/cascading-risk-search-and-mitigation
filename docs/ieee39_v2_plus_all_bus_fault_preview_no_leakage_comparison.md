# IEEE39 v2-plus-all-bus-fault Preview/No-Leakage Comparison

This round is preview/no-leakage comparison only.

It did not run Simulink.
It did not run actual smoke.
It did not export labels.
It did not train GCN.
It did not retrain the formal reranker.
It did not run a GCN usefulness audit.

## What This Step Means

In plain language, this round is a small leakage and generalization check on the
latest 79-row candidate dataset. We use lightweight Ridge Regression to predict
`dynamic_stress_score` and lightweight Logistic Regression to predict
`unstable_flag`. The purpose is not to claim final model performance. The
purpose is to see how much the score changes after removing post-fault compact
dynamic measurement inputs, and how hard bus-fault generalization looks under
stricter holdouts.

## Dataset Boundary

- candidate_dataset: `v2_plus_all_bus_fault_candidates`
- total_candidate_rows: `79`
- num_total_bus_fault_candidates: `39`
- all_ieee39_buses_have_bus_fault_candidate: `true`
- old_formal_gate: `35 / 33 / 33`
- l12_excluded: `true`
- nf06_provenance_warning_preserved: `true`
- unstable_flag_false_buses: `["B1"]`

The 79-row candidate dataset still contains candidate labels, not formal
labels. Bus-fault labels still remain temporary smoke candidates, not formal
protection labels.

## Leakage Boundary

The compact dynamic measurement features

- `min_voltage_pu`
- `max_voltage_pu`
- `min_frequency_hz`
- `max_frequency_hz`
- `max_speed_deviation`
- `max_rotor_angle_separation_deg`

are post-fault compact dynamic measurements. They should not be used as main
GCN inputs later, because they create target-feature leakage risk for this proxy
target setup.

So:

- `include_all_79_candidates` is a leaky upper-bound
- `no_dynamic_measurement_features` is the more important leakage-reduced sanity
  check
- `leave_one_bus_fault_out` matters more than plain leave-one-out over all 79
  rows
- `no_dynamic_measurement_leave_one_bus_fault_out` is the stricter bus-fault
  generalization check

## Preview Results

| mode | RMSE | MAE | meaning |
| --- | ---: | ---: | --- |
| include_all_79_candidates | `0.047793` | `0.037348` | leaky upper-bound |
| no_dynamic_measurement_features | `0.076096` | `0.056225` | leakage-reduced sanity check |
| label_family_holdout | `0.229895` | `0.208437` | train formal, test non-formal families |
| bus_fault_holdout | `0.165132` | `0.135876` | train non-bus-fault, test all 39 bus-fault candidates |
| leave_one_bus_fault_out | `0.061684` | `0.050703` | all-feature bus-fault leave-one-out |
| no_dynamic_measurement_leave_one_bus_fault_out | `0.086604` | `0.069158` | stricter no-leakage bus-fault leave-one-out |

The increase from `include_all_79_candidates` to
`no_dynamic_measurement_features`, and from all-feature bus-fault leave-one-out
to no-dynamic-measurement bus-fault leave-one-out, supports the leakage risk
warning. It does not prove GCN useful or not useful. It only says the leaky
upper-bound is easier than the stricter no-leakage setting.

## B1 Detail

`B1 unstable_flag=false` is a low-risk / stable marker, not an error.

- b1_true_dynamic_stress_score: `0.196026`
- b1_predicted_dynamic_stress_score: `0.393280`
- b1_absolute_error: `0.197254`
- b1_true_unstable_flag: `0`
- b1_unstable_probability: `0.884100`
- b1_unstable_probability_source: `bus_fault_holdout_fallback`

The fallback note means the stricter leave-one-bus-fault-out classifier could
not provide a probability for B1 because that fold loses class balance after
holding out the only stable bus-fault marker.

## Worst 10 Buses In No-Dynamic LOO

`B1, B9, B12, B27, B19, B18, B20, B6, B10, B5`

This is a descriptive preview result only. It is not a final bus ranking.

## Important Boundaries

- `phasor_RMS` is not EMT.
- `generator_speed_proxy` is not direct frequency.
- temporary bus-fault injection is not engineering-grade protection.
- this round cannot directly prove GCN useful or not useful.
- this round cannot directly justify reranker retraining.
- this round can at most support a future GCN usefulness audit design.

## Recommended Next Step

`leakage risk confirmed; prepare GCN usefulness audit only with no-leakage features and strict holdouts, not training yet`

## Audit-Plan Follow-Up

A later separate round now prepares the IEEE39 GCN usefulness audit plan. That
follow-up still does not train GCN, does not run the GCN usefulness audit, does
not run Simulink, does not export labels, and does not retrain the reranker.

The next allowed action is only the audit dry-run validator. It is still not
time to start formal GCN training.

## Dry-Run Validator Follow-Up

The later dry-run validator round also stays conservative. It does not train
GCN, does not run the formal GCN usefulness audit, does not run Simulink, does
not export labels, and does not retrain the reranker.

That dry-run only checks whether a future strict no-leakage GCN usefulness
audit is structurally ready:

- forbidden features remain excluded from proposed primary GCN inputs
- strict holdouts remain complete
- baseline comparison remains complete
- B1 remains special-tracked
- NF06 sensitivity remains enabled
- L12 remains excluded

Even after dry-run pass, it is still not time to blindly train GCN. The next
safe action can only be to prepare a formal usefulness audit execution round.
