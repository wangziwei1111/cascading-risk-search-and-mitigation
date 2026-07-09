# IEEE118 Paper-Aligned Training Scale-Up Results

This stage scales PR #13 beyond the 12-state smoke run. It keeps the same protocol:

- no Algorithm 1 search-logic changes;
- no replacement GCN model;
- original RTS-79 `PaperStyleRts79Gcn`;
- PR #11 first-step critical early-stop;
- PR #13 S0 + S1 multi-state current-state samples;
- paper-style four-channel branch features.

Large local artifacts remain untracked: raw full-truth CSVs, the 2.7GB Step2-State CSV, NPZ datasets, model checkpoints, full predictions, and Simulink/MATLAB outputs.

## Calibration 200

Command:

```bash
python src/gcn_search/ieee118/sweep_ieee118_training_calibration.py \
  --seeds 20260701 20260702 20260703 20260704 20260705 20260706 20260707 20260708 20260709 20260710 \
  --target-state-samples 200 \
  --samples-per-scenario 20 \
  --load-scales 1.0 1.05 1.1 \
  --flow-limit-scales 8.0 10.0 12.0 \
  --min-rate-a 1.0 \
  --sample-seed 20260709 \
  --output-dir results/gcn_search/ieee118_paper_aligned_training_scaleup/calibration_200 \
  --output-stem ieee118_training_calibration_sweep_200
```

Outputs:

- `ieee118_training_calibration_sweep_200.csv`
- `ieee118_training_calibration_sweep_200.json`
- `ieee118_training_calibration_sweep_200_readme.md`

Selection rule: prefer the original-paper load setting `load_scale=1.1` when label density is not too sparse/dense and first-step critical labels do not dominate. If `flow_scaled=8.0` is too tight under `load_scale=1.1`, evaluate `10.0` or `12.0` before changing the main training setting.

Status in this PR: calibration is implemented and run commands are recorded. The committed compact outputs are used only as label-density calibration, not as final search-efficiency evidence.

Calibration-200 completed for all nine settings. All settings were classified as `candidate`; the original-paper load setting with `flow_scaled=8.0` remains reasonable:

| load_scale | flow_limit_scale | positive_label_ratio | S0 positive ratio | S1 positive ratio | first-step critical labels | recommendation |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1.00 | 8.0 | 0.053889 | 0.050538 | 0.054067 | 94 | candidate |
| 1.00 | 10.0 | 0.046408 | 0.041935 | 0.046646 | 78 | candidate |
| 1.00 | 12.0 | 0.042929 | 0.040323 | 0.043068 | 75 | candidate |
| 1.05 | 8.0 | 0.051958 | 0.049462 | 0.052090 | 92 | candidate |
| 1.05 | 10.0 | 0.043412 | 0.039247 | 0.043634 | 73 | candidate |
| 1.05 | 12.0 | 0.041121 | 0.037634 | 0.041306 | 70 | candidate |
| 1.10 | 8.0 | 0.052705 | 0.046774 | 0.053021 | 87 | candidate |
| 1.10 | 10.0 | 0.041782 | 0.034946 | 0.042146 | 65 | candidate |
| 1.10 | 12.0 | 0.036926 | 0.032796 | 0.037145 | 61 | candidate |

Because `load_scale=1.1, flow_limit_scale=8.0` keeps the label ratio near 5.3% without excessive first-step critical dominance, pilot training keeps `flow_scaled=8.0`.

## Pilot 200

Dataset command:

```bash
python src/gcn_search/ieee118/build_ieee118_paper_gcn_training_dataset.py \
  --seeds 20260701 20260702 20260703 20260704 20260705 20260706 20260707 20260708 20260709 20260710 \
  --target-state-samples 200 \
  --samples-per-scenario 20 \
  --load-scale 1.1 \
  --load-random-low 0.9 \
  --load-random-high 1.1 \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.0 \
  --min-rate-a 1.0 \
  --beta 1.2 \
  --security-limit 1.0 \
  --first-step-critical-policy skip \
  --feature-mode paper \
  --sample-seed 20260709 \
  --output-dir results/gcn_search/ieee118_paper_aligned_training_scaleup/pilot_200
```

Training command:

```bash
python src/gcn_search/ieee118/train_ieee118_paper_aligned_gcn.py \
  --dataset-npz results/gcn_search/ieee118_paper_aligned_training_scaleup/pilot_200/ieee118_paper_gcn_dataset.npz \
  --output-dir results/gcn_search/ieee118_paper_aligned_training_scaleup/pilot_200 \
  --epochs 20 \
  --batch-size 32 \
  --learning-rate 0.005 \
  --positive-weight 20
```

The held-out test seed remains `20260708`; it must not appear in train or validation seeds.

Pilot-200 dataset completed:

- state samples: 200
- S0 samples: 10
- S1 samples: 190
- positive labels: 1,937 / 36,752
- positive label ratio: 0.052705
- first-step critical labels: 87
- valid N-2 positive labels: 1,850
- train seeds: 20260701-20260707, 20260709
- validation seed: 20260710
- test seed: 20260708

Pilot-200 classification with original RTS-79 defaults (`positive_weight=20`, 20 epochs):

| split | accuracy | hit rate | cover rate | F1 | average precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| overall | 0.856797 | 0.256729 | 0.906040 | 0.400091 | 0.548383 |
| validation | 0.827056 | 0.200969 | 0.813725 | 0.322330 | 0.474770 |
| test | 0.844774 | 0.222973 | 0.882353 | 0.355987 | 0.529281 |
| S0 | 0.767204 | 0.136555 | 0.747126 | 0.230906 | 0.189129 |
| S1 | 0.861573 | 0.265723 | 0.913514 | 0.411693 | 0.565602 |

Search evaluation reuses the existing evaluator and does not change the search algorithm. The required methods are:

- `random`
- `line_order`
- `PFW`
- `LODF_yP`
- `RTS79_GCN_path_prob_reused_on_IEEE118_earlystop`
- `RTS79_GCN_second_only_reused_on_IEEE118_earlystop`

Pilot-200 search on held-out seed `20260708`:

| method | K=100 hits | K=1000 hits | K=5000 hits | K=1000 recall | K=1000 precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| random | 4.7 | 60.0 | 275.4 | 0.034208 | 0.060000 |
| line_order | 6 | 56 | 281 | 0.031927 | 0.056000 |
| PFW | 6 | 66 | 265 | 0.037628 | 0.066000 |
| LODF_yP | 10 | 58 | 275 | 0.033067 | 0.058000 |
| path_prob | 26 | 271 | 878 | 0.154504 | 0.271000 |
| second_only ablation | 79 | 545 | 1214 | 0.310718 | 0.545000 |

## Pilot 2000

The pilot-2000 target is:

```bash
python src/gcn_search/ieee118/build_ieee118_paper_gcn_training_dataset.py \
  --seeds 20260701 20260702 20260703 20260704 20260705 20260706 20260707 20260709 20260710 20260711 20260712 20260713 20260714 20260715 20260716 20260717 20260718 20260719 20260720 20260721 \
  --target-state-samples 2000 \
  --samples-per-scenario 100 \
  --load-scale 1.1 \
  --load-random-low 0.9 \
  --load-random-high 1.1 \
  --limit-mode flow_scaled \
  --flow-limit-scale 8.0 \
  --min-rate-a 1.0 \
  --beta 1.2 \
  --security-limit 1.0 \
  --first-step-critical-policy skip \
  --feature-mode paper \
  --sample-seed 20260709 \
  --test-seeds 20260708 \
  --output-dir results/gcn_search/ieee118_paper_aligned_training_scaleup/pilot_2000
```

The command intentionally excludes `20260708` from the listed training scenario seeds and reserves it as the held-out test seed. Pilot-2000 must not be described as the formal 8000-state result.

Implementation note: the completed pilot-2000 run includes `20260708` as a held-out test split and reassigns seed `20260720` as validation because `target_state_samples=2000` was reached before the originally listed validation seed `20260721` was sampled. The reassignment is whole-seed and therefore avoids leakage.

Pilot-2000 dataset completed:

- state samples: 2,000
- S0 samples: 20
- S1 samples: 1,980
- positive labels: 18,349 / 367,414
- positive label ratio: 0.049941
- first-step critical labels: 167
- valid N-2 positive labels: 18,182
- train state samples: 1,818
- validation state samples: 81
- test state samples: 101

Pilot-2000 classification with original RTS-79 defaults (`positive_weight=20`, 20 epochs):

| split | accuracy | hit rate | cover rate | F1 | average precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| overall | 0.939978 | 0.451589 | 0.941523 | 0.610405 | 0.878658 |
| validation | 0.945342 | 0.460248 | 0.893768 | 0.607607 | 0.865178 |
| test | 0.933804 | 0.414307 | 0.943439 | 0.575768 | 0.860736 |
| S0 | 0.905645 | 0.321012 | 0.988024 | 0.484581 | 0.513846 |
| S1 | 0.940329 | 0.453368 | 0.941096 | 0.611938 | 0.880911 |

## Positive-Weight Sensitivity

Command:

```bash
python src/gcn_search/ieee118/sweep_ieee118_paper_gcn_weights.py \
  --dataset-npz results/gcn_search/ieee118_paper_aligned_training_scaleup/pilot_2000/ieee118_paper_gcn_dataset.npz \
  --output-dir results/gcn_search/ieee118_paper_aligned_training_scaleup/pilot_2000_weight_sweep \
  --positive-weights 20 50 100 200 800 \
  --epochs 20 \
  --batch-size 32 \
  --learning-rate 0.005
```

`positive_weight=20` is the original RTS-79 paper-default baseline. Higher weights are IEEE118 sensitivities. The best sensitivity setting must be reported separately and must not replace the original-paper default in the main protocol narrative.

Pilot-2000 positive-weight sensitivity completed. The original RTS-79 default remains the best by overall average precision:

| positive_weight | role | overall hit rate | overall cover rate | overall F1 | overall AP | S0 AP | S1 AP |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 20 | original_paper_default | 0.451589 | 0.941523 | 0.610405 | 0.878658 | 0.513846 | 0.880911 |
| 50 | sensitivity | 0.278149 | 0.972042 | 0.432529 | 0.812385 | 0.350169 | 0.816612 |
| 100 | sensitivity | 0.210964 | 0.980653 | 0.347230 | 0.798987 | 0.446660 | 0.801869 |
| 200 | sensitivity | 0.160066 | 0.988119 | 0.275503 | 0.763008 | 0.397314 | 0.765502 |
| 800 | sensitivity | 0.085841 | 0.994932 | 0.158046 | 0.616816 | 0.193050 | 0.620001 |

Pilot-2000 search on held-out seed `20260708`:

| method | K=100 hits | K=1000 hits | K=5000 hits | K=1000 recall | K=1000 precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| random | 4.7 | 60.0 | 275.4 | 0.034208 | 0.060000 |
| line_order | 6 | 56 | 281 | 0.031927 | 0.056000 |
| PFW | 6 | 66 | 265 | 0.037628 | 0.066000 |
| LODF_yP | 10 | 58 | 275 | 0.033067 | 0.058000 |
| path_prob | 57 | 360 | 1185 | 0.205245 | 0.360000 |
| second_only ablation | 94 | 661 | 1705 | 0.376853 | 0.661000 |

Pilot-2000 materially improves over random, line order, PFW, and LODF_yP. The `second_only` ablation remains stronger than strict `path_prob`, which means the learned S0 first-step probability is still a bottleneck and should be discussed rather than hidden.

## Paper 8000 Target

The formal paper-aligned target remains `target_state_samples=8000`. If this is not completed in the current PR, pilot-2000 results must be labeled as pilot results only.

Paper-8000 was not completed in this PR. The runnable command and protocol are documented, but pilot-2000 must not be presented as the formal 8000-state result.

## Interpretation Rules

These results can support the claim that IEEE118 now has a paper-aligned training protocol with multi-state S0/S1 samples. They cannot by themselves claim final IEEE118 GCN superiority unless pilot-2000 or paper-8000 search evaluation clearly supports it.

If `path_prob` or `second_only` outperforms Algorithm 1, keep that as an ablation result. If Algorithm 1 remains close to LODF/PFW/random, discuss possible causes such as threshold calibration, positive label sparsity, mismatch between S0 first-step and valid N-2 risk, and IEEE118 mechanism differences from RTS-79.
