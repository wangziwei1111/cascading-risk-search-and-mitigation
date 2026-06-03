# RL Paper Figure Index

| Paper Figure | Repository file | Generated | Smoke/Formal | Claim boundary | Note |
|---|---|---:|---|---|---|
| Figure 1 | `results/rl_mitigation/paper/figure1_trace/ieee14_example_trace.md`; `ieee14_example_trace.json` | yes | smoke trace | main mechanism evidence | PYPOWER IEEE14 example trace, not a numerical figure reproduction |
| Figure 2 | `results/rl_mitigation/paper/ieee5/fig2_ieee5_without_mitigation.png/pdf` | yes | mechanism | main mechanism evidence | IEEE5 exact paper parameters unavailable |
| Figure 3 | `results/rl_mitigation/paper/ieee5/fig3_ieee5_with_mitigation.png/pdf` | yes | mechanism | main mechanism evidence | DP mechanism reproduction |
| Figure 7 | `results/rl_mitigation/paper/ieee14/figures/fig7_ieee14_learning_curves_gridsearch_smoke.png/pdf/csv` | yes | smoke | not formal numerical reproduction | Formal target is `fig7_ieee14_learning_curves_gridsearch.*` after 60000-step gridsearch |
| Figure 8 | `results/rl_mitigation/paper/ieee14/figures/fig8_ieee14_negative_return_survival_smoke.png/pdf/csv` | yes | smoke | not formal numerical reproduction | Smoke uses 100 or fewer scenarios; formal target uses `eval_1000_before_after.csv` |
| Figure 9 | `results/rl_mitigation/paper/ieee118/figures/fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png/pdf` | yes | smoke | framework evidence | Full IEEE118 600000-step run not completed |
| Figure 10 | `results/rl_mitigation/paper/ieee118/figures/fig10_ieee118_negative_return_survival_smoke.png/pdf` | yes | smoke | framework evidence | PYPOWER case118 smoke |
| Figure 11 | `results/rl_mitigation/paper/ieee118/figures/fig11a_ieee118_generations_survival_smoke.png/pdf`; `fig11b_*`; `fig11c_*` | yes | smoke | framework evidence | Generations, line outages, load shed |
| Figure 12 | `results/rl_mitigation/paper/ieee118/figures/fig12_ieee118_action_frequency_smoke.png/pdf` | yes | smoke | framework evidence | Action-frequency proxy from smoke eval |

