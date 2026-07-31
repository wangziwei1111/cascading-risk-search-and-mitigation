# IEEE118 Phase 4 Prospective Physical-Oracle Evaluation

## Purpose

Phase 3 evaluated the adaptive search policy retrospectively: labels were
hidden behind a callback, but the complete truth table already existed. This
phase performs a stricter prospective test on the unseen load-scenario seed
`20260709`. The search program has no full-truth input and receives a cascade
outcome only after selecting an ordered N-2 path for physical simulation.

The experiment keeps the Phase-3 policy frozen:

- IEEE118 `flow_scaled=8.00`, `min_rate_a=1.0`;
- label-free transformer-tap-aware iterative LODF gate;
- 26 candidate second-line families;
- five physical probes per family;
- promote a family after at least one critical probe;
- expand promoted families, then use the unchanged GCN as fallback;
- original RTS-79 `PaperStyleRts79Gcn` architecture and checkpoint wrapper.

No full-truth CSV path is accepted by the prospective runner. Full truth was
generated independently only after the 2,100-query search log was frozen and
hashed. The posthoc audit is read-only and cannot change query order.

## Physical Accounting

The search issued 2,100 unique N-2 cascade queries. Extending the initial
150-query run through resume required 221 cumulative N-1 state constructions,
including states reconstructed after process restart, for 2,321 cumulative
physical operations. The completed-resume check performed zero additional
N-1 or N-2 simulations. All 2,100 queried paths converged without errors.

First-step critical early stop is active. Ten first outages were already
critical and therefore do not create artificial second-outage samples. The
independent truth table consequently contains 32,560 valid ordered N-2 paths,
not the unfiltered `186 * 185 = 34,410` combinations.

## Prospective Results

The independent seed contains 1,866 critical paths and 1,726 critical
relay-cascade paths. At 2,100 N-2 queries, or 6.45% of the valid search space,
the frozen policy found:

| Metric | Result |
|---|---:|
| critical discoveries | 1,613 |
| critical recall | 86.44% |
| query precision | 76.81% |
| relay-cascade discoveries | 1,487 |
| relay-cascade recall | 86.15% |
| captured load shed | 53,443.71 MW |
| load-shed capture ratio | 86.60% |
| error queries | 0 |

`relay_cascade` means a critical path whose final mechanism is classified as
relay cascade. `overload relay activity` is broader: a relay may trip even
when the path is not ultimately labeled critical. These quantities are kept
separate in all summaries.

## Stage Attribution

| Search stage | Queries | Critical | Precision | Critical relay cascade |
|---|---:|---:|---:|---:|
| physical probes | 130 | 51 | 39.23% | 6 |
| promoted-family expansion | 1,866 | 1,548 | 82.96% | 1,468 |
| unchanged-GCN fallback | 104 | 14 | 13.46% | 13 |

The main gain on this seed comes from the application-level promoted-family
expansion. The unchanged GCN fallback is substantially weaker in the small
remaining budget. The 86.44% recall is therefore a result of the complete
frozen adaptive policy, not a standalone-GCN result.

## Reproduction

Run the prospective search without access to full truth:

```bash
python src/gcn_search/ieee118/run_ieee118_prospective_oracle.py \
  --seed 20260709 \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.0 \
  --min-rate-a 1.0 \
  --gate-size 26 \
  --probes-per-second-line 5 \
  --promotion-min-positives 1 \
  --max-n2-queries 2100 \
  --resume \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase4_prospective_smoke150_seed20260709
```

After search completion, independently generate truth for audit:

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260709 \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.0 \
  --min-rate-a 1.0 \
  --first-step-critical-policy skip \
  --resume --checkpoint-every 500 \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase4_posthoc_fulltruth_seed20260709
```

Then run the read-only audit:

```bash
python src/gcn_search/ieee118/audit_ieee118_prospective_oracle.py \
  --query-log results/gcn_search/ieee118_simulation_efficient_gcn/phase4_prospective_smoke150_seed20260709/ieee118_prospective_oracle_queries.csv \
  --fulltruth-csv results/gcn_search/ieee118_simulation_efficient_gcn/phase4_posthoc_fulltruth_seed20260709/ieee118_fulltruth_summary.csv \
  --seed 20260709 \
  --policy-summary-json results/gcn_search/ieee118_simulation_efficient_gcn/phase4_prospective_smoke150_seed20260709/ieee118_prospective_oracle_summary.json \
  --output-dir results/gcn_search/ieee118_simulation_efficient_gcn/phase4_prospective_posthoc_audit_seed20260709
```

## Scope Boundary

This is one prospective IEEE118 seed, not evidence of deployment readiness on
a real utility grid. It does not establish transfer to N-3/N-4 contingencies,
IEEE300, ACTIVSg systems, or utility data. Raw query logs and the complete
32,560-row truth CSV remain local; the repository contains only compact audit
artifacts. Broader multi-seed prospective evaluation is the next required
experiment.
