from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from rts79_cascade import (
    Rts79InitialConfig,
    line_label_to_index_1based,
    run_initial_dcopf,
    search_all_n2_cascade_paths,
)


@dataclass(frozen=True)
class DatasetConfig:
    """训练集配置；dataset 是“数据集”，config 是“配置”。"""

    num_scenarios: int = 5
    first_seed: int = 20260511
    load_scale: float = 1.1
    load_random_low: float = 0.9
    load_random_high: float = 1.1
    relay_threshold_beta: float = 1.2
    security_limit: float = 1.0
    max_paths_per_scenario: int | None = None


@dataclass(frozen=True)
class TrainConfig:
    """训练配置；train 是“训练”，epoch 是“一轮完整训练”。"""

    epochs: int = 800
    learning_rate: float = 5e-2
    l2: float = 1e-4
    validation_fraction: float = 0.2
    random_seed: int = 20260512


def build_training_dataset(config: DatasetConfig, output_dir: str | Path) -> pd.DataFrame:
    """生成 RTS-79 训练集；每个样本是一条有序 N-2 初始故障路径。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scenario_tables: list[pd.DataFrame] = []
    scenario_summaries: list[dict] = []

    for scenario_id in range(1, config.num_scenarios + 1):
        seed = config.first_seed + scenario_id - 1
        initial_config = Rts79InitialConfig(
            random_seed=seed,
            load_scale=config.load_scale,
            load_random_low=config.load_random_low,
            load_random_high=config.load_random_high,
        )
        print(f"[数据集] 场景 {scenario_id}/{config.num_scenarios}，随机种子 seed={seed}")
        initial_state = run_initial_dcopf(initial_config)
        search_result = search_all_n2_cascade_paths(
            config=initial_config,
            relay_threshold_beta=config.relay_threshold_beta,
            security_limit=config.security_limit,
            max_paths=config.max_paths_per_scenario,
        )
        table = search_result.summary_table.copy()
        table.insert(0, "scenario_id", scenario_id)
        table.insert(1, "seed", seed)
        table["first_line_index"] = table["first_line"].map(line_label_to_index_1based)
        table["second_line_index"] = table["second_line"].map(line_label_to_index_1based)
        table["first_line_index_norm"] = table["first_line_index"] / 38.0
        table["second_line_index_norm"] = table["second_line_index"] / 38.0
        table["line_order_delta_norm"] = (table["second_line_index"] - table["first_line_index"]) / 38.0
        table = pd.concat(
            [
                table,
                _make_scenario_feature_frame(len(table), initial_state.bus_table, initial_state.branch_table),
                _make_path_one_hot_feature_frame(table, num_lines=38),
            ],
            axis=1,
        )
        table["critical_label"] = table["critical"].astype(int)
        table["final_outage_count"] = table["final_outage_labels"].fillna("").map(_count_final_outages)
        scenario_tables.append(table)
        scenario_summaries.append(
            {
                "scenario_id": scenario_id,
                "seed": seed,
                "num_paths": int(search_result.num_paths),
                "num_critical_paths": int(search_result.num_critical_paths),
                "critical_ratio": float(search_result.num_critical_paths / max(search_result.num_paths, 1)),
                "max_total_load_shed_mw": float(table["total_load_shed_mw"].max(skipna=True)),
            }
        )

    dataset = pd.concat(scenario_tables, ignore_index=True)
    dataset_path = out / "rts79_training_dataset.csv"
    summary_path = out / "rts79_training_scenario_summary.csv"
    config_path = out / "rts79_training_dataset_config.json"
    dataset.to_csv(dataset_path, index=False, encoding="utf-8-sig")
    pd.DataFrame(scenario_summaries).to_csv(summary_path, index=False, encoding="utf-8-sig")
    config_path.write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[数据集] 已保存: {dataset_path}")
    return dataset


def train_surrogate_model(
    dataset: pd.DataFrame,
    train_config: TrainConfig,
    output_dir: str | Path,
) -> dict:
    """训练二分类替代模型；binary classification 是“二分类”。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    feature_columns = _select_feature_columns(dataset)
    clean = dataset.loc[dataset["error"].fillna("") == ""].copy()
    clean = clean.dropna(subset=feature_columns + ["critical_label"])
    train_idx, validation_idx = _split_train_validation(clean, train_config)

    x_train_raw = clean.loc[train_idx, feature_columns].to_numpy(dtype=np.float32)
    y_train = clean.loc[train_idx, "critical_label"].to_numpy(dtype=np.float32)
    x_validation_raw = clean.loc[validation_idx, feature_columns].to_numpy(dtype=np.float32)
    y_validation = clean.loc[validation_idx, "critical_label"].to_numpy(dtype=np.float32)

    mean = x_train_raw.mean(axis=0)
    std = x_train_raw.std(axis=0)
    std[std < 1e-8] = 1.0
    x_train = (x_train_raw - mean) / std
    x_validation = (x_validation_raw - mean) / std

    weights = np.zeros(x_train.shape[1], dtype=np.float64)
    bias = 0.0
    positives = max(float(y_train.sum()), 1.0)
    negatives = max(float(len(y_train) - y_train.sum()), 1.0)
    sample_weight = np.where(y_train > 0.5, negatives / positives, 1.0)

    for epoch in range(1, train_config.epochs + 1):
        logits = x_train @ weights + bias
        probabilities = _sigmoid(logits)
        error = (probabilities - y_train) * sample_weight
        grad_w = (x_train.T @ error) / len(y_train) + train_config.l2 * weights
        grad_b = float(error.mean())
        weights -= train_config.learning_rate * grad_w
        bias -= train_config.learning_rate * grad_b
        if epoch in {1, train_config.epochs} or epoch % 200 == 0:
            loss = _weighted_binary_cross_entropy(y_train, probabilities, sample_weight)
            metrics = _evaluate_model(weights, bias, x_validation, y_validation, threshold=0.5)
            print(
                "[训练] "
                f"epoch={epoch}, "
                f"loss={loss:.6f}, "
                f"validation_f1={metrics['f1']:.4f}, "
                f"validation_recall={metrics['recall']:.4f}"
            )

    validation_probabilities = _predict_probabilities(weights, bias, x_validation)
    best_threshold = _find_best_threshold(y_validation, validation_probabilities)
    validation_metrics = _evaluate_model(weights, bias, x_validation, y_validation, threshold=best_threshold)
    train_metrics = _evaluate_model(weights, bias, x_train, y_train, threshold=best_threshold)
    np.savez(
        out / "rts79_surrogate_logistic.npz",
        weights=weights,
        bias=np.array([bias], dtype=np.float64),
        feature_mean=mean,
        feature_std=std,
        threshold=np.array([best_threshold], dtype=np.float64),
    )
    (out / "rts79_surrogate_feature_columns.json").write_text(
        json.dumps(feature_columns, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "rts79_surrogate_train_config.json").write_text(
        json.dumps(asdict(train_config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    metrics_table = pd.DataFrame(
        [
            {"split": "train", "threshold": best_threshold, **train_metrics},
            {"split": "validation", "threshold": best_threshold, **validation_metrics},
        ]
    )
    metrics_table.to_csv(out / "rts79_surrogate_metrics.csv", index=False, encoding="utf-8-sig")
    prediction_table = _make_prediction_table(clean.loc[validation_idx].copy(), weights, bias, x_validation, best_threshold)
    prediction_table.to_csv(out / "rts79_surrogate_validation_predictions.csv", index=False, encoding="utf-8-sig")
    print(f"[训练] 已保存模型: {out / 'rts79_surrogate_logistic.npz'}")
    return {"train": train_metrics, "validation": validation_metrics}


def _make_scenario_feature_frame(row_count: int, bus_table: pd.DataFrame, branch_table: pd.DataFrame) -> pd.DataFrame:
    features: dict[str, float] = {}
    for _, row in bus_table.iterrows():
        bus_label = row["bus_label"]
        features[f"gamma_{bus_label}"] = float(row["load_factor"])
        features[f"P_D_new_{bus_label}_MW"] = float(row["P_D_MW"])
    for _, row in branch_table.iterrows():
        line_label = row["line_label"]
        features[f"initial_loading_{line_label}"] = float(row["loading_ratio"])
        features[f"initial_flow_{line_label}_MW"] = float(row["F_MW"])
    return pd.DataFrame({key: np.full(row_count, value) for key, value in features.items()})


def _make_path_one_hot_feature_frame(table: pd.DataFrame, num_lines: int) -> pd.DataFrame:
    features: dict[str, np.ndarray] = {}
    for line_idx in range(1, num_lines + 1):
        label = f"L{line_idx:02d}"
        features[f"first_is_{label}"] = (table["first_line"].to_numpy() == label).astype(int)
        features[f"second_is_{label}"] = (table["second_line"].to_numpy() == label).astype(int)
    return pd.DataFrame(features, index=table.index)


def _count_final_outages(value: str) -> int:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return 0
    return len([part for part in text.split(",") if part])


def _select_feature_columns(dataset: pd.DataFrame) -> list[str]:
    prefixes = (
        "gamma_",
        "P_D_new_",
        "initial_loading_",
        "initial_flow_",
        "first_is_",
        "second_is_",
    )
    feature_columns = [column for column in dataset.columns if column.startswith(prefixes)]
    feature_columns += ["first_line_index_norm", "second_line_index_norm", "line_order_delta_norm"]
    return feature_columns


def _split_train_validation(clean: pd.DataFrame, config: TrainConfig) -> tuple[pd.Index, pd.Index]:
    rng = np.random.default_rng(config.random_seed)
    scenario_ids = np.array(sorted(clean["scenario_id"].unique()))
    if len(scenario_ids) >= 2:
        rng.shuffle(scenario_ids)
        num_validation = max(1, int(round(len(scenario_ids) * config.validation_fraction)))
        validation_scenarios = set(scenario_ids[:num_validation])
        validation_mask = clean["scenario_id"].isin(validation_scenarios)
    else:
        validation_mask = pd.Series(False, index=clean.index)
        validation_size = max(1, int(round(len(clean) * config.validation_fraction)))
        validation_idx = rng.choice(clean.index.to_numpy(), size=validation_size, replace=False)
        validation_mask.loc[validation_idx] = True
    return clean.index[~validation_mask], clean.index[validation_mask]


def _sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(value, -50.0, 50.0)))


def _weighted_binary_cross_entropy(y: np.ndarray, probabilities: np.ndarray, sample_weight: np.ndarray) -> float:
    clipped = np.clip(probabilities, 1e-8, 1.0 - 1e-8)
    loss = -(y * np.log(clipped) + (1.0 - y) * np.log(1.0 - clipped))
    return float(np.average(loss, weights=sample_weight))


def _predict_probabilities(weights: np.ndarray, bias: float, x: np.ndarray) -> np.ndarray:
    return _sigmoid(x @ weights + bias)


def _find_best_threshold(y: np.ndarray, probabilities: np.ndarray) -> float:
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in np.linspace(0.05, 0.95, 91):
        metrics = _classification_metrics(y, probabilities, float(threshold))
        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_threshold = float(threshold)
    return best_threshold


def _evaluate_model(weights: np.ndarray, bias: float, x: np.ndarray, y: np.ndarray, threshold: float) -> dict:
    probabilities = _predict_probabilities(weights, bias, x)
    return _classification_metrics(y, probabilities, threshold)


def _classification_metrics(y: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    y_int = y.astype(int)
    tp = int(((predictions == 1) & (y_int == 1)).sum())
    tn = int(((predictions == 0) & (y_int == 0)).sum())
    fp = int(((predictions == 1) & (y_int == 0)).sum())
    fn = int(((predictions == 0) & (y_int == 1)).sum())
    accuracy = (tp + tn) / max(len(y_int), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-12)
    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def _make_prediction_table(
    validation_table: pd.DataFrame,
    weights: np.ndarray,
    bias: float,
    x_validation: np.ndarray,
    threshold: float,
) -> pd.DataFrame:
    probabilities = _predict_probabilities(weights, bias, x_validation)
    keep_columns = [
        "scenario_id",
        "seed",
        "path",
        "first_line",
        "second_line",
        "critical_label",
        "total_load_shed_mw",
        "final_outage_count",
    ]
    table = validation_table[keep_columns].copy()
    table["critical_probability"] = probabilities
    table["decision_threshold"] = threshold
    table["predicted_critical_label"] = (probabilities >= threshold).astype(int)
    return table.sort_values("critical_probability", ascending=False).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成 RTS-79 连锁故障训练集并训练替代模型。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "training"), help="输出目录。")
    parser.add_argument("--num-scenarios", type=int, default=5, help="负荷场景数量。")
    parser.add_argument("--first-seed", type=int, default=20260511, help="第一个随机种子。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="安全运行约束阈值。")
    parser.add_argument("--max-paths-per-scenario", type=int, default=None, help="每个场景最多搜索的路径数。")
    parser.add_argument("--epochs", type=int, default=800, help="训练轮数。")
    parser.add_argument("--dataset-csv", default=None, help="已有训练集 CSV 路径；如果提供则只训练，不重新仿真。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_config = DatasetConfig(
        num_scenarios=args.num_scenarios,
        first_seed=args.first_seed,
        relay_threshold_beta=args.beta,
        security_limit=args.security_limit,
        max_paths_per_scenario=args.max_paths_per_scenario,
    )
    train_config = TrainConfig(epochs=args.epochs)
    if args.dataset_csv:
        dataset = pd.read_csv(args.dataset_csv)
        print(f"[数据集] 已读取已有训练集: {args.dataset_csv}")
    else:
        dataset = build_training_dataset(dataset_config, args.output_dir)
    metrics = train_surrogate_model(dataset, train_config, args.output_dir)
    print("[结果] train 是“训练集”，validation 是“验证集”。")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
