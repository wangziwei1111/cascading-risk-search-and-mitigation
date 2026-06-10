# Simulink Dynamic Negative Controls

## Purpose

Round 19 checks whether calibrated Top20 dynamic smoke has real discrimination. The key question is simple: if learned_top20 is 20/20 unstable, are low_score_top20, random_top20, and line_order_top20 also 20/20 unstable?

If every group is unstable, the dynamic prototype or thresholds are still degenerate. If learned_top20 is clearly more stressful than controls, then learned reranker Top-K starts to show a dynamic discrimination signal.

## Groups

- `learned_top20`: highest reranker score or best path rank.
- `low_score_top20`: lowest reranker score.
- `random_top20`: fixed-seed random sample.
- `line_order_top20`: lexicographic first/second line order.

The control inputs do not use `opa_is_critical` or `opa_total_load_shed_mw` for sorting.

## Diagnostics

Round 19 adds:

```text
src/gcn_search/legacy_rts79/analyze_dynamic_instability_reasons.py
src/gcn_search/legacy_rts79/compute_dynamic_stress_score.py
src/gcn_search/legacy_rts79/prepare_dynamic_negative_control_inputs.py
src/gcn_search/legacy_rts79/run_dynamic_negative_control_pipeline.py
matlab/simulink_rts79/run_dynamic_negative_control_batch.m
```

The instability reason summary separates frequency nadir, rotor-angle separation, unresolved relay violation, simulation failure, and mixed reasons. Security redispatch or load shedding alone is not treated as a dynamic instability reason.

The dynamic stress score is only an auxiliary ranking metric. It does not replace `dynamic_unstable`.

## Current Interpretation

Round 18 removed the all-passive-relay-trip behavior under calibrated options, but calibrated Top20 still had 20/20 dynamic unstable cases. Round 19 therefore compares learned_top20 against negative controls before interpreting the learned reranker dynamically.

Round 19 negative-control result:

| group | precision@20 | passive relay trips | security actions | mean dynamic stress |
| --- | ---: | ---: | ---: | ---: |
| learned_top20 | 1.0000 | 0 | 20 | 4.9614 |
| low_score_top20 | 1.0000 | 0 | 15 | 5.1883 |
| random_top20 | 1.0000 | 0 | 18 | 4.9650 |
| line_order_top20 | 1.0000 | 0 | 12 | 4.9756 |

The current calibrated dynamic prototype still has `global_degeneracy_warning = true` and `dynamic_discrimination_signal = false`. In plain terms, the learned Top20 set is not uniquely identified as dynamically worse than the negative controls. The dynamic validation layer is therefore useful as a plumbing and diagnostic prototype, but it is not yet a discriminative evaluation metric.

The calibrated learned Top20 instability reasons were:

```text
frequency_nadir_below_threshold = 20
rotor_angle_above_threshold = 20
relay_violation_not_eliminated = 0
sim_failed = 0
mixed_reasons = 20
```

This confirms that the current `dynamic_unstable` decisions are driven by frequency and rotor-angle criteria, not by passive relay trips or simulation failures. Security redispatch/load shedding is logged as a physical action, but it is not by itself treated as a dynamic instability reason.

No dynamic recall is reported because there is no full dynamic truth set.

This is still a simplified swing-equation prototype:

- not EMT;
- not full OPF;
- no renewable generation;
- no exciter, governor, or PSS;
- not an engineering-grade dynamic stability conclusion.

## Next Step

If all groups remain 20/20 unstable, continue calibrating swing dynamics and instability thresholds. If controls are less unstable or have lower stress score, expand to Top50/Top100 and compare learned, PIO-GCN, and LODF dynamic behavior.
