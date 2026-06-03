# RL Paper Reproduction Report

Smoke run: `True`

## Step Status

| Step | Status | Outputs |
|---|---|---|
| ieee5_dp | completed | results/rl_mitigation/paper/ieee5/ieee5_dp_report.md |
| figure1_trace | completed | results/rl_mitigation/paper/figure1_trace/ieee14_example_trace.md |
| ieee14_paper_pipeline | completed | results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_report.md |
| ieee14_gridsearch | completed | results/rl_mitigation/paper/ieee14/figures/fig7_ieee14_learning_curves_gridsearch_smoke.png |
| ieee14_eval_integrity | completed | results/rl_mitigation/paper/ieee14/reports/ieee14_eval_integrity_check.json |
| ieee14_claim_check | completed | results/rl_mitigation/paper/ieee14/reports/ieee14_claim_check.json; results/rl_mitigation/paper/ieee14/tables/table_ieee14_claim_metrics.csv |
| ieee14_mask_pretrain_ablation | completed | results/rl_mitigation/paper/ieee14/ablation/mask_pretrain_ablation.csv |
| ieee118_pretrain | completed | results/rl_mitigation/paper/ieee118/pretrain/pretrain_diagnostics.json |
| ieee118_ppo | completed | results/rl_mitigation/paper/ieee118/train_logs/proposed_pretrain_mask_smoke.csv |
| ieee118_eval | completed | results/rl_mitigation/paper/ieee118/eval/eval_20_before_after_smoke.csv |
| ieee118_figures | completed | results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png |

## IEEE5

IEEE5 DP: `completed`

## Figure 1

Cascade trace: `completed`

## IEEE14

Paper pipeline: `completed`
Claim check: `completed`

## IEEE118

Smoke framework: `completed`

## Formal Commands

```powershell
python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --steps 60000 --eval-episodes 1000
python -m scripts.rl_mitigation.paper.train_ieee118_ppo --config configs/rl_mitigation/paper/ieee118_paper_ppo.yaml --steps 600000
```

## Thesis Wording

Use paper reproduction results under `results/rl_mitigation/paper/` as the main RL reproduction package. Diagnostics and enhanced experiments are not original paper results.
