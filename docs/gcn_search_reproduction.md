# GCN Critical Cascading Path Search Reproduction

## Migrated Source

The current workspace's RTS79/GCN reproduction scripts were migrated to:

```text
src/gcn_search/legacy_rts79/
```

This preserves the existing cascade simulation, N-k path generation, Step2-State style data generation, GCN training scripts, LODF utilities, search evaluation scripts, and search-counting analysis scripts.

## Preserved Capabilities

- Cascading failure simulation.
- N-k outage path generation.
- Step2-State or equivalent reachable-state dataset generation.
- Branch graph construction.
- GCN training and reachable-label learning.
- Path-level ranking through GCN-derived path probability.
- Baseline comparison with LODF, random search, and line-order search where present in the migrated scripts.
- Search count, Top-K coverage, and critical path discovery analysis.

## Entrypoints

```bash
python -m scripts.gcn_search.train_gcn
python -m scripts.gcn_search.evaluate_search
python -m scripts.gcn_search.make_figures
```

## Scope

This repository now keeps the GCN cascading-failure path-search reproduction as the active public scope.
