# Cascading Risk Search and Mitigation

This repository is an independent reproduction workspace for a thesis project on power-system cascading failure risk identification and real-time mitigation.

## Scope

The project contains two connected but non-substitutable modules:

- `src/gcn_search`: identifies which N-k cascading outage paths are dangerous.
- `src/rl_mitigation`: decides how to intervene after a cascade starts, using do-nothing or one proactive line trip per generation.

Together they form a risk identification to risk mitigation defense workflow.

## Repository Status

`git` and `gh` were not available in the current Codex environment, so this directory has been created locally without a remote. To publish later:

```bash
git init
git add .
git commit -m "Initialize cascading risk search and mitigation reproduction"
gh repo create cascading-risk-search-and-mitigation --private --source . --push
```

## Layout

```text
configs/              Experiment configuration
docs/                 Reproduction notes and thesis integration docs
scripts/              Command-line entry points
src/gcn_search/       Migrated GCN critical path search work
src/rl_mitigation/    RL cascade mitigation implementation
tests/rl_mitigation/  Unit and smoke tests
results/              Reproduction outputs
```

## GCN Search Module

Migrated RTS79/GCN reproduction scripts are preserved under:

```text
src/gcn_search/legacy_rts79/
```

Available wrapper commands:

```bash
python -m scripts.gcn_search.train_gcn
python -m scripts.gcn_search.evaluate_search
python -m scripts.gcn_search.make_figures
```

Existing GCN reports and copied result assets are under `docs/` and `results/gcn_search/`.

## RL Mitigation Module

The RL module implements the paper-facing MDP skeleton:

- State: `S_t = [l_1, ..., l_n, rho_1, ..., rho_n]`.
- Action: `0` for do-nothing, `i` for proactively opening line `i`.
- Reward: includes cascade continuation, power-flow failure, proactive action penalty, new line outages, and load shedding.
- Invalid action mask: do-nothing is always valid; already opened lines are invalid.
- Cascade environment: Gymnasium-style `reset`, `step`, `get_action_mask`, and `render_cascade`.

Required commands:

```bash
python -m scripts.rl_mitigation.run_ieee5_dp --config configs/rl_mitigation/ieee5_dp.yaml
python -m scripts.rl_mitigation.pretrain_do_nothing --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml
python -m scripts.rl_mitigation.train_gridsearch_ieee14 --config configs/rl_mitigation/ieee14_gridsearch.yaml
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 1000 --with-agent --without-agent
python -m scripts.rl_mitigation.make_figures --case ieee14
```

Quick smoke commands:

```bash
python -m scripts.rl_mitigation.train_ppo --case ieee14 --config configs/rl_mitigation/ieee14_ppo.yaml --smoke --steps 2048
python -m scripts.rl_mitigation.evaluate_policy --case ieee14 --episodes 10 --smoke
pytest tests/rl_mitigation -q
```

## Thesis Figure Name Suggestions

- Figure 7 reproduction: `IEEE14 PPO训练回报曲线`
- Figure 8 reproduction: `IEEE14负回报生存函数对比`
- IEEE5 DP figures: `IEEE5无缓解级联传播示意图`, `IEEE5主动缓解级联传播示意图`

## Reproducibility Note

The current IEEE14 implementation is a runnable surrogate reproduction framework. It does not claim exact numerical reproduction of the paper because the paper's original chronics, random seeds, and full AC-islanding implementation are not available in this workspace. Differences are tracked in `docs/rl_mitigation_reproducibility_gaps.md`.
