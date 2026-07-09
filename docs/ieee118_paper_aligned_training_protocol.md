# IEEE118 Paper-Aligned GCN Training Protocol

This stage aligns IEEE118 training with the original paper-style GCN protocol. It does not change the search algorithm.

## Motivation

The previous IEEE118 single-scenario run trained mostly on `S1(first_line)` Step2-State samples. That is incomplete for the original protocol because the same GCN is later used for both:

- `p_shed(Li | S0)`: first-outage vulnerability in the base state.
- `p_shed(Lj | S1(i))`: second-outage vulnerability after a non-critical first outage.

The paper trains on many `X_GCN -> y_GCN` current-state samples, not on a single held-out ordered N-2 seed. IEEE118 therefore needs S0 and S1 samples across multiple load scenarios.

## Dataset

The new builder is:

`src/gcn_search/ieee118/build_ieee118_paper_gcn_training_dataset.py`

Each sample is a current operating state:

- `sample_type=S0`: base state. Labels mark whether actively opening each online line causes load shed after OPA stabilization.
- `sample_type=S1`: state after a non-critical first outage. Labels mark whether opening each valid remaining line causes load shed after OPA stabilization.

First-step critical lines remain early-stop N-1 critical events. They are positive S0 labels, but they do not generate S1 ordered N-2 samples.

The formal target size is `target_state_samples=8000`, matching the original RTS-79 paper-scale training idea. The committed artifact is only a small smoke run.

## Features

The main protocol uses the paper-style 4 features:

- `x_t`: branch outage status.
- `x_p`: `abs(PF) / (beta * RATE_A)`.
- `x_b`: absolute branch flow.
- `x_l`: larger terminal-bus load.

The committed smoke metadata reports `feature_mode=paper` and `input_channels=4`.

## Splits

Train, validation, and test splits are assigned by load-scenario seed. The same seed must not appear in multiple splits.

## Training

The training script is:

`src/gcn_search/ieee118/train_ieee118_paper_aligned_gcn.py`

It still uses:

`src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py::PaperStyleRts79Gcn`

The default hyperparameters remain RTS-79 aligned:

- epochs: 20
- batch size: 32
- learning rate: 0.005
- `k_gcn`: 3
- first layer channels: 16
- second layer channels: 4
- positive weight: 20

The script records a sensitivity grid for `positive_weight`, epochs, and batch size, but the main smoke run keeps the conservative RTS-79-style setup.

## Metrics

Metrics are reported overall and separately for S0 and S1:

- total accuracy
- hit rate / precision
- cover rate / recall
- F1
- average precision
- mean positive and negative scores
- positive prediction rates at 0.5 and 0.8

Hit rate is the fraction of predicted-positive labels that are truly load-shedding. Cover rate is the fraction of true load-shedding labels covered by predicted positives.

## Calibration

The lightweight calibration script is:

`src/gcn_search/ieee118/sweep_ieee118_training_calibration.py`

It samples a small number of states for combinations of:

- load scale: 1.0, 1.05, 1.1
- flow-limit scale: 8.0, 10.0, 12.0

The smoke artifact is only a label-density sanity check. Full paper-aligned training should use a larger run before final claims.

## Scope

This PR does not regenerate full-truth, does not change Algorithm 1 or other search ordering logic, and does not commit NPZ datasets, model checkpoints, raw full-truth CSV, full predictions, or Simulink/MATLAB artifacts.

## Scale-Up Stage

The follow-up scale-up stage keeps this same protocol and increases the run size from the PR #13 smoke artifact to:

- `calibration_200`: medium label-density calibration over `load_scale={1.0,1.05,1.1}` and `flow_limit_scale={8,10,12}`.
- `pilot_200`: first usable end-to-end pilot with original RTS-79 defaults.
- `pilot_2000`: larger pilot for classification and search evaluation.
- `paper_8000`: the formal target matching the original paper-scale training idea.

Scale-up results are recorded in `docs/ieee118_paper_aligned_training_scaleup_results.md`. Pilot results must not be described as the final paper-8000 result, and positive-weight sensitivities must not overwrite the original-paper `positive_weight=20` baseline.
