# RL Paper Reproduction Report

Mode: `smoke`
IEEE14 claim check: `not_supported`
Source eval CSV: `results/rl_mitigation/paper/ieee14/eval/eval_100_before_after_smoke.csv`

| Step | Status | Outputs |
|---|---|---|
| ieee5_dp | completed | results/rl_mitigation/paper/ieee5/ieee5_dp_report.md |
| figure1_trace | completed | results/rl_mitigation/paper/figure1_trace/ieee14_example_trace.md |
| ieee14_paper_pipeline | completed | results/rl_mitigation/paper/ieee14/reports/ieee14_paper_pipeline_report_smoke.md |
| ieee14_gridsearch | completed | results/rl_mitigation/paper/ieee14/figures/fig7_ieee14_learning_curves_gridsearch_smoke.png |
| ieee14_eval_integrity | completed | results/rl_mitigation/paper/ieee14/reports/ieee14_eval_integrity_check_smoke.json |
| ieee14_claim_check | completed | results/rl_mitigation/paper/ieee14/reports/ieee14_claim_check_smoke.json; results/rl_mitigation/paper/ieee14/tables/table_ieee14_claim_metrics_smoke.csv |
| ieee14_mask_pretrain_ablation | completed | results/rl_mitigation/paper/ieee14/ablation/mask_pretrain_ablation_smoke.csv |
| ieee118_pretrain | completed | results/rl_mitigation/paper/ieee118/pretrain/pretrain_diagnostics.json |
| ieee118_ppo | completed | results/rl_mitigation/paper/ieee118/train_logs/proposed_pretrain_mask_smoke.csv |
| ieee118_eval | completed | results/rl_mitigation/paper/ieee118/eval/eval_20_before_after_smoke.csv |
| ieee118_figures | completed | results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png |

## Formal Commands

```powershell
python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --mode formal
python -m scripts.rl_mitigation.paper.train_ieee14_gridsearch --config configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml --mode formal
python -m scripts.rl_mitigation.paper.train_ieee118_ppo --config configs/rl_mitigation/paper/ieee118_paper_ppo.yaml --steps 600000
```

Diagnostics and enhanced experiments are not paper reproduction results.
