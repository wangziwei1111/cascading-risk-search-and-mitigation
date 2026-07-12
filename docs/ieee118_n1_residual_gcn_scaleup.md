# IEEE118 N-1 Residual-Reachable GCN Paper-8000 Scale-Up

## Scope

This stage scales the successful 2,000-state pilot to the formal 8,000-state
paper-aligned target. It does not change the IEEE118 physical truth, the
`PaperStyleRts79Gcn` core, or the selected graph radius.

Fixed settings:

- truth: IEEE118 early-stop ordered N-2, `flow_scaled=8.00`, `min_rate_a=1.0`;
- model: original RTS-79 `PaperStyleRts79Gcn`;
- graph radius: `k_gcn=6`, selected by pilot validation AP;
- loss: weighted cross entropy, `positive_weight=20`;
- load scenarios: `load_scale=1.1`, independent bus multipliers in `[0.9, 1.1]`;
- held-out test/full-truth seed: `20260708`;
- no label leakage or outcome fields in model input.

## Why Scale the Data

The pilot contains 2,000 states, or about 10.8 states per IEEE118 line. It
already shows that the N-1 gate plus residual GCN can reach 90% critical recall
in 2,125 total physical evaluations, but the residual tail remains difficult:
K99 is 10,386 total evaluations for the second-only ablation.

The next controlled variable is therefore training coverage, not architecture.
Paper-8000 increases state coverage fourfold while preserving the selected
model, loss, and evaluation protocol.

## Seed-Split Plan

The dataset contains exactly 8,000 states:

| Split | Seeds | Planned states | Role |
|---|---:|---:|---|
| train, 7 full shards | 70 | 7,070 | fitting model and normalizer |
| train, partial shard | 1 | 21 | exact total-size adjustment |
| validation | 8 | 808 | checkpoint selection |
| test | 1 | 101 | frozen classification audit only |
| total | 80 | 8,000 | paper-8000 |

Seed `20260708` appears only in the test shard. The merged normalizer is refit
using only train states. Validation and test labels do not select input
normalization statistics.

## Resumable Parallel Generation

The previous builder exposed `--resume` and `--checkpoint-every` but did not
implement persistence. This stage adds:

1. deterministic per-seed first-line sampling;
2. incremental compressed NPZ checkpoint shards;
3. an atomic checkpoint progress file;
4. a full generation-configuration fingerprint;
5. completed-seed skipping and partial-seed restoration;
6. rejection of resume attempts with changed physical/data settings.

The formal run uses eight worker processes. BLAS/OpenMP threads are limited to
one per worker to avoid CPU oversubscription. A failed worker can be rerun with
the same command and `--resume`; completed shards are returned immediately.

```powershell
& '.venv\Scripts\python.exe' `
  src/gcn_search/ieee118/generate_ieee118_residual_scaleup_shards.py `
  --num-workers 8 `
  --resume `
  --checkpoint-every 25 `
  --sample-seed 20260712 `
  --output-root results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_shards
```

## Merge and Residual Conversion

After all ten shards complete:

```powershell
& '.venv\Scripts\python.exe' `
  src/gcn_search/ieee118/merge_ieee118_paper_gcn_shards.py `
  --input-root results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_shards `
  --output-dir results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_source `
  --expected-state-samples 8000

& '.venv\Scripts\python.exe' `
  src/gcn_search/ieee118/build_ieee118_residual_reachable_dataset.py `
  --source-dataset-npz results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_source/ieee118_paper_gcn_dataset.npz `
  --source-normalizer-json results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_source/ieee118_paper_gcn_feature_normalizer.json `
  --output-dir results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_residual
```

Merge validation requires:

- exactly 8,000 states;
- no duplicate `(seed, sample_type, active_first_line)` keys;
- no seed overlap across train/validation/test;
- test split exactly `{20260708}`;
- explicit `active_first_line` for every S1 state;
- identical line labels, branch endpoints, and feature schema across shards.

## Training and Frozen Evaluation

Training keeps the pilot-selected hyperparameters:

```powershell
& '.venv\Scripts\python.exe' `
  src/gcn_search/ieee118/train_ieee118_residual_reachable_gcn.py `
  --dataset-npz results/gcn_search/ieee118_n1_residual_scaleup/paper_8000_residual/ieee118_residual_reachable_gcn_dataset.npz `
  --output-dir results/gcn_search/ieee118_n1_residual_scaleup/training_k6 `
  --k-gcn 6 `
  --epochs 20 `
  --positive-weight 20 `
  --random-seed 20260712
```

The final model checkpoint is selected by validation AP. Search evaluation then
uses the unchanged 32,560-path early-stop truth. Both rankings remain visible:

- primary: N-1 gate plus RTS-79-compatible path probability;
- diagnostic ablation: N-1 gate plus second-step probability only.

Fair N-1-gated random, line order, and LODF_yP baselines remain unchanged.

## Acceptance Criteria

1. All ten shards complete with no simulation errors.
2. Merged states equal 8,000 and all S1 active-first labels are explicit.
3. Seed `20260708` never appears in train or validation.
4. Original `PaperStyleRts79Gcn` is used with `k=6`; no new GCN is introduced.
5. Paper-8000 is compared directly with pilot-2000 at K90/K95/K99, fixed K,
   relay recall, precision, and captured load shed.
6. A regression is reported honestly even if more data does not improve the
   frozen test ranking.

## Formal Paper-8000 Result

The eight-worker run completed on 2026-07-12. It used the resumable shard
pipeline and took about 90 minutes of wall-clock time on the local Windows
workstation. All ten shards completed, generated exactly 8,000 states, and
left every `generation_stderr.log` empty.

Merged data audit:

| Item | Value |
|---|---:|
| train states | 7,091 |
| validation states | 808 |
| held-out test states | 101 |
| S0 states | 80 |
| S1 states | 7,920 |
| unknown S1 active first lines | 0 |
| paper-source candidate labels | 1,470,463 |
| paper-source positive ratio | 4.864% |
| residual S1 positive ratio | 1.090% |

The fixed `k=6` model selected epoch 19 by validation AP. Validation AP was
0.6422 and held-out test AP was 0.6167. The pilot-2000 values were 0.3416 and
0.4463 respectively.

The primary ranking remains N-1 gate plus RTS-79-compatible `path_prob`:

| Training data | Total physical K90 | K95 | K99 | K100 |
|---|---:|---:|---:|---:|
| pilot-2000 | 2,189 | 3,362 | 11,115 | 22,503 |
| paper-8000 | **1,979** | **2,449** | **4,491** | **13,718** |

Increasing state coverage reduced K90 by 210 evaluations, K95 by 913, and
K99 by 6,624. The largest improvement is therefore in the difficult
high-recall tail, not only at the early part of the ranking.

At K90, paper-8000 uses 1,979 physical evaluations, or 6.08% of the 32,560
ordered N-2 paths. Fair N-1-gated baselines require 3,879 for line order,
4,617 for LODF_yP, and 5,129.6 on average for random ranking. This makes the
IEEE118 early-recall budget ratio closer to the scale of the RTS-79 result,
but it is not an equal claim: the RTS-79 slide reports finding all critical
paths, whereas 1,979 is the IEEE118 90%-recall point. IEEE118 K100 remains
13,718, so complete tail recovery is still substantially harder.

The `second_only` diagnostic ablation reaches total physical K90/K95/K99 at
1,978/2,475/4,543. It is nearly tied at K90 but slightly worse than the
primary `path_prob` ranking at K95 and K99, so `path_prob` remains the formal
primary method.

## Artifact Policy

Checkpoint shards, merged NPZs, model checkpoints, and full predictions remain
local. Git may contain only code, tests, documentation, and compact metrics,
thresholds, and curve tables. No Simulink/MATLAB content belongs to this stage.

Committed compact results include the pilot-vs-paper8000 threshold and budget
tables, the training metrics/log, the N-1-gated thresholds and cumulative
curve points, and dataset metadata. Local-only artifacts include checkpoint
NPZ shards, merged datasets, the model checkpoint, and full top-K path tables.

## Status (2026-07-12)

- scale-up branch created: `feature/ieee118-n1-residual-gcn-scaleup`;
- real checkpoint/resume support implemented and tested;
- deterministic paper-8000 shard plan implemented and validated;
- train-only merge/normalization implemented and tested;
- formal eight-worker generation completed: 8,000/8,000 states, ten shards,
  zero non-empty stderr logs;
- merge and residual conversion completed with no split leakage and no unknown
  S1 active first lines;
- original RTS-79 `PaperStyleRts79Gcn` trained at fixed `k=6` and evaluated on
  the unchanged 32,560-path truth;
- paper-8000 improves primary total physical K90/K95/K99 to
  1,979/2,449/4,491;
- no GCN architecture change, no Simulink/MATLAB scope, and no large artifact
  is intended for Git.
