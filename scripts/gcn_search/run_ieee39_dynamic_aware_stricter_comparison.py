from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from train_ieee39_dynamic_aware_reranker_preview import (
    classification_metrics,
    fit_logistic,
    fit_ridge,
    predict_linear,
    predict_logistic,
    regression_metrics,
)


DEFAULT_DATASET = "results/gcn_search/ieee39_dynamic_aware_reranker_preview_expanded/preview_training_dataset.csv"
DEFAULT_LINE_MAP = "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
DEFAULT_LABEL_SUMMARY = "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_label_quality_summary.json"
DEFAULT_READINESS = "results/gcn_search/ieee39_dynamic_labels/ieee39_dynamic_aware_training_readiness.json"
DEFAULT_OUTPUT_DIR = "results/gcn_search/ieee39_dynamic_aware_reranker_stricter_comparison"
TARGET_COLUMNS = ["dynamic_stress_score", "unstable_flag"]
MEASUREMENT_FEATURES = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
]


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset = pd.read_csv(args.expanded_dataset)
    line_map = pd.read_csv(args.line_map)
    label_summary = _read_json(Path(args.label_summary))
    readiness = _read_json(Path(args.readiness))
    _assert_gate(label_summary, readiness)

    dataset = dataset[dataset["line_id"].astype(str).ne("L12")].copy()
    dataset = dataset[dataset["measurement_extraction_status"].astype(str).eq("voltage_speed_angle")].copy()
    dataset = dataset[dataset["training_ready_candidate"].astype(str).str.lower().isin({"1", "true"})].copy()
    dataset = enrich_topology(dataset, line_map)
    feature_sets = build_feature_sets(dataset)
    split_strategies = build_split_strategies(dataset, random_seed=args.random_seed)

    all_predictions: list[pd.DataFrame] = []
    all_metrics: dict[str, dict[str, Any]] = {}
    skipped: dict[str, str] = {}
    for feature_set_name, feature_columns in feature_sets.items():
        all_metrics[feature_set_name] = {}
        x = build_feature_table(dataset, feature_columns)
        for split_name, folds in split_strategies.items():
            result = evaluate_split(
                dataset=dataset,
                x=x,
                folds=folds,
                random_seed=args.random_seed,
                feature_set_name=feature_set_name,
                split_name=split_name,
            )
            all_metrics[feature_set_name][split_name] = result["metrics"]
            if result["classification_skipped_reason"]:
                skipped[f"{feature_set_name}/{split_name}"] = result["classification_skipped_reason"]
            all_predictions.append(result["predictions"])

    predictions = pd.concat(all_predictions, ignore_index=True)
    metrics_payload = {
        "preview_only": True,
        "final_performance_conclusion": False,
        "num_samples": int(len(dataset)),
        "excluded_line_ids": ["L12"],
        "target_columns": TARGET_COLUMNS,
        "feature_sets": feature_sets,
        "split_strategies": {name: describe_folds(dataset, folds) for name, folds in split_strategies.items()},
        "random_seed": int(args.random_seed),
        "per_feature_set_per_split_metrics": all_metrics,
        "best_no_leakage_result": best_result(all_metrics, ["no_dynamic_measurement_features", "topology_only_features"]),
        "best_leaky_result": best_result(all_metrics, ["leaky_dynamic_measurement_features"]),
        "leakage_gap_summary": leakage_gap_summary(all_metrics),
        "classification_skipped_reasons": skipped,
        "caveats": [
            "preview / sanity check only",
            "phasor_RMS, not EMT",
            "generator_speed_proxy is not direct frequency",
            "handwired breaker is pilot breaker-like validation, not engineering-grade protection",
            "L12 excluded because it is simulation_timeout / suspected islanding",
        ],
    }
    config_payload = {
        "expanded_dataset": args.expanded_dataset,
        "line_map": args.line_map,
        "label_summary": args.label_summary,
        "readiness": args.readiness,
        "output_dir": args.output_dir,
        "random_seed": args.random_seed,
        "split_rules": {
            "grouped_line_range_holdout": "L01-L10, L11-L20, L21-L34; L12 excluded; non-line rows use auxiliary fold.",
            "endpoint_bus_region_holdout": "line rows grouped by average endpoint bus: low <=10, mid <=24, high >24; non-line rows use auxiliary fold.",
            "random_kfold_baseline": "K=5, shuffle=True, random_seed=42; baseline only.",
        },
    }

    dataset.to_csv(out_dir / "stricter_comparison_dataset.csv", index=False, encoding="utf-8-sig")
    predictions.to_csv(out_dir / "stricter_comparison_predictions.csv", index=False, encoding="utf-8-sig")
    (out_dir / "stricter_comparison_config.json").write_text(json.dumps(_json_safe(config_payload), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "stricter_comparison_metrics.json").write_text(json.dumps(_json_safe(metrics_payload), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "stricter_comparison_feature_sets.json").write_text(json.dumps(_json_safe(feature_sets), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "stricter_comparison_summary.md").write_text(render_summary(metrics_payload), encoding="utf-8")
    (out_dir / "stricter_comparison_leakage_notes.md").write_text(render_leakage_notes(metrics_payload), encoding="utf-8")
    print(json.dumps({"output_dir": str(out_dir), "num_samples": len(dataset)}, ensure_ascii=False, indent=2))


def enrich_topology(dataset: pd.DataFrame, line_map: pd.DataFrame) -> pd.DataFrame:
    line_map = line_map.copy()
    line_map["from_bus_numeric"] = line_map["from_bus"].map(bus_number)
    line_map["to_bus_numeric"] = line_map["to_bus"].map(bus_number)
    line_map["line_map_inventory_order"] = np.arange(1, len(line_map) + 1)
    graph = build_graph(line_map)
    degrees = {node: len(neigh) for node, neigh in graph.items()}
    topo_rows = []
    reference = {"B1", "B39"}
    for _, row in line_map.iterrows():
        a, b = str(row["from_bus"]), str(row["to_bus"])
        component, largest = component_after_remove(graph, a, frozenset((a, b)))
        contains_ref_or_main = bool(component & reference) or len(component) == len(largest)
        topo_rows.append(
            {
                "line_id": row["line_id"],
                "from_bus_numeric": bus_number(a),
                "to_bus_numeric": bus_number(b),
                "min_bus": min(bus_number(a), bus_number(b)),
                "max_bus": max(bus_number(a), bus_number(b)),
                "bus_distance_abs": abs(bus_number(a) - bus_number(b)),
                "endpoint_degree_from": degrees.get(a, 0),
                "endpoint_degree_to": degrees.get(b, 0),
                "component_size_after_line_removed": len(component),
                "largest_component_size_after_line_removed": len(largest),
                "component_contains_reference_or_main_grid": int(contains_ref_or_main),
                "islanding_candidate": int(not contains_ref_or_main),
                "line_map_inventory_order": int(row["line_map_inventory_order"]),
            }
        )
    topology = pd.DataFrame(topo_rows)
    out = dataset.merge(topology, on="line_id", how="left")
    topology_defaults = [col for col in topology.columns if col != "line_id"]
    for col in topology_defaults:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)
    out["source_model"] = out["source_model"].fillna("unknown").astype(str)
    return out.reset_index(drop=True)


def build_feature_sets(dataset: pd.DataFrame) -> dict[str, list[str]]:
    leaky = MEASUREMENT_FEATURES + [
        "breaker_opened",
        "physical_fault_or_breaker_action_executed",
        "fault_type",
        "trip_implementation",
        "line_id",
    ]
    no_dynamic = [
        "fault_type",
        "trip_implementation",
        "line_id",
        "line_id_numeric",
        "from_bus_numeric",
        "to_bus_numeric",
        "min_bus",
        "max_bus",
        "bus_distance_abs",
        "line_map_inventory_order",
        "endpoint_degree_from",
        "endpoint_degree_to",
        "islanding_candidate",
        "component_size_after_line_removed",
        "component_contains_reference_or_main_grid",
        "source_model",
    ]
    topology = [
        "from_bus_numeric",
        "to_bus_numeric",
        "min_bus",
        "max_bus",
        "bus_distance_abs",
        "endpoint_degree_from",
        "endpoint_degree_to",
        "component_size_after_line_removed",
        "largest_component_size_after_line_removed",
        "component_contains_reference_or_main_grid",
        "islanding_candidate",
        "fault_type",
        "trip_implementation",
    ]
    return {
        "leaky_dynamic_measurement_features": [c for c in leaky if c in dataset.columns],
        "no_dynamic_measurement_features": [c for c in no_dynamic if c in dataset.columns],
        "topology_only_features": [c for c in topology if c in dataset.columns],
    }


def build_feature_table(dataset: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    numeric = dataset[[c for c in columns if pd.api.types.is_numeric_dtype(dataset[c])]].copy()
    categorical_cols = [c for c in columns if c not in numeric.columns]
    one_hot = pd.get_dummies(dataset[categorical_cols].astype(str), prefix=categorical_cols, dtype=float) if categorical_cols else pd.DataFrame(index=dataset.index)
    features = pd.concat([numeric, one_hot], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features


def build_split_strategies(dataset: pd.DataFrame, random_seed: int) -> dict[str, list[tuple[str, np.ndarray, np.ndarray]]]:
    n = len(dataset)
    folds: dict[str, list[tuple[str, np.ndarray, np.ndarray]]] = {}
    folds["leave_one_out"] = [(str(i), np.where(np.arange(n) != i)[0], np.array([i])) for i in range(n)]

    line_nums = dataset["line_id"].map(line_number).to_numpy()
    ranges = {
        "L01-L10": (line_nums >= 1) & (line_nums <= 10),
        "L11-L20": (line_nums >= 11) & (line_nums <= 20) & (line_nums != 12),
        "L21-L34": (line_nums >= 21) & (line_nums <= 34),
        "non_line_aux": line_nums == 0,
    }
    folds["grouped_line_range_holdout"] = make_group_folds(ranges, n)

    avg_bus = ((dataset["from_bus_numeric"] + dataset["to_bus_numeric"]) / 2.0).to_numpy()
    region_groups = {
        "low_bus_region": (avg_bus > 0) & (avg_bus <= 10),
        "mid_bus_region": (avg_bus > 10) & (avg_bus <= 24),
        "high_bus_region": avg_bus > 24,
        "non_line_aux": avg_bus == 0,
    }
    folds["endpoint_bus_region_holdout"] = make_group_folds(region_groups, n)

    rng = np.random.default_rng(random_seed)
    order = rng.permutation(n)
    random_folds = []
    for fold_id, test_idx in enumerate(np.array_split(order, 5)):
        train_idx = np.setdiff1d(np.arange(n), test_idx)
        random_folds.append((str(fold_id), train_idx, np.asarray(test_idx, dtype=int)))
    folds["random_kfold_baseline"] = random_folds
    return folds


def make_group_folds(groups: dict[str, np.ndarray], n: int) -> list[tuple[str, np.ndarray, np.ndarray]]:
    folds = []
    all_idx = np.arange(n)
    for name, mask in groups.items():
        test_idx = np.where(mask)[0]
        if len(test_idx) == 0:
            continue
        folds.append((name, np.setdiff1d(all_idx, test_idx), test_idx))
    return folds


def evaluate_split(
    dataset: pd.DataFrame,
    x: pd.DataFrame,
    folds: list[tuple[str, np.ndarray, np.ndarray]],
    random_seed: int,
    feature_set_name: str,
    split_name: str,
) -> dict[str, Any]:
    y_reg = dataset["dynamic_stress_score"].to_numpy(dtype=float)
    y_cls = dataset["unstable_flag"].to_numpy(dtype=int)
    matrix = x.to_numpy(dtype=float)
    pred_reg = np.full(len(dataset), np.nan)
    pred_cls = np.full(len(dataset), np.nan)
    class_skip_reasons = []
    rows = []
    for fold_id, train_idx, test_idx in folds:
        coef = fit_ridge(matrix[train_idx], y_reg[train_idx], alpha=1.0)
        pred_reg[test_idx] = predict_linear(coef, matrix[test_idx])
        if len(np.unique(y_cls[train_idx])) >= 2:
            model = fit_logistic(matrix[train_idx], y_cls[train_idx], l2=0.1, learning_rate=0.2, epochs=800, random_seed=random_seed + len(rows))
            pred_cls[test_idx] = predict_logistic(model, matrix[test_idx])
        else:
            class_skip_reasons.append(f"{fold_id}: training fold has one unstable_flag class")
        fold_rows = dataset.iloc[test_idx][["line_id", "test_case", "unstable_flag", "dynamic_stress_score"]].copy()
        fold_rows["feature_set"] = feature_set_name
        fold_rows["split_strategy"] = split_name
        fold_rows["fold_id"] = fold_id
        fold_rows["y_true_dynamic_stress_score"] = fold_rows["dynamic_stress_score"]
        fold_rows["y_pred_dynamic_stress_score"] = pred_reg[test_idx]
        fold_rows["residual"] = fold_rows["y_true_dynamic_stress_score"] - fold_rows["y_pred_dynamic_stress_score"]
        fold_rows["y_true_unstable_flag"] = fold_rows["unstable_flag"]
        fold_rows["y_pred_unstable_score"] = pred_cls[test_idx]
        fold_rows["note"] = "stricter preview comparison; not final dynamic performance"
        rows.append(fold_rows.drop(columns=["unstable_flag", "dynamic_stress_score"]))
    valid = ~np.isnan(pred_reg)
    cls_available = not np.isnan(pred_cls).any() and len(np.unique(y_cls[valid])) >= 2
    metrics = {
        "regression": regression_metrics(y_reg[valid], pred_reg[valid]),
        "classification": classification_metrics(y_cls[valid], pred_cls[valid]) if cls_available else {},
        "num_predictions": int(valid.sum()),
        "num_folds": len(folds),
    }
    return {
        "metrics": metrics,
        "classification_skipped_reason": "; ".join(class_skip_reasons) if not cls_available else "",
        "predictions": pd.concat(rows, ignore_index=True),
    }


def best_result(all_metrics: dict[str, dict[str, Any]], feature_sets: list[str]) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_rmse = float("inf")
    for fs in feature_sets:
        for split, metrics in all_metrics.get(fs, {}).items():
            rmse = metrics.get("regression", {}).get("rmse")
            if rmse is not None and rmse < best_rmse:
                best_rmse = rmse
                best = {"feature_set": fs, "split_strategy": split, "regression": metrics["regression"], "classification": metrics.get("classification", {})}
    return best


def leakage_gap_summary(all_metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    leaky = best_result(all_metrics, ["leaky_dynamic_measurement_features"])
    no_leak = best_result(all_metrics, ["no_dynamic_measurement_features", "topology_only_features"])
    leaky_rmse = leaky.get("regression", {}).get("rmse")
    no_leak_rmse = no_leak.get("regression", {}).get("rmse")
    return {
        "best_leaky_rmse": leaky_rmse,
        "best_no_leakage_rmse": no_leak_rmse,
        "rmse_gap_no_leak_minus_leaky": None if leaky_rmse is None or no_leak_rmse is None else float(no_leak_rmse - leaky_rmse),
        "interpretation": "A positive gap indicates that removing dynamic measurement features makes the task harder, which is expected and important.",
    }


def describe_folds(dataset: pd.DataFrame, folds: list[tuple[str, np.ndarray, np.ndarray]]) -> list[dict[str, Any]]:
    return [{"fold_id": fid, "num_train": int(len(tr)), "num_test": int(len(te)), "test_line_ids": sorted(dataset.iloc[te]["line_id"].astype(str).unique())} for fid, tr, te in folds]


def render_summary(metrics: dict[str, Any]) -> str:
    gap = metrics["leakage_gap_summary"]
    lines = [
        "# IEEE39 Dynamic-Aware Stricter Comparison",
        "",
        "This is a preview-only stricter comparison, not a final dynamic performance conclusion.",
        "",
        "The expanded 35-sample preview is more complete than the historical 10-sample preview. However, the leaky dynamic measurement feature set can still be optimistic because the target is derived from compact dynamic measurements.",
        "",
        "The no_dynamic_measurement_features and topology_only_features settings are closer to a realistic prediction scenario. If their metrics are worse than the leaky setting, that is an expected and important finding rather than a failure.",
        "",
        f"- num_samples: {metrics['num_samples']}",
        "- L12 excluded because it is timeout / suspected islanding.",
        f"- leakage gap summary: {gap}",
        "- phasor_RMS, not EMT.",
        "- generator_speed_proxy is not direct frequency.",
        "- handwired breaker is pilot breaker-like validation, not engineering-grade protection.",
        "- Future work needs more fault types, independent test sets, more operating conditions, and stricter leakage checks.",
    ]
    return "\n".join(lines) + "\n"


def render_leakage_notes(metrics: dict[str, Any]) -> str:
    return """# Leakage Notes

`leaky_dynamic_measurement_features` includes compact dynamic measurement
columns such as voltage, frequency proxy, speed deviation, and rotor-angle
separation. Because `dynamic_stress_score` is synthesized from the same compact
measurements, this setting is an optimistic preview upper-bound, not credible
generalization evidence.

`no_dynamic_measurement_features` removes those measurement columns but may
still include line identity, source-model category, and topology-derived
features. It is less leaky but still only preview evidence.

`topology_only_features` uses line-map / topology / fault-setup information and
avoids compact measurements and line_id one-hot features. This is the most
conservative preview feature set in this round.

No Simulink simulation was run. No `.slx` was modified. L12 remains excluded.
The result remains phasor_RMS preview evidence, not EMT. It is not a final
dynamic performance conclusion.
`generator_speed_proxy` is not direct frequency. The handwired breaker remains
pilot breaker-like validation, not engineering-grade protection.
"""


def build_graph(line_map: pd.DataFrame) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for _, row in line_map.iterrows():
        a, b = str(row["from_bus"]), str(row["to_bus"])
        graph[a].add(b)
        graph[b].add(a)
    return graph


def component_after_remove(graph: dict[str, set[str]], start: str, removed: frozenset[str]) -> tuple[set[str], set[str]]:
    g = {k: set(v) for k, v in graph.items()}
    a, b = tuple(removed)
    g.get(a, set()).discard(b)
    g.get(b, set()).discard(a)
    comp = connected_component(g, start)
    remaining = set(g)
    largest: set[str] = set()
    while remaining:
        c = connected_component(g, next(iter(remaining)))
        if len(c) > len(largest):
            largest = c
        remaining -= c
    return comp, largest


def connected_component(graph: dict[str, set[str]], start: str) -> set[str]:
    seen: set[str] = set()
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        queue.extend(sorted(graph.get(node, set()) - seen))
    return seen


def bus_number(value: object) -> int:
    text = str(value)
    return int(text[1:]) if text.startswith("B") and text[1:].isdigit() else 0


def line_number(value: object) -> int:
    text = str(value)
    return int(text[1:]) if text.startswith("L") and text[1:].isdigit() else 0


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _assert_gate(summary: dict[str, Any], readiness: dict[str, Any]) -> None:
    if summary.get("num_training_ready_labels") != 35:
        raise RuntimeError("Expected num_training_ready_labels=35.")
    if readiness.get("allowed_for_dynamic_aware_training") is not True:
        raise RuntimeError("Expected allowed_for_dynamic_aware_training=true.")
    if readiness.get("ready_for_preview_training") is not True:
        raise RuntimeError("Expected ready_for_preview_training=true.")
    by_line = summary.get("num_training_ready_handwired_line_trip_labels_by_line", {})
    if "L12" in by_line:
        raise RuntimeError("L12 must not be training-ready.")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(float(value)) else float(value)
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run IEEE39 dynamic-aware stricter leakage comparison.")
    parser.add_argument("--expanded-dataset", default=DEFAULT_DATASET)
    parser.add_argument("--line-map", default=DEFAULT_LINE_MAP)
    parser.add_argument("--label-summary", default=DEFAULT_LABEL_SUMMARY)
    parser.add_argument("--readiness", default=DEFAULT_READINESS)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--random-seed", type=int, default=42)
    return parser.parse_args()


if __name__ == "__main__":
    main()
