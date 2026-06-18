# IEEE39 Single-Outage Pilot Pair Generation Runner Dry-Run

This round is a selected single-outage pilot pair generation runner dry-run. It does not train GCN, does not rerun formal audit, does not run new Simulink, does not export formal labels, does not retrain the reranker, and does not save a production model.

There is no deployment in this round.

## Plain-Language Purpose

The base-state labels are all negative for the 33 available non-L12 branches, so they cannot be used alone for training. This round does not run all 1056 eligible `single_outage_state x next_branch` pairs. Instead, this dry-run selects a small pilot set and writes the future run plan. The selected rows are still planned samples, not real labels.

## Selection Strategy

1. `high_relay_ratio_pairs`: select high prior/next `x_p_relay_ratio` combinations to increase the chance of finding positive examples.
2. `shared_bus_neighbor_pairs`: select branch pairs that share a bus, matching the branch-as-node graph adjacency idea.
3. `non_neighbor_control_pairs`: select non-neighbor pairs as lower-risk/control samples.
4. `known_special_exclusion`: exclude any pair with L12 as prior or next branch.
5. `diversity`: avoid putting every pilot row on the same branch area.

## Current Counts

- dry_run_scope: `single_outage_pilot_pair_runner_dry_run`
- max_pairs_requested: `32`
- num_candidate_pairs_available: `1056`
- num_pilot_pairs_selected: `32`
- num_high_relay_ratio_pairs: `10`
- num_shared_bus_neighbor_pairs: `10`
- num_non_neighbor_control_pairs: `12`
- num_l12_pairs_excluded: `66`
- selected_pairs_label_status: `planned`
- label_values_fabricated: `False`

## Boundaries

`beta * RATE_A` is an audit-only proxy, not a real relay setting. Bus-fault labels are not used. L12 remains special/excluded. NF06 warning is preserved. `phasor_RMS` is not EMT. `generator_speed_proxy` is not direct frequency. Temporary bus-fault injection is not engineering-grade protection.

Dynamic outputs such as `dynamic_stress_score` and `unstable_flag` can only be future labels or audit targets, not input features. No label-derived flags are inputs.

## Next Step

`approve and execute selected single-outage pilot pair generation in a separate round`

Manual approval is required before executing the selected pair generation runner.

## Follow-Up: Selected Pair Execution Approval

The follow-up approval round approved a selected 32-pair pilot execution scope, not the full 1056 state-branch grid. Because there was no safe controlled Simulink execution backend at that time, all selected pair labels remained blocked/null and were not exported as formal labels.

## Follow-Up: Backend Diagnosis

The backend diagnosis found that the selected-pair mapping and wrapper artifacts existed, but execution was blocked by missing controlled two-step line-trip injection, a selected-32-only batch runner, and a result parser contract.

## Follow-Up: Backend Repair Skeleton

The backend repair follow-up added the selected-32-only runner, MATLAB entrypoint skeleton, parser contract, evidence-only writer, and manual execution instruction pack. It still does not execute selected pairs or create formal labels.
