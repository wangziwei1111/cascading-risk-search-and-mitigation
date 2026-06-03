# RL Paper Reproduction Status

Paper: `Real-Time Cascade Mitigation in Power Systems Using Influence Graph Improved by Reinforcement Learning`

Current priority: reproduce the RL paper body. GCN-RL coupling and IEEE14 GCN risk ranking are paused and must not be treated as paper reproduction results.

| Paper content | Paper requirement | Current implementation | Done | Gap | Script / result |
|---|---|---|---|---|---|
| Figure 1 cascade flow | Complete cascade environment loop | IEEE14 example trace with action, islands, power-flow convergence, trip probabilities, reward terms | yes | PYPOWER substitute environment | `scripts/rl_mitigation/paper/check_figure1_cascade_flow.py`; `results/rl_mitigation/paper/figure1_trace/` |
| Figure 2/3 IEEE5 DP | Small-system DP explanation | IEEE5 mechanism reproduction, DFS transitions, policy iteration, figures | partial | exact paper IEEE5 parameters unavailable; mechanism reproduction only | `scripts/rl_mitigation/paper/run_ieee5_dp.py`; `results/rl_mitigation/paper/ieee5/` |
| IEEE14 MDP state | `S=[line_status, relative_flow]` | default observation length is `2n` | yes | none for implemented environment | `tests/rl_mitigation/paper/test_paper_mdp_definition.py` |
| IEEE14 action space | `A=0` do-nothing, `A=i` open line i | full `0..n_lines`; no Top-M compression | yes | none | `tests/rl_mitigation/paper/test_paper_action_space.py` |
| IEEE14 reward | paper reward terms | exact term function and tests | yes | PYPOWER failure behavior differs from original environment | `src/rl_mitigation/envs/reward.py` |
| do-nothing initialization | supervised actor initialization to action 0 | paper wrapper with probability diagnostics and figure | yes | smoke uses reduced states | `results/rl_mitigation/paper/ieee14/pretrain/` |
| invalid action mask | mask out already-opened lines | action mask and PPO masked logits | yes | no-mask path records invalid actions as do-nothing | `src/rl_mitigation/rl/action_mask.py` |
| IEEE14 9-grid search | lr x entropy 3x3 | smoke gridsearch completed with 9 logs | partial | smoke 512 steps, not full 60000 | `results/rl_mitigation/paper/ieee14/gridsearch/` |
| Figure 7 | IEEE14 learning curves | smoke Figure 7 generated | partial | smoke figure name marks smoke | `results/rl_mitigation/paper/ieee14/figures/fig7_*_smoke.*` |
| Figure 8 | before/after negative-return survival | 100-scenario smoke survival generated | partial | formal entry supports 1000, current run is 100 smoke | `results/rl_mitigation/paper/ieee14/figures/fig8_*` |
| IEEE118 training | PPO on IEEE118 | PYPOWER case118 framework and short smoke | partial | backend now supports case118; full 600000 not run | `scripts/rl_mitigation/paper/train_ieee118_ppo.py` |
| Figure 9 | IEEE118 learning curve | interface and smoke figure generated | partial | short smoke only | `results/rl_mitigation/paper/ieee118/figures/fig9_*` |
| Figure 10 | IEEE118 negative-return survival | interface and smoke figure generated | partial | do-nothing smoke only when checkpoint load is limited | `results/rl_mitigation/paper/ieee118/figures/fig10_*` |
| Figure 11 | IEEE118 generations/outages/load-shed survival | interface and smoke figures generated | partial | smoke only | `results/rl_mitigation/paper/ieee118/figures/fig11a/b/c_*` |
| Figure 12 | IEEE118 action frequency | interface and smoke figure generated | partial | action-frequency proxy from proactive-action count | `results/rl_mitigation/paper/ieee118/figures/fig12_*` |

Diagnostic and enhanced results are separated from the paper main line:

- Diagnostics: action-value scan, one-step oracle, policy diagnosis.
- Enhanced experiments: oracle BC, safe gate, GCN-RL bridge.
- Paper reproduction: `results/rl_mitigation/paper/`.

Current IEEE14 claim check is `partially_supported`; the smoke proposed policy does not yet stably improve all do-nothing metrics in the PYPOWER IEEE14 substitute environment.

