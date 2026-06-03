# RL Paper Reproduction Status

Paper: `Real-Time Cascade Mitigation in Power Systems Using Influence Graph Improved by Reinforcement Learning`

Current boundary: only the RL paper reproduction is in scope. GCN, GCN-RL bridge, oracle BC, safe gate, and one-step oracle are excluded from paper main results.

Status values: `done`, `partial-smoke`, `partial-framework`, `not-done`.

| Paper content | Paper requirement | Current implementation | Status | Gap / boundary | Next formal command |
|---|---|---|---|---|---|
| MDP state/action/reward | `S=[line_status, relative_flow]`, full `0..n` actions, paper reward | Implemented and tested | done | PYPOWER substitute environment | `pytest tests/rl_mitigation/paper -q` |
| Figure 1 | Cascade flow trace | JSON/MD trace with required fields | done | Example trace, not numerical figure | `python -m scripts.rl_mitigation.paper.check_figure1_cascade_flow --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml` |
| IEEE5 DP / Figure 2/3 | DP example | IEEE5 mechanism reproduction with DFS and policy iteration | done | Exact paper IEEE5 parameters unavailable | `python -m scripts.rl_mitigation.paper.run_ieee5_dp --config configs/rl_mitigation/paper/ieee5_dp.yaml` |
| IEEE14 paper PPO | do-nothing init + mask + PPO | Smoke pipeline runs and report is generated | partial-smoke | Formal 60000-step run not completed in this round | `python -m scripts.rl_mitigation.paper.run_ieee14_paper_pipeline --config configs/rl_mitigation/paper/ieee14_paper_ppo.yaml --steps 60000 --eval-episodes 1000` |
| IEEE14 Figure 7 | 9-grid learning curves | Smoke gridsearch output under `gridsearch/smoke` | partial-smoke | Not formal 60000-step gridsearch | `python -m scripts.rl_mitigation.paper.train_ieee14_gridsearch --config configs/rl_mitigation/paper/ieee14_paper_gridsearch.yaml --steps 60000` |
| IEEE14 Figure 8 | 1000-scenario before/after survival | Smoke survival figure generated with `_smoke` suffix | partial-smoke | Not 1000-scenario formal evaluation | `python -m scripts.rl_mitigation.paper.evaluate_ieee14_survival --eval-csv results/rl_mitigation/paper/ieee14/eval/eval_1000_before_after.csv --episodes 1000` |
| IEEE14 claim check | classify performance conclusion | JSON/MD/table produced | partial-smoke | Current result is not fully supported | `python -m scripts.rl_mitigation.paper.check_ieee14_paper_claims --eval-csv results/rl_mitigation/paper/ieee14/eval/eval_1000_before_after.csv` |
| IEEE118 case118 smoke | runnable IEEE118 framework | PYPOWER case118, action space 187, state 372 | partial-framework | Full 600000-step training not run | `python -m scripts.rl_mitigation.paper.train_ieee118_ppo --config configs/rl_mitigation/paper/ieee118_paper_ppo.yaml --smoke --steps 2048` |
| IEEE118 baseline/proposed | baseline vs proposed comparison | scaffold and smoke proposed output | partial-framework | Full baseline/proposed training not run | `python -m scripts.rl_mitigation.paper.compare_ieee118_pretrain_mask` |
| IEEE118 Figure 9-12 | learning/survival/action figures | Smoke figure interfaces generated | partial-smoke | Framework evidence only | `python -m scripts.rl_mitigation.paper.make_ieee118_paper_figures --smoke` |

Current thesis-safe wording:

```text
The repository reproduces the RL paper mechanism and provides PYPOWER IEEE14/IEEE118 smoke evidence. IEEE14 PPO performance is currently partially supported rather than a complete numerical reproduction. Formal claims require the 60000-step IEEE14 run, 1000-scenario evaluation, and preferably a closer grid2op-compatible environment.
```
