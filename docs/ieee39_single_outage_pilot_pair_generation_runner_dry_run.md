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

The selected 32 single-outage pilot pair execution was approved in a later
round. That follow-up does not train GCN, does not rerun formal audit, does not
export formal labels, does not retrain the reranker, and is not full 1056
generation.

The controlled execution runner currently records the selected 32 rows as
`blocked` because no safe controlled Simulink execution backend is available in
the audit runner. Timeout, unknown, blocked, or failed cases are not converted
to 0/1, and pilot labels are not formal training labels.

Boundary notes remain unchanged: `beta * RATE_A` is an audit-only proxy, not a
real relay setting; bus-fault labels are not used; L12 remains special/excluded;
NF06 warning is preserved; `phasor_RMS` is not EMT; `generator_speed_proxy` is
not direct frequency; temporary bus-fault injection is not engineering-grade
protection; no deployment is claimed.

## Follow-Up: Backend Diagnosis

A later controlled execution backend diagnosis checks why the selected pair
execution remained blocked. It does not train GCN, does not rerun formal audit,
does not execute selected 32 pairs, does not run full 1056 generation, does not
export formal labels, and does not retrain the reranker.

The diagnosis confirms that selected-pair branch mapping exists, but an approved
two-step line-trip sequence injection, a selected-32-only batch runner, and a
selected-pair result parser contract are still missing. The next step is to add
that safe backend or write local manual execution instructions before rerunning
evidence collection.
