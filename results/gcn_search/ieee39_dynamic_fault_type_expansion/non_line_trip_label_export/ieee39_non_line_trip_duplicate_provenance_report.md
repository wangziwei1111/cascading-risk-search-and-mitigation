# IEEE39 Non-Line-Trip Duplicate / Provenance Report

- duplicate measurement groups: 1
- provenance check required scenarios: NF06
- rows deleted due to duplicates: 0

## NF01 / NF04 / NF06

NF01 and NF04 are both existing three-phase fault block 0.10 s cases, so identical values are expected. NF06 is relay_proxy_fault_smoke but currently has measurements identical to the 0.10 s fault group, so it is retained but marked provenance_check_required and not_independent_physical_sample_until_verified.

Rows are retained, but duplicate/provenance flags must be reviewed before treating them as independent physical samples.

## group_1

- scenarios: NF01, NF04, NF06
- fault types: fault_duration_sweep_smoke, relay_proxy_fault_smoke, three_phase_fault_clear_smoke
- same timing: True
- fault type differs with identical measurement: True
- note: NF01/NF04 duplicate timing is expected; NF06 needs provenance check because relay proxy measurements match the same group.
