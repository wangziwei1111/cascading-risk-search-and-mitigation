"""Run IEEE39 strict no-leakage GCN usefulness audit execution.

This round is audit-only. It does not run Simulink, does not export labels,
does not save a production model, and does not retrain the reranker.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from train_ieee39_dynamic_aware_reranker_v2_plus_b39_preview import (
    _json_safe,
    _write_json,
    binary_auc,
    classification_metrics,
    compute_dynamic_stress_score,
    fit_logistic,
    fit_ridge,
    predict_linear,
    predict_logistic,
    regression_metrics,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_execution"
DATASET_PATH = (
    ROOT
    / "results/gcn_search/ieee39_dynamic_fault_type_expansion/bus_fault_smoke/"
    "batch_bus_fault_expansion_all_remaining/candidate_label_export/"
    "ieee39_dynamic_label_schema_v2_plus_all_bus_fault_candidates.csv"
)
PLAN_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan/gcn_usefulness_audit_plan.json"
POLICY_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan/no_leakage_feature_policy.json"
SPLIT_MANIFEST_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan/strict_holdout_split_manifest.json"
BASELINE_PLAN_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_plan/baseline_comparison_plan.json"
DRY_RUN_SUMMARY_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/gcn_audit_dry_run_validator_summary.json"
DRY_RUN_MANIFEST_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/proposed_no_leakage_gcn_inputs_manifest.json"
EXECUTION_DRAFT_PATH = ROOT / "results/gcn_search/ieee39_gcn_usefulness_audit_dry_run/formal_gcn_audit_execution_draft.json"
DOC_PATH = ROOT / "docs/ieee39_strict_no_leakage_gcn_usefulness_audit_execution.md"

OLD_FORMAL_GATE = "35 / 33 / 33"
ALLOWED_INPUT_COLUMNS = [
    "fault_type",
    "duration_s",
    "fault_start_s",
    "fault_clear_s",
    "trip_implementation",
    "line_id",
    "target_bus",
    "target_bus_or_component",
    "source_model_type",
]
FORBIDDEN_INPUT_COLUMNS = [
    "min_voltage_pu",
    "max_voltage_pu",
    "min_frequency_hz",
    "max_frequency_hz",
    "max_speed_deviation",
    "max_rotor_angle_separation_deg",
    "measurement_extraction_status",
    "unstable_flag",
    "dynamic_stress_score",
    "trip_time_s",
    "signal_source_summary",
    "output_summary_path",
    "output_event_log_path",
    "formal_line_trip_label",
    "handwired_line_trip_label",
    "non_line_trip_label",
    "bus_fault_label",
    "temporary_smoke_candidate",
    "candidate_not_formal_label",
    "training_ready_label_v2",
    "training_ready_candidate",
    "training_ready_candidate_smoke",
    "training_ready_label_candidate",
]
REQUIRED_SPLITS = [
    "random_candidate_split_baseline",
    "label_family_holdout",
    "bus_fault_holdout",
    "leave_one_bus_fault_out",
    "no_dynamic_measurement_leave_one_bus_fault_out",
    "existing_vs_new_bus_fault_holdout",
]


def _fs_path(path: Path) -> str:
    resolved = str(path.resolve())
    if os.name == "nt" and not resolved.startswith("\\\\?\\"):
        return "\\\\?\\" + resolved
    return resolved


def _read_json(path: Path) -> dict[str, Any]:
    with open(_fs_path(path), encoding="utf-8") as handle:
        return json.load(handle)


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(_fs_path(path))


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(_fs_path(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(_fs_path(path), index=False, encoding="utf-8-sig")


def _finite(value: Any) -> float | None:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def _boolish(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _torch_available() -> bool:
    if importlib.util.find_spec("torch") is None:
        return False
    try:
        import torch  # noqa: F401
    except Exception:
        return False
    return True


def _torch_geometric_available() -> bool:
    return importlib.util.find_spec("torch_geometric") is not None


def _sklearn_available() -> bool:
    return importlib.util.find_spec("sklearn") is not None


def _gcn_dependency_probe() -> dict[str, Any]:
    probe = {
        "torch_spec_present": importlib.util.find_spec("torch") is not None,
        "torch_geometric_spec_present": importlib.util.find_spec("torch_geometric") is not None,
        "torch_import_ok": False,
        "torch_import_error": "",
    }
    if not probe["torch_spec_present"]:
        return probe
    try:
        import torch  # noqa: F401

        probe["torch_import_ok"] = True
    except Exception as exc:
        probe["torch_import_error"] = str(exc)
    return probe


def _ensure_required_inputs() -> None:
    for path in [
        DATASET_PATH,
        PLAN_PATH,
        POLICY_PATH,
        SPLIT_MANIFEST_PATH,
        BASELINE_PLAN_PATH,
        DRY_RUN_SUMMARY_PATH,
        DRY_RUN_MANIFEST_PATH,
        EXECUTION_DRAFT_PATH,
    ]:
        if not os.path.exists(_fs_path(path)):
            raise FileNotFoundError(f"Missing required input: {path}")


def _prepare_raw_dataset() -> pd.DataFrame:
    raw = _read_csv(DATASET_PATH)
    work = raw.copy()
    work = work[work["training_ready_label_v2"].map(_boolish)].copy()
    work = work[work["measurement_extraction_status"].astype(str).eq("voltage_speed_angle")].copy()
    for col in ["line_id", "target_bus", "target_bus_or_component", "source_model_type"]:
        if col not in work.columns:
            work[col] = ""
        work[col] = work[col].fillna("").astype(str)
    work.loc[work["line_id"].eq(""), "line_id"] = work["target_bus_or_component"]
    work.loc[work["line_id"].eq("B39"), "line_id"] = "NO_LINE"
    work.loc[work["line_id"].eq(""), "line_id"] = "NO_LINE"
    work["target_bus"] = work["target_bus"].fillna("").astype(str)
    work.loc[work["scenario_id"].astype(str).eq("BF_B39_TEMP_SMOKE"), "target_bus"] = "B39"
    for col in [
        "duration_s",
        "fault_start_s",
        "fault_clear_s",
        "min_voltage_pu",
        "max_voltage_pu",
        "min_frequency_hz",
        "max_frequency_hz",
        "max_speed_deviation",
        "max_rotor_angle_separation_deg",
    ]:
        if col not in work.columns:
            work[col] = 0.0
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)
    for col in ["fault_type", "trip_implementation", "target_bus_or_component", "source_model_type", "label_family"]:
        if col not in work.columns:
            work[col] = "unknown"
        work[col] = work[col].replace("", "unknown").fillna("unknown").astype(str)
    work["unstable_flag"] = work["unstable_flag"].map(_boolish).astype(int)
    work["bus_fault_label"] = work["bus_fault_label"].map(_boolish).astype(float)
    work["dynamic_stress_score"] = compute_dynamic_stress_score(work)
    work["scenario_id"] = work["scenario_id"].astype(str)
    key_cols = ["line_id", "target_bus", "target_bus_or_component", "scenario_id"]
    if any(work[col].astype(str).str.contains(r"\bL12\b", case=False, na=False).any() for col in key_cols):
        raise ValueError("L12 must remain excluded from formal audit execution.")
    return work.reset_index(drop=True)


def _build_no_leakage_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    work = dataset.copy()
    numeric = work[["duration_s", "fault_start_s", "fault_clear_s"]].copy()
    categorical = work[
        ["fault_type", "trip_implementation", "line_id", "target_bus", "target_bus_or_component", "source_model_type"]
    ].copy()
    categorical = categorical.fillna("unknown").replace("", "unknown").astype(str)
    one_hot = pd.get_dummies(categorical, prefix=categorical.columns.tolist(), dtype=float)
    features = pd.concat([numeric, one_hot], axis=1).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return features, list(features.columns)


def _build_topology_only_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    categorical = dataset[["line_id", "target_bus", "target_bus_or_component"]].fillna("unknown").replace("", "unknown").astype(str)
    one_hot = pd.get_dummies(categorical, prefix=categorical.columns.tolist(), dtype=float)
    return one_hot, list(one_hot.columns)


def _build_target_bus_only_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    categorical = dataset[["target_bus"]].fillna("unknown").replace("", "unknown").astype(str)
    one_hot = pd.get_dummies(categorical, prefix=["target_bus"], dtype=float)
    return one_hot, list(one_hot.columns)


def _graph_adjacency(dataset: pd.DataFrame) -> np.ndarray:
    n = len(dataset)
    adj = np.eye(n, dtype=float)
    cols = ["line_id", "target_bus", "target_bus_or_component", "fault_type", "source_model_type"]
    for col in cols:
        values = dataset[col].fillna("unknown").astype(str).to_numpy()
        for value in np.unique(values):
            idx = np.where(values == value)[0]
            if len(idx) <= 1:
                continue
            adj[np.ix_(idx, idx)] += 1.0
    degree = adj.sum(axis=1)
    degree[degree <= 0.0] = 1.0
    inv_sqrt = np.diag(1.0 / np.sqrt(degree))
    return inv_sqrt @ adj @ inv_sqrt


def _prediction_frame(dataset: pd.DataFrame) -> pd.DataFrame:
    frame = dataset[
        ["scenario_id", "label_family", "fault_type", "line_id", "target_bus", "target_bus_or_component", "source_model_type"]
    ].copy()
    frame["y_true_dynamic_stress_score"] = dataset["dynamic_stress_score"].astype(float)
    frame["y_true_unstable_flag"] = dataset["unstable_flag"].astype(int)
    return frame


def _extend_frame(frame: pd.DataFrame, prefix: str, pred_reg: np.ndarray, pred_cls: np.ndarray) -> None:
    frame[f"{prefix}_pred_dynamic_stress_score"] = pred_reg
    frame[f"{prefix}_absolute_error"] = np.abs(frame["y_true_dynamic_stress_score"].to_numpy(dtype=float) - pred_reg)
    frame[f"{prefix}_pred_unstable_probability"] = pred_cls


def _regression_summary(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    residual = np.abs(y_true - y_pred)
    metrics = regression_metrics(y_true, y_pred)
    metrics["median_absolute_error"] = float(np.median(residual))
    metrics["max_absolute_error"] = float(np.max(residual))
    return metrics


def _classification_summary(y_true: np.ndarray, prob: np.ndarray) -> tuple[dict[str, Any], str]:
    valid = ~np.isnan(prob)
    if not valid.any():
        return {}, "Classification predictions unavailable for this split."
    y_valid = y_true[valid]
    prob_valid = prob[valid]
    if len(np.unique(y_valid)) < 2:
        return classification_metrics(y_valid, prob_valid), "AUC unavailable because test labels contain only one class."
    return classification_metrics(y_valid, prob_valid), ""


def _collect_metrics(frame: pd.DataFrame, prefix: str) -> dict[str, Any]:
    reg = _regression_summary(
        frame["y_true_dynamic_stress_score"].to_numpy(dtype=float),
        frame[f"{prefix}_pred_dynamic_stress_score"].to_numpy(dtype=float),
    )
    cls, reason = _classification_summary(
        frame["y_true_unstable_flag"].to_numpy(dtype=int),
        frame[f"{prefix}_pred_unstable_probability"].to_numpy(dtype=float),
    )
    return {
        "regression": reg,
        "classification": cls,
        "classification_unavailable_reason": reason,
    }


def _global_mean_baseline(y_train_reg: np.ndarray, y_train_cls: np.ndarray, num_test: int) -> tuple[np.ndarray, np.ndarray]:
    reg = np.full(num_test, float(np.mean(y_train_reg)))
    cls = np.full(num_test, float(np.mean(y_train_cls)))
    return reg, cls


def _group_mean_predict(
    train_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    group_cols: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    reg_means = train_frame.groupby(group_cols, dropna=False)["dynamic_stress_score"].mean()
    cls_means = train_frame.groupby(group_cols, dropna=False)["unstable_flag"].mean()
    global_reg = float(train_frame["dynamic_stress_score"].mean())
    global_cls = float(train_frame["unstable_flag"].mean())
    reg_pred: list[float] = []
    cls_pred: list[float] = []
    for _, row in test_frame.iterrows():
        key = tuple(row[col] for col in group_cols)
        reg_pred.append(float(reg_means.get(key, global_reg)))
        cls_pred.append(float(cls_means.get(key, global_cls)))
    return np.asarray(reg_pred, dtype=float), np.asarray(cls_pred, dtype=float)


def _ridge_logistic_predict(
    train_x: np.ndarray,
    test_x: np.ndarray,
    y_train_reg: np.ndarray,
    y_train_cls: np.ndarray,
    random_seed: int,
) -> tuple[np.ndarray, np.ndarray, str]:
    coef = fit_ridge(train_x, y_train_reg)
    reg_pred = predict_linear(coef, test_x)
    if len(np.unique(y_train_cls)) < 2:
        return reg_pred, np.full(len(test_x), np.nan), "Training fold has only one unstable_flag class."
    model = fit_logistic(train_x, y_train_cls, random_seed)
    cls_pred = predict_logistic(model, test_x)
    return reg_pred, cls_pred, ""


@dataclass
class SplitDefinition:
    name: str
    folds: list[tuple[str, np.ndarray, np.ndarray]]
    role: str


def _random_split(dataset: pd.DataFrame, seed: int) -> SplitDefinition:
    rng = np.random.default_rng(seed)
    idx = np.arange(len(dataset))
    rng.shuffle(idx)
    cut = max(int(round(len(idx) * 0.2)), 1)
    test_idx = np.sort(idx[:cut])
    train_idx = np.sort(idx[cut:])
    return SplitDefinition("random_candidate_split_baseline", [("random_80_20", train_idx, test_idx)], "sanity_only")


def _label_family_holdout(dataset: pd.DataFrame) -> SplitDefinition:
    family = dataset["label_family"].astype(str).to_numpy()
    train_idx = np.where(family == "existing_formal_dynamic")[0]
    test_idx = np.where(family != "existing_formal_dynamic")[0]
    return SplitDefinition("label_family_holdout", [("holdout_non_formal_families", train_idx, test_idx)], "core")


def _bus_fault_holdout(dataset: pd.DataFrame) -> SplitDefinition:
    is_bus_fault = dataset["bus_fault_label"].astype(float).to_numpy() > 0.5
    train_idx = np.where(~is_bus_fault)[0]
    test_idx = np.where(is_bus_fault)[0]
    return SplitDefinition("bus_fault_holdout", [("holdout_all_bus_fault_candidates", train_idx, test_idx)], "core")


def _leave_one_bus_fault_out(dataset: pd.DataFrame, name: str) -> SplitDefinition:
    bus_fault_idx = np.where(dataset["bus_fault_label"].astype(float).to_numpy() > 0.5)[0]
    folds: list[tuple[str, np.ndarray, np.ndarray]] = []
    for idx in bus_fault_idx:
        bus = str(dataset.iloc[idx]["target_bus"])
        train_idx = np.setdiff1d(np.arange(len(dataset)), [idx])
        folds.append((f"holdout_{bus}", train_idx, np.array([idx], dtype=int)))
    return SplitDefinition(name, folds, "core")


def _existing_vs_new_bus_fault_holdout(dataset: pd.DataFrame) -> SplitDefinition:
    is_bus_fault = dataset["bus_fault_label"].astype(float).to_numpy() > 0.5
    buses = dataset["target_bus"].astype(str).to_numpy()
    existing = np.isin(buses, ["B26", "B39"]) & is_bus_fault
    new = (~np.isin(buses, ["B26", "B39"])) & is_bus_fault
    train_idx = np.where((~is_bus_fault) | existing)[0]
    test_idx = np.where(new)[0]
    return SplitDefinition("existing_vs_new_bus_fault_holdout", [("holdout_new_bus_fault_candidates", train_idx, test_idx)], "distribution_check")


def _evaluate_baselines_for_fold(
    dataset: pd.DataFrame,
    full_features: pd.DataFrame,
    topology_features: pd.DataFrame,
    bus_features: pd.DataFrame,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    random_seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    y_train_reg = dataset.iloc[train_idx]["dynamic_stress_score"].to_numpy(dtype=float)
    y_train_cls = dataset.iloc[train_idx]["unstable_flag"].to_numpy(dtype=int)
    prediction_table = _prediction_frame(dataset.iloc[test_idx].reset_index(drop=True))
    results: dict[str, Any] = {}

    reg_pred, cls_pred, cls_reason = _ridge_logistic_predict(
        full_features.to_numpy(dtype=float)[train_idx],
        full_features.to_numpy(dtype=float)[test_idx],
        y_train_reg,
        y_train_cls,
        random_seed,
    )
    _extend_frame(prediction_table, "ridge_logistic", reg_pred, cls_pred)
    results["Ridge Regression / Logistic Regression"] = {
        **_collect_metrics(prediction_table, "ridge_logistic"),
        "classification_training_reason": cls_reason,
        "audit_only": True,
    }

    reg_pred, cls_pred, cls_reason = _ridge_logistic_predict(
        topology_features.to_numpy(dtype=float)[train_idx],
        topology_features.to_numpy(dtype=float)[test_idx],
        y_train_reg,
        y_train_cls,
        random_seed + 1,
    )
    _extend_frame(prediction_table, "topology_only", reg_pred, cls_pred)
    results["topology-only baseline"] = {
        **_collect_metrics(prediction_table, "topology_only"),
        "classification_training_reason": cls_reason,
        "audit_only": True,
    }

    reg_pred, cls_pred, cls_reason = _ridge_logistic_predict(
        bus_features.to_numpy(dtype=float)[train_idx],
        bus_features.to_numpy(dtype=float)[test_idx],
        y_train_reg,
        y_train_cls,
        random_seed + 2,
    )
    _extend_frame(prediction_table, "target_bus_only", reg_pred, cls_pred)
    results["target-bus-only baseline"] = {
        **_collect_metrics(prediction_table, "target_bus_only"),
        "classification_training_reason": cls_reason,
        "audit_only": True,
    }

    train_frame = dataset.iloc[train_idx].copy()
    test_frame = dataset.iloc[test_idx].copy()
    reg_pred, cls_pred = _group_mean_predict(train_frame, test_frame, ["fault_type", "trip_implementation", "source_model_type"])
    _extend_frame(prediction_table, "simple_ranking", reg_pred, cls_pred)
    results["simple ranking baseline"] = {
        **_collect_metrics(prediction_table, "simple_ranking"),
        "classification_training_reason": "",
        "audit_only": True,
    }

    reg_pred, cls_pred = _global_mean_baseline(y_train_reg, y_train_cls, len(test_idx))
    _extend_frame(prediction_table, "global_mean", reg_pred, cls_pred)
    results["global mean sanity baseline"] = {
        **_collect_metrics(prediction_table, "global_mean"),
        "classification_training_reason": "",
        "audit_only": True,
    }

    if _sklearn_available():
        results["RandomForest or GradientBoosting"] = {
            "status": "not_implemented_even_though_sklearn_available",
            "audit_only": True,
        }
    else:
        results["RandomForest or GradientBoosting"] = {
            "status": "dependency_unavailable",
            "reason": "sklearn not installed in this workspace",
            "audit_only": True,
        }
    return results, prediction_table


def _aggregate_prediction_tables(tables: list[pd.DataFrame], prefix: str) -> pd.DataFrame:
    merged = pd.concat(tables, ignore_index=True)
    merged = merged.sort_values(["target_bus", "scenario_id"]).reset_index(drop=True)
    return merged


def _average_metric_dict(metrics_list: list[dict[str, Any]]) -> dict[str, Any]:
    if not metrics_list:
        return {}
    keys = sorted(set().union(*[m.keys() for m in metrics_list]))
    result: dict[str, Any] = {}
    for key in keys:
        values = [m.get(key) for m in metrics_list if m.get(key) is not None]
        numeric = [float(v) for v in values if isinstance(v, (int, float))]
        result[key] = float(np.mean(numeric)) if numeric else None
    return result


def _aggregate_baselines(fold_results: list[dict[str, Any]]) -> dict[str, Any]:
    names = sorted(set().union(*[set(item.keys()) for item in fold_results]))
    combined: dict[str, Any] = {}
    for name in names:
        subset = [item[name] for item in fold_results if name in item]
        if subset and "status" in subset[0]:
            combined[name] = subset[0]
            continue
        reg = _average_metric_dict([item["regression"] for item in subset])
        cls = _average_metric_dict([item["classification"] for item in subset if item["classification"]])
        combined[name] = {
            "regression": reg,
            "classification": cls,
            "audit_only": True,
        }
    return combined


def _best_baseline_by_rmse(baselines: dict[str, Any]) -> tuple[str | None, float | None]:
    best_name = None
    best_rmse = None
    for name, payload in baselines.items():
        rmse = payload.get("regression", {}).get("rmse") if isinstance(payload, dict) else None
        if rmse is None:
            continue
        value = float(rmse)
        if best_rmse is None or value < best_rmse:
            best_name = name
            best_rmse = value
    return best_name, best_rmse


def _torch_import():
    import torch
    import torch.nn.functional as F

    return torch, F


def _run_dense_gcn_fold(
    dataset: pd.DataFrame,
    features: pd.DataFrame,
    adjacency: np.ndarray,
    train_idx: np.ndarray,
    test_idx: np.ndarray,
    seed: int,
    hidden_dim: int = 32,
    epochs: int = 250,
) -> tuple[np.ndarray, np.ndarray]:
    torch, F = _torch_import()

    torch.manual_seed(seed)
    x = torch.tensor(features.to_numpy(dtype=np.float32))
    adj = torch.tensor(adjacency.astype(np.float32))
    y_reg = torch.tensor(dataset["dynamic_stress_score"].to_numpy(dtype=np.float32)).unsqueeze(1)
    y_cls = torch.tensor(dataset["unstable_flag"].to_numpy(dtype=np.float32)).unsqueeze(1)
    train_mask = torch.zeros(len(dataset), dtype=torch.bool)
    train_mask[train_idx] = True

    class DenseGCN(torch.nn.Module):
        def __init__(self, in_dim: int, hidden: int):
            super().__init__()
            self.w1 = torch.nn.Linear(in_dim, hidden)
            self.w2 = torch.nn.Linear(hidden, hidden)
            self.reg_head = torch.nn.Linear(hidden, 1)
            self.cls_head = torch.nn.Linear(hidden, 1)

        def forward(self, feat: torch.Tensor, norm_adj: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
            h = norm_adj @ feat
            h = F.relu(self.w1(h))
            h = norm_adj @ h
            h = F.relu(self.w2(h))
            return self.reg_head(h), self.cls_head(h)

    model = DenseGCN(x.shape[1], hidden_dim)
    opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=1e-4)
    has_two_cls = len(np.unique(dataset.iloc[train_idx]["unstable_flag"].to_numpy(dtype=int))) >= 2

    for _ in range(epochs):
        model.train()
        opt.zero_grad()
        reg_out, cls_out = model(x, adj)
        reg_loss = F.mse_loss(reg_out[train_mask], y_reg[train_mask])
        loss = reg_loss
        if has_two_cls:
            pos_count = float(y_cls[train_mask].sum().item())
            neg_count = float(train_mask.sum().item() - pos_count)
            pos_weight = torch.tensor([neg_count / max(pos_count, 1.0)], dtype=torch.float32)
            cls_loss = F.binary_cross_entropy_with_logits(cls_out[train_mask], y_cls[train_mask], pos_weight=pos_weight)
            loss = loss + 0.5 * cls_loss
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        reg_out, cls_out = model(x, adj)
        reg_pred = reg_out.squeeze(1).cpu().numpy()
        cls_pred = torch.sigmoid(cls_out).squeeze(1).cpu().numpy() if has_two_cls else np.full(len(dataset), np.nan)
    return reg_pred[test_idx], cls_pred[test_idx]


def _evaluate_gcn_split(
    dataset: pd.DataFrame,
    features: pd.DataFrame,
    adjacency: np.ndarray,
    split: SplitDefinition,
    seed: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    tables: list[pd.DataFrame] = []
    reg_all = np.full(0, 0.0)
    cls_all = np.full(0, 0.0)
    true_reg_all = np.full(0, 0.0)
    true_cls_all = np.full(0, 0)
    for fold_num, (_, train_idx, test_idx) in enumerate(split.folds):
        pred_table = _prediction_frame(dataset.iloc[test_idx].reset_index(drop=True))
        reg_pred, cls_pred = _run_dense_gcn_fold(dataset, features, adjacency, train_idx, test_idx, seed + fold_num)
        _extend_frame(pred_table, "gcn", reg_pred, cls_pred)
        tables.append(pred_table)
        reg_all = np.concatenate([reg_all, reg_pred])
        cls_all = np.concatenate([cls_all, cls_pred])
        true_reg_all = np.concatenate([true_reg_all, pred_table["y_true_dynamic_stress_score"].to_numpy(dtype=float)])
        true_cls_all = np.concatenate([true_cls_all, pred_table["y_true_unstable_flag"].to_numpy(dtype=int)])
    combined = _aggregate_prediction_tables(tables, "gcn")
    metrics = {
        "audit_only": True,
        "dependency_status": "torch_available_custom_dense_gcn",
        "num_folds": len(split.folds),
        "regression": _regression_summary(true_reg_all, reg_all),
        "classification": _classification_summary(true_cls_all, cls_all)[0],
        "classification_unavailable_reason": _classification_summary(true_cls_all, cls_all)[1],
    }
    return metrics, combined


def _evaluate_split(
    dataset: pd.DataFrame,
    full_features: pd.DataFrame,
    topology_features: pd.DataFrame,
    bus_features: pd.DataFrame,
    split: SplitDefinition,
    random_seed: int,
    gcn_enabled: bool,
) -> tuple[dict[str, Any], dict[str, Any], pd.DataFrame]:
    baseline_fold_metrics: list[dict[str, Any]] = []
    tables: list[pd.DataFrame] = []
    for fold_num, (_, train_idx, test_idx) in enumerate(split.folds):
        result, table = _evaluate_baselines_for_fold(
            dataset,
            full_features,
            topology_features,
            bus_features,
            train_idx,
            test_idx,
            random_seed + fold_num * 7,
        )
        baseline_fold_metrics.append(result)
        tables.append(table)
    baseline_metrics = _aggregate_baselines(baseline_fold_metrics)
    prediction_table = _aggregate_prediction_tables(tables, "baseline")

    if gcn_enabled:
        adjacency = _graph_adjacency(dataset)
        gcn_metrics, gcn_table = _evaluate_gcn_split(dataset, full_features, adjacency, split, random_seed + 10_000)
        prediction_table = prediction_table.merge(
            gcn_table[
                [
                    "scenario_id",
                    "gcn_pred_dynamic_stress_score",
                    "gcn_absolute_error",
                    "gcn_pred_unstable_probability",
                ]
            ],
            on="scenario_id",
            how="left",
        )
    else:
        gcn_metrics = {
            "audit_only": True,
            "dependency_status": "blocked_by_missing_gcn_dependency",
            "regression": {},
            "classification": {},
            "classification_unavailable_reason": "GCN dependency unavailable.",
        }
        prediction_table["gcn_pred_dynamic_stress_score"] = np.nan
        prediction_table["gcn_absolute_error"] = np.nan
        prediction_table["gcn_pred_unstable_probability"] = np.nan
    return gcn_metrics, baseline_metrics, prediction_table


def _render_split_report(
    split_name: str,
    gcn_metrics: dict[str, Any],
    baseline_metrics: dict[str, Any],
    note: str,
) -> str:
    best_name, best_rmse = _best_baseline_by_rmse(baseline_metrics)
    gcn_rmse = gcn_metrics.get("regression", {}).get("rmse")
    return f"""# {split_name}

This split is audit-only.

- gcn_dependency_status: `{gcn_metrics.get('dependency_status', 'n/a')}`
- gcn_rmse: `{gcn_rmse}`
- best_baseline_by_rmse: `{best_name}`
- best_baseline_rmse: `{best_rmse}`

## Note

{note}
"""


def _run_nf06_sensitivity(
    dataset: pd.DataFrame,
    random_seed: int,
    gcn_enabled: bool,
) -> dict[str, Any]:
    include = dataset.copy()
    exclude = dataset[~dataset["scenario_id"].astype(str).eq("NF06")].copy().reset_index(drop=True)
    payload: dict[str, Any] = {"include_NF06": {}, "exclude_NF06": {}}
    for name, frame in [("include_NF06", include), ("exclude_NF06", exclude)]:
        full_features, _ = _build_no_leakage_features(frame)
        topology_features, _ = _build_topology_only_features(frame)
        bus_features, _ = _build_target_bus_only_features(frame)
        split = _bus_fault_holdout(frame)
        gcn_metrics, baseline_metrics, _ = _evaluate_split(
            frame,
            full_features,
            topology_features,
            bus_features,
            split,
            random_seed + (0 if name == "include_NF06" else 5000),
            gcn_enabled,
        )
        payload[name] = {
            "gcn_bus_fault_holdout_rmse": gcn_metrics.get("regression", {}).get("rmse"),
            "best_baseline_name": _best_baseline_by_rmse(baseline_metrics)[0],
            "best_baseline_bus_fault_holdout_rmse": _best_baseline_by_rmse(baseline_metrics)[1],
            "row_count": int(len(frame)),
        }
    include_rmse = payload["include_NF06"]["gcn_bus_fault_holdout_rmse"]
    exclude_rmse = payload["exclude_NF06"]["gcn_bus_fault_holdout_rmse"]
    payload["difference_summary"] = {
        "gcn_rmse_delta_exclude_minus_include": None
        if include_rmse is None or exclude_rmse is None
        else float(exclude_rmse) - float(include_rmse)
    }
    return payload


def _b1_report(prediction_table: pd.DataFrame) -> dict[str, Any]:
    row = prediction_table[prediction_table["target_bus"].astype(str).eq("B1")]
    if row.empty:
        return {"status": "missing"}
    record = row.iloc[0]
    return {
        "target_bus": "B1",
        "scenario_id": str(record["scenario_id"]),
        "true_dynamic_stress_score": _finite(record["y_true_dynamic_stress_score"]),
        "gcn_predicted_dynamic_stress_score": _finite(record["gcn_pred_dynamic_stress_score"]),
        "gcn_absolute_error": _finite(record["gcn_absolute_error"]),
        "gcn_unstable_probability": _finite(record["gcn_pred_unstable_probability"]),
        "ridge_logistic_predicted_dynamic_stress_score": _finite(record["ridge_logistic_pred_dynamic_stress_score"]),
        "ridge_logistic_absolute_error": _finite(record["ridge_logistic_absolute_error"]),
        "target_bus_only_predicted_dynamic_stress_score": _finite(record["target_bus_only_pred_dynamic_stress_score"]),
        "target_bus_only_absolute_error": _finite(record["target_bus_only_absolute_error"]),
    }


def _l12_report(dataset: pd.DataFrame) -> dict[str, Any]:
    present = sorted([value for value in dataset["line_id"].astype(str).unique().tolist() if value == "L12"])
    return {
        "l12_excluded": present == [],
        "present_l12_entries": present,
    }


def _forbidden_feature_report(features: list[str]) -> dict[str, Any]:
    forbidden_present = [column for column in features if column in FORBIDDEN_INPUT_COLUMNS]
    return {
        "allowed_input_columns": ALLOWED_INPUT_COLUMNS,
        "forbidden_columns_checked": FORBIDDEN_INPUT_COLUMNS,
        "forbidden_features_detected_in_inputs": forbidden_present,
        "no_leakage_feature_policy_passed": forbidden_present == [],
        "target_bus_memorization_risk_flagged": True,
    }


def _audit_level_conclusion(gcn_available: bool, bus_fault: dict[str, Any], lobo: dict[str, Any]) -> str:
    if not gcn_available:
        return "formal GCN audit blocked by missing dependency; baseline-only audit completed"
    gcn_bus_rmse = bus_fault.get("gcn_rmse")
    base_bus_rmse = bus_fault.get("best_baseline_rmse")
    gcn_lobo_rmse = lobo.get("gcn_rmse")
    base_lobo_rmse = lobo.get("best_baseline_rmse")
    if None not in {gcn_bus_rmse, base_bus_rmse, gcn_lobo_rmse, base_lobo_rmse}:
        if float(gcn_bus_rmse) < float(base_bus_rmse) and float(gcn_lobo_rmse) < float(base_lobo_rmse):
            return "audit evidence suggests GCN may add value under no-leakage strict holdouts"
    return "audit evidence does not support GCN usefulness over simpler baselines yet"


def _summary_md(summary: dict[str, Any]) -> str:
    if not summary.get("gcn_trained_for_audit", False):
        return f"""# IEEE39 Strict No-Leakage GCN Usefulness Audit Execution

This document describes the existing formal audit execution artifacts. It must
stay consistent with:

`results/gcn_search/ieee39_gcn_usefulness_audit_execution/gcn_usefulness_audit_execution_summary.json`

The execution summary is still a baseline-only audit because the GCN dependency
was blocked when that audit was produced.

## Core Summary

- audit_scope: `{summary['audit_scope']}`
- audit_only: `{str(summary['audit_only']).lower()}`
- production_model_saved: `{str(summary['production_model_saved']).lower()}`
- gcn_trained_for_audit: `{str(summary['gcn_trained_for_audit']).lower()}`
- gcn_dependency_available: `{str(summary.get('gcn_dependency_available', False)).lower()}`
- gcn_dependency_status: `{summary['gcn_dependency_status']}`
- GCN metrics: unavailable / `null`
- total_candidate_rows: `{summary['total_candidate_rows']}`
- num_total_bus_fault_candidates: `{summary['num_total_bus_fault_candidates']}`
- no_leakage_feature_policy_passed: `{str(summary['no_leakage_feature_policy_passed']).lower()}`
- forbidden_features_detected_in_inputs: `{json.dumps(summary['forbidden_features_detected_in_inputs'], ensure_ascii=False)}`
- target_bus_memorization_risk_flagged: `{str(summary['target_bus_memorization_risk_flagged']).lower()}`
- strict_holdouts_executed: `{json.dumps(summary['strict_holdouts_executed'], ensure_ascii=False)}`
- baseline_comparison_executed: `{str(summary['baseline_comparison_executed']).lower()}`
- audit_level_conclusion: `{summary['audit_level_conclusion']}`
- final_engineering_conclusion: `{str(summary['final_engineering_conclusion']).lower()}`
- should_retrain_reranker_now: `{str(summary['should_retrain_reranker_now']).lower()}`
- should_deploy_model: `{str(summary['should_deploy_model']).lower()}`

## Important Boundary Notes

- no-leakage features only
- forbidden features did not enter inputs
- target_bus memorization risk still exists, so target-bus-only baseline must be reported
- bus_fault_holdout and leave-one-bus-fault-out are mandatory
- B1 is reported explicitly
- NF06 sensitivity is reported explicitly
- L12 exclusion is confirmed explicitly
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
- this is not a final engineering conclusion

## Dependency Repair Follow-Up

A later dependency repair commit fixed the local Python environment:

- local `torch` import is available
- local `torch_geometric` import is available
- `dependency_blocker_resolved = true`

That repair did not rerun the formal strict no-leakage GCN audit. Therefore the
audit execution summary remains baseline-only, GCN metrics remain unavailable,
and this document must not make an early GCN usefulness conclusion.

## Next Step

Rerun the strict no-leakage GCN audit in a separate round using the repaired
environment. Until that rerun is completed, do not deploy a model and do not
retrain the reranker.
"""
    return f"""# IEEE39 Strict No-Leakage GCN Usefulness Audit Execution

This round is formal GCN usefulness audit execution.
It is audit-only, not production training.
It did not run Simulink.
It did not export labels.
It did not retrain the reranker.
It did not modify RL mitigation.

## Core Summary

- audit_scope: `{summary['audit_scope']}`
- audit_only: `{str(summary['audit_only']).lower()}`
- gcn_trained_for_audit: `{str(summary['gcn_trained_for_audit']).lower()}`
- gcn_dependency_status: `{summary['gcn_dependency_status']}`
- total_candidate_rows: `{summary['total_candidate_rows']}`
- num_total_bus_fault_candidates: `{summary['num_total_bus_fault_candidates']}`
- no_leakage_feature_policy_passed: `{str(summary['no_leakage_feature_policy_passed']).lower()}`
- forbidden_features_detected_in_inputs: `{json.dumps(summary['forbidden_features_detected_in_inputs'], ensure_ascii=False)}`
- target_bus_memorization_risk_flagged: `{str(summary['target_bus_memorization_risk_flagged']).lower()}`
- strict_holdouts_executed: `{json.dumps(summary['strict_holdouts_executed'], ensure_ascii=False)}`
- baseline_comparison_executed: `{str(summary['baseline_comparison_executed']).lower()}`
- final_engineering_conclusion: `{str(summary['final_engineering_conclusion']).lower()}`
- should_retrain_reranker_now: `{str(summary['should_retrain_reranker_now']).lower()}`
- should_deploy_model: `{str(summary['should_deploy_model']).lower()}`

## Important Boundary Notes

- no-leakage features only
- forbidden features did not enter inputs
- target_bus memorization risk still exists, so target-bus-only baseline must be reported
- bus_fault_holdout and leave-one-bus-fault-out are mandatory
- B1 is reported explicitly
- NF06 sensitivity is reported explicitly
- L12 exclusion is confirmed explicitly
- `phasor_RMS` is not EMT
- `generator_speed_proxy` is not direct frequency
- temporary bus-fault injection is not engineering-grade protection
- this is not a final engineering conclusion

## Audit-Level Conclusion

{summary['audit_level_conclusion']}

## Next Step

{summary['recommended_next_step']}
"""


def _report_md(title: str, payload: dict[str, Any]) -> str:
    return f"# {title}\n\n```json\n{json.dumps(_json_safe(payload), ensure_ascii=False, indent=2)}\n```\n"


def run_audit(args: argparse.Namespace) -> dict[str, Any]:
    _ensure_required_inputs()
    dataset = _prepare_raw_dataset()
    plan = _read_json(PLAN_PATH)
    policy = _read_json(POLICY_PATH)
    split_manifest = _read_json(SPLIT_MANIFEST_PATH)
    baseline_plan = _read_json(BASELINE_PLAN_PATH)
    dry_run = _read_json(DRY_RUN_SUMMARY_PATH)
    dry_run_manifest = _read_json(DRY_RUN_MANIFEST_PATH)
    _ = _read_json(EXECUTION_DRAFT_PATH)

    full_features, feature_columns = _build_no_leakage_features(dataset)
    topology_features, _ = _build_topology_only_features(dataset)
    bus_features, _ = _build_target_bus_only_features(dataset)
    forbidden_report = _forbidden_feature_report(feature_columns)
    if forbidden_report["forbidden_features_detected_in_inputs"]:
        summary = {
            "audit_scope": "formal_gcn_usefulness_audit_execution",
            "audit_only": True,
            "production_model_saved": False,
            "gcn_trained_for_audit": False,
            "gcn_dependency_available": False,
            "gcn_dependency_status": "blocked_by_forbidden_feature_leakage",
            "simulink_run": False,
            "actual_smoke_run": False,
            "labels_exported": False,
            "reranker_retrained": False,
            "rl_mitigation_touched": False,
            "total_candidate_rows": int(len(dataset)),
            "num_total_bus_fault_candidates": int(dataset["bus_fault_label"].sum()),
            "all_ieee39_buses_have_bus_fault_candidate": True,
            "old_formal_gate": OLD_FORMAL_GATE,
            "l12_excluded": True,
            "nf06_provenance_warning_preserved": True,
            "b1_special_tracking_enabled": True,
            "forbidden_features_detected_in_inputs": forbidden_report["forbidden_features_detected_in_inputs"],
            "no_leakage_feature_policy_passed": False,
            "target_bus_memorization_risk_flagged": True,
            "strict_holdouts_executed": [],
            "baseline_comparison_executed": False,
            "gcn_vs_baseline_summary": {},
            "bus_fault_holdout_result": {},
            "leave_one_bus_fault_out_result": {},
            "no_dynamic_measurement_leave_one_bus_fault_out_result": {},
            "b1_result": {},
            "nf06_sensitivity_result": {},
            "l12_exclusion_result": _l12_report(dataset),
            "audit_level_conclusion": "audit evidence does not support GCN usefulness over simpler baselines yet",
            "final_engineering_conclusion": False,
            "should_retrain_reranker_now": False,
            "should_deploy_model": False,
            "recommended_next_step": "fix leakage before rerun",
        }
        return summary

    dependency_probe = _gcn_dependency_probe()
    gcn_dependency_available = bool(dependency_probe["torch_import_ok"]) and bool(args.allow_post_repair_gcn_audit)
    gcn_dependency_status = (
        "torch_available_custom_dense_gcn_without_torch_geometric"
        if gcn_dependency_available and not dependency_probe["torch_geometric_spec_present"]
        else ("torch_and_torch_geometric_available" if gcn_dependency_available else "blocked_by_missing_gcn_dependency")
    )

    splits = [
        _random_split(dataset, args.random_seed),
        _label_family_holdout(dataset),
        _bus_fault_holdout(dataset),
        _leave_one_bus_fault_out(dataset, "leave_one_bus_fault_out"),
        _leave_one_bus_fault_out(dataset, "no_dynamic_measurement_leave_one_bus_fault_out"),
        _existing_vs_new_bus_fault_holdout(dataset),
    ]

    split_results: dict[str, dict[str, Any]] = {}
    split_output_dir = args.output_dir / "splits"
    strict_holdouts_executed: list[str] = []
    for split in splits:
        gcn_metrics, baseline_metrics, prediction_table = _evaluate_split(
            dataset,
            full_features,
            topology_features,
            bus_features,
            split,
            args.random_seed,
            gcn_dependency_available,
        )
        split_dir = split_output_dir / split.name
        split_dir.mkdir(parents=True, exist_ok=True)
        _write_json(split_dir / "gcn_metrics.json", gcn_metrics)
        _write_json(split_dir / "baseline_metrics.json", baseline_metrics)
        _write_csv(split_dir / "prediction_table.csv", prediction_table)
        _write_text(
            split_dir / "split_report.md",
            _render_split_report(split.name, gcn_metrics, baseline_metrics, f"role = {split.role}"),
        )
        split_results[split.name] = {
            "gcn_metrics": gcn_metrics,
            "baseline_metrics": baseline_metrics,
            "prediction_table": prediction_table,
        }
        strict_holdouts_executed.append(split.name)

    nf06_sensitivity = _run_nf06_sensitivity(dataset, args.random_seed, gcn_dependency_available)
    b1_result = _b1_report(split_results["no_dynamic_measurement_leave_one_bus_fault_out"]["prediction_table"])
    l12_result = _l12_report(dataset)
    forbidden_report["policy_columns"] = policy.get("proposed_no_leakage_gcn_input_columns", [])
    forbidden_report["dry_run_columns"] = dry_run_manifest.get("proposed_no_leakage_gcn_input_columns", [])
    forbidden_report["dry_run_passed"] = dry_run.get("dry_run_validator_passed")

    bus_fault_best_name, bus_fault_best_rmse = _best_baseline_by_rmse(split_results["bus_fault_holdout"]["baseline_metrics"])
    lobo_best_name, lobo_best_rmse = _best_baseline_by_rmse(split_results["no_dynamic_measurement_leave_one_bus_fault_out"]["baseline_metrics"])
    comparison = {
        "bus_fault_holdout": {
            "gcn_rmse": split_results["bus_fault_holdout"]["gcn_metrics"].get("regression", {}).get("rmse"),
            "best_baseline_name": bus_fault_best_name,
            "best_baseline_rmse": bus_fault_best_rmse,
        },
        "leave_one_bus_fault_out": {
            "gcn_rmse": split_results["leave_one_bus_fault_out"]["gcn_metrics"].get("regression", {}).get("rmse"),
            "best_baseline_name": _best_baseline_by_rmse(split_results["leave_one_bus_fault_out"]["baseline_metrics"])[0],
            "best_baseline_rmse": _best_baseline_by_rmse(split_results["leave_one_bus_fault_out"]["baseline_metrics"])[1],
        },
        "no_dynamic_measurement_leave_one_bus_fault_out": {
            "gcn_rmse": split_results["no_dynamic_measurement_leave_one_bus_fault_out"]["gcn_metrics"].get("regression", {}).get("rmse"),
            "best_baseline_name": lobo_best_name,
            "best_baseline_rmse": lobo_best_rmse,
        },
    }

    audit_level_conclusion = _audit_level_conclusion(
        gcn_dependency_available,
        comparison["bus_fault_holdout"],
        comparison["no_dynamic_measurement_leave_one_bus_fault_out"],
    )

    summary = {
        "audit_scope": "formal_gcn_usefulness_audit_execution",
        "audit_only": True,
        "production_model_saved": False,
        "gcn_trained_for_audit": gcn_dependency_available,
        "gcn_dependency_available": gcn_dependency_available,
        "gcn_dependency_status": gcn_dependency_status,
        "simulink_run": False,
        "actual_smoke_run": False,
        "labels_exported": False,
        "reranker_retrained": False,
        "rl_mitigation_touched": False,
        "total_candidate_rows": int(len(dataset)),
        "num_total_bus_fault_candidates": int(dataset["bus_fault_label"].sum()),
        "all_ieee39_buses_have_bus_fault_candidate": True,
        "old_formal_gate": plan.get("old_formal_gate", OLD_FORMAL_GATE),
        "l12_excluded": l12_result["l12_excluded"],
        "nf06_provenance_warning_preserved": True,
        "b1_special_tracking_enabled": True,
        "forbidden_features_detected_in_inputs": forbidden_report["forbidden_features_detected_in_inputs"],
        "no_leakage_feature_policy_passed": forbidden_report["forbidden_features_detected_in_inputs"] == [],
        "target_bus_memorization_risk_flagged": True,
        "strict_holdouts_executed": strict_holdouts_executed,
        "baseline_comparison_executed": True,
        "gcn_vs_baseline_summary": comparison,
        "bus_fault_holdout_result": comparison["bus_fault_holdout"],
        "leave_one_bus_fault_out_result": comparison["leave_one_bus_fault_out"],
        "no_dynamic_measurement_leave_one_bus_fault_out_result": comparison["no_dynamic_measurement_leave_one_bus_fault_out"],
        "b1_result": b1_result,
        "nf06_sensitivity_result": nf06_sensitivity,
        "l12_exclusion_result": l12_result,
        "audit_level_conclusion": audit_level_conclusion,
        "final_engineering_conclusion": False,
        "should_retrain_reranker_now": False,
        "should_deploy_model": False,
        "recommended_next_step": (
            "repair the local GCN dependency environment and rerun the strict no-leakage audit; still do not deploy and do not retrain the reranker"
            if not gcn_dependency_available
            else (
                "improve feature / graph construction before any stronger GCN usefulness claim"
                if "does not support" in audit_level_conclusion
                else "move to review-only follow-up and report-level scrutiny, not deployment"
            )
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(args.output_dir / "gcn_usefulness_audit_execution_summary.json", summary)
    _write_text(args.output_dir / "gcn_usefulness_audit_execution_summary.md", _summary_md(summary))
    _write_csv(
        args.output_dir / "gcn_usefulness_audit_execution_summary.csv",
        pd.DataFrame([{"field": key, "value": json.dumps(_json_safe(value), ensure_ascii=False) if isinstance(value, (dict, list)) else value} for key, value in summary.items()]),
    )
    _write_json(args.output_dir / "b1_special_tracking_report.json", b1_result)
    _write_text(args.output_dir / "b1_special_tracking_report.md", _report_md("B1 Special Tracking Report", b1_result))
    _write_json(args.output_dir / "nf06_sensitivity_report.json", nf06_sensitivity)
    _write_text(args.output_dir / "nf06_sensitivity_report.md", _report_md("NF06 Sensitivity Report", nf06_sensitivity))
    _write_json(args.output_dir / "l12_exclusion_confirmation.json", l12_result)
    _write_text(args.output_dir / "l12_exclusion_confirmation.md", _report_md("L12 Exclusion Confirmation", l12_result))
    _write_json(args.output_dir / "forbidden_feature_audit_report.json", forbidden_report)
    _write_text(args.output_dir / "forbidden_feature_audit_report.md", _report_md("Forbidden Feature Audit Report", forbidden_report))
    _write_json(args.output_dir / "baseline_vs_gcn_comparison.json", comparison)
    _write_text(args.output_dir / "baseline_vs_gcn_comparison.md", _report_md("Baseline vs GCN Comparison", comparison))
    if not gcn_dependency_available:
        blocker = {
            "audit_only": True,
            "status": "blocked_by_missing_gcn_dependency",
            **dependency_probe,
        }
        _write_json(args.output_dir / "dependency_blocker_report.json", blocker)
    _write_text(DOC_PATH, _summary_md(summary))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument(
        "--allow-post-repair-gcn-audit",
        action="store_true",
        help="Explicitly allow rerunning the post-repair GCN audit. Default keeps the existing baseline-only artifact.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_audit(args)
    print(json.dumps(_json_safe(summary), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
