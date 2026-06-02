from __future__ import annotations

import numpy as np


LOWER_IS_BETTER = {"negative_return", "num_generations", "num_line_outages", "load_shed_MW", "load_shed_ratio"}


def paired_metric_stats(rows: list[dict], policy_a: str, policy_b: str, metric: str, seed: int = 0, n_bootstrap: int = 1000) -> dict:
    by_policy = {}
    for row in rows:
        by_policy.setdefault(row["policy"], {})[str(row["scenario_id"])] = row
    common = sorted(set(by_policy.get(policy_a, {})) & set(by_policy.get(policy_b, {})))
    diffs = np.asarray([float(by_policy[policy_a][sid][metric]) - float(by_policy[policy_b][sid][metric]) for sid in common], dtype=float)
    if len(diffs) == 0:
        return _empty(policy_a, policy_b, metric)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_bootstrap):
        sample = rng.choice(diffs, size=len(diffs), replace=True)
        boots.append(float(np.mean(sample)))
    low, high = np.percentile(boots, [2.5, 97.5])
    if metric in LOWER_IS_BETTER:
        improved = diffs < -1e-9
        worse = diffs > 1e-9
    else:
        improved = diffs > 1e-9
        worse = diffs < -1e-9
    ties = np.abs(diffs) <= 1e-9
    return {
        "policy_a": policy_a,
        "policy_b": policy_b,
        "metric": metric,
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
        "bootstrap_ci_low": float(low),
        "bootstrap_ci_high": float(high),
        "direction": _direction(float(low), float(high), metric),
        "improved_ratio": float(np.mean(improved)),
        "worse_ratio": float(np.mean(worse)),
        "tie_ratio": float(np.mean(ties)),
        "num_scenarios": int(len(diffs)),
    }


def paired_improvement_summary(rows: list[dict], policy: str, baseline: str = "do_nothing", metric: str = "negative_return") -> dict:
    by_policy = {}
    for row in rows:
        by_policy.setdefault(row["policy"], {})[str(row["scenario_id"])] = row
    common = sorted(set(by_policy.get(policy, {})) & set(by_policy.get(baseline, {})))
    improvements = np.asarray([float(by_policy[baseline][sid][metric]) - float(by_policy[policy][sid][metric]) for sid in common], dtype=float)
    if len(improvements) == 0:
        return {
            "mean_improvement_vs_do_nothing": 0.0,
            "median_improvement_vs_do_nothing": 0.0,
            "improved_scenario_ratio_vs_do_nothing": 0.0,
            "worse_scenario_ratio_vs_do_nothing": 0.0,
        }
    return {
        "mean_improvement_vs_do_nothing": float(np.mean(improvements)),
        "median_improvement_vs_do_nothing": float(np.median(improvements)),
        "improved_scenario_ratio_vs_do_nothing": float(np.mean(improvements > 1e-9)),
        "worse_scenario_ratio_vs_do_nothing": float(np.mean(improvements < -1e-9)),
    }


def _empty(policy_a: str, policy_b: str, metric: str) -> dict:
    return {
        "policy_a": policy_a,
        "policy_b": policy_b,
        "metric": metric,
        "mean_diff": 0.0,
        "median_diff": 0.0,
        "bootstrap_ci_low": 0.0,
        "bootstrap_ci_high": 0.0,
        "direction": "no_clear_difference",
        "improved_ratio": 0.0,
        "worse_ratio": 0.0,
        "tie_ratio": 0.0,
        "num_scenarios": 0,
    }


def _direction(low: float, high: float, metric: str) -> str:
    if metric in LOWER_IS_BETTER:
        if high < 0:
            return "policy_a_better"
        if low > 0:
            return "policy_a_worse"
    else:
        if low > 0:
            return "policy_a_better"
        if high < 0:
            return "policy_a_worse"
    return "no_clear_difference"
