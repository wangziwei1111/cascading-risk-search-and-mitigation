# IEEE 118 Ordered N-2 Full-Truth Plan

This stage moves IEEE 118 beyond the initial smoke test by adding a generator for ordered N-2 cascade truth rows. The generator enumerates paths such as `L001->L002` through `L186->L185`, skipping paths where the first and second line are the same.

## Scope

- Case: PYPOWER `case118`.
- Output directory default: `results/gcn_search/ieee118_fulltruth/`.
- Default relay threshold: `beta=1.2`.
- Default redispatch security limit: `security_limit=1.0`.
- Default load scale: `load_scale=1.0`.

For each seed, the script applies a deterministic load scenario by multiplying each bus load by `load_scale * U(0.9, 1.1)`. Use `--load-scale 1.1` for a more stressed first pass; keep the exact value in the config JSON for reproducibility.

## Command

```bash
python src/gcn_search/ieee118/generate_ieee118_ordered_n2_fulltruth.py \
  --seeds 20260708 \
  --max-paths 100 \
  --output-dir results/gcn_search/ieee118_fulltruth_smoke
```

Remove `--max-paths` for a full per-seed enumeration of `186 * 185 = 34,410` ordered N-2 paths.

## Outputs

- `ieee118_fulltruth_summary.csv`: all generated path rows.
- `ieee118_critical_paths.csv`: subset where `critical == True`.
- `ieee118_fulltruth_config.json`: seeds, load scale, protection parameters, checkpoint settings, and candidate-path count.

Each row includes `scenario_id`, `seed`, `path`, `first_line`, `second_line`, `converged`, `critical`, load-shed fields, final maximum loading ratio, final outage labels, final outage count, and error text.

## Caching

The first-step outage state is cached within each seed. For each `first_line`, the script computes the stable post-contingency state `S1(first_line)` once, then evaluates every `second_line` from that cached state. This avoids repeating the first active outage, protection cascade, island handling, and redispatch for every ordered pair with the same first line.

## Not Yet GCN Validation

This stage still is not a GCN efficiency validation. It only generates IEEE 118 ordered N-2 truth rows. GCN efficiency claims require a completed full-truth dataset followed by method comparison against GCN, `LODF_yP`, random ordering, and simple `line_order` baselines under the same evaluation protocol.
