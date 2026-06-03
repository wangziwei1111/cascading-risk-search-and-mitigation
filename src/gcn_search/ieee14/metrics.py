from __future__ import annotations

import numpy as np


def rankdata(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0
        start = end
    return ranks


def spearman_corr(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2:
        return 0.0
    rx = rankdata(np.asarray(x))
    ry = rankdata(np.asarray(y))
    if float(np.std(rx)) == 0.0 or float(np.std(ry)) == 0.0:
        return 0.0
    return float(np.corrcoef(rx, ry)[0, 1])


def topk_recall_by_true_risk(scores: np.ndarray, true_risk: np.ndarray, k: int) -> float:
    k = min(int(k), len(scores))
    if k <= 0:
        return 0.0
    pred_top = set(np.argsort(scores)[::-1][:k].tolist())
    true_top = set(np.argsort(true_risk)[::-1][:k].tolist())
    return len(pred_top.intersection(true_top)) / k


def pairwise_order_accuracy(scores: np.ndarray, true_risk: np.ndarray) -> float:
    total = 0
    correct = 0.0
    for i in range(len(scores)):
        for j in range(i + 1, len(scores)):
            diff = float(true_risk[i] - true_risk[j])
            if abs(diff) < 1e-9:
                continue
            total += 1
            pred_diff = float(scores[i] - scores[j])
            if pred_diff == 0.0:
                correct += 0.5
            elif pred_diff * diff > 0.0:
                correct += 1.0
    return float(correct / total) if total else 0.0


def evaluate_scenario_ranking(scores: np.ndarray, true_risk: np.ndarray) -> dict:
    top_k = min(10, len(scores))
    return {
        "spearman": spearman_corr(scores, true_risk),
        "pairwise_order_accuracy": pairwise_order_accuracy(scores, true_risk),
        "top10_recall": topk_recall_by_true_risk(scores, true_risk, top_k),
    }

