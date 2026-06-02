# RL Cascade Mitigation Reproduction

## Method Overview

This module targets the small-system parts of `Real-Time Cascade Mitigation in Power Systems Using Influence Graph Improved by Reinforcement Learning`: an IEEE5 dynamic-programming mechanism example and an IEEE14 PPO real-time mitigation experiment. IEEE118 is intentionally out of scope for the current stage.

## MDP

State:

```text
S_t = [l_1, ..., l_n, rho_1, ..., rho_n]
```

`l_i` is the line status. `rho_i` is relative line flow. For disconnected lines, `rho_i` is set to zero.

Action:

```text
A = 0: do-nothing
A = i: proactively open line i
```

Only one proactive line-opening action is allowed per generation.

Reward:

```text
R_t = - I_{S_t != S_T}
      - 100 I_fail
      - alpha I_{A_{t-1} != 0}
      - 100(1 - exp(-0.01 N_{g,t}))
      - (L_{t-1} - L_t) / L_{t-1}
```

Generation 0 initial outages are not rewarded. Power-flow failure terminates the episode and receives the failure penalty.

## Cascade Flow

`CascadeMitigationEnv` implements a Gymnasium-style interface:

```python
reset()
step(action)
get_action_mask()
render_cascade()
```

Each generation records current outages, proactive action, overloaded lines, stochastic trips, convergence status, and load shedding.

## IEEE5 DP

Command:

```bash
python -m scripts.rl_mitigation.run_ieee5_dp --config configs/rl_mitigation/ieee5_dp.yaml
```

Outputs:

```text
results/rl_mitigation/ieee5/dp_policy.json
results/rl_mitigation/ieee5/transition_counts.pkl
results/rl_mitigation/ieee5/fig_ieee5_cascade_without_mitigation.png
results/rl_mitigation/ieee5/fig_ieee5_cascade_with_mitigation.png
results/rl_mitigation/ieee5/fig_ieee5_transition_dfs.png
```

The current IEEE5 case is a mechanism reproduction if exact paper parameters are not available.

## IEEE14 PPO

Commands:

```bash
python -m scripts.rl_mitigation.pretrain_do_nothing --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml --smoke --steps 2048
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 10 --smoke
python -m scripts.rl_mitigation.make_figures --case ieee14
```

The PPO configuration records the paper hyperparameters: 60000 total steps, learning rate 1e-3, gamma 1, entropy coefficient 0.001, clipping 0.2, rollout length 1024, and hidden layers `[64, 64]` / `[64, 8]`.

## Do-Nothing Pretraining

The pretraining routine collects diverse states with a random policy, labels every state with action `0`, and trains the policy actor by cross entropy with entropy regularization. It saves:

```text
results/rl_mitigation/ieee14/pretrain/states_actions.npz
results/rl_mitigation/ieee14/pretrain/policy_pretrained.pt
```

## Invalid Action Mask

`get_action_mask()` marks do-nothing as valid and already disconnected lines as invalid. The masked policy sets invalid logits to `-1e9`. In no-mask mode, invalid line actions are replaced by do-nothing and counted in `num_invalid_actions`.

## Figure Mapping

- Paper Figure 7: `fig7_learning_curves_gridsearch.png/pdf`.
- Paper Figure 8: `fig8_survival_negative_return.png/pdf`.
- IEEE5 cascade diagrams: `fig_ieee5_*`.

## Known Differences

See `docs/rl_mitigation_reproducibility_gaps.md`.
