# IEEE 118 First-Stage Extension Plan

This change is a first-stage smoke-test extension of the RTS-79 cascade simulator. It adds a small generic case adapter so the existing ordered outage workflow can run on both `rts79` and `ieee118`.

## What This Stage Covers

- Load `rts79` from PYPOWER `case24_ieee_rts`.
- Load `ieee118` from PYPOWER `case118`.
- Generate benchmark-specific branch labels from the case branch table.
- Use canonical three-digit line labels: `L001`, `L002`, ...
- Keep RTS-79 two-digit labels such as `L01` as compatibility aliases in the adapter.
- Preserve the ordered N-2 sequence: apply the first active outage, run DCPF, protection relay trips, island balancing, and redispatch to a stable state before applying the second active outage.
- Add an IEEE 118 smoke entry point:

```bash
python src/gcn_search/ieee118/run_ieee118_n2_smoke.py --num-paths 100 --seed 20260708
```

Smoke outputs are written under:

```text
results/gcn_search/ieee118_smoke/
```

## What This Stage Does Not Claim

This stage does not generate the full IEEE 118 ordered N-2 truth dataset. It also does not train or evaluate a GCN on IEEE 118, and it does not claim IEEE 118 GCN search efficiency improvements. The smoke test only verifies that the generalized case path can load IEEE 118, solve the initial DCOPF, run outage simulations, and emit structured path-level results.

## Next Stage

The next stage should generate a reproducible IEEE 118 full-truth dataset, audit path failure modes, define train/validation/test splits, retrain the GCN or path-reranker on IEEE 118, and only then evaluate top-k search efficiency against the full ordered N-2 baseline.
