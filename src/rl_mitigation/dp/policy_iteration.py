from __future__ import annotations


def transition_probabilities(counts: dict) -> dict:
    probs = {}
    for sa, outcomes in counts.items():
        total = sum(outcomes.values())
        probs[sa] = [(sp, reward, c / total) for (sp, reward), c in outcomes.items()]
    return probs


def policy_iteration(counts: dict, gamma: float = 1.0, iterations: int = 50) -> dict:
    probs = transition_probabilities(counts)
    states = sorted({sa[0] for sa in probs} | {sp for outs in probs.values() for sp, _, _ in outs})
    actions_by_state = {}
    for state, action in probs:
        actions_by_state.setdefault(state, []).append(action)
    values = {s: 0.0 for s in states}
    policy = {s: min(actions_by_state.get(s, [0])) for s in states}
    for _ in range(iterations):
        for s in states:
            action = policy.get(s, 0)
            values[s] = sum(p * (r + gamma * values.get(sp, 0.0)) for sp, r, p in probs.get((s, action), []))
        stable = True
        for s, actions in actions_by_state.items():
            q = {
                a: sum(p * (r + gamma * values.get(sp, 0.0)) for sp, r, p in probs.get((s, a), []))
                for a in actions
            }
            best = max(q, key=q.get)
            stable = stable and best == policy.get(s)
            policy[s] = int(best)
        if stable:
            break
    return {"policy": policy, "values": values}
