from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from pypower.idx_brch import F_BUS, RATE_A, T_BUS

from rts79_cascade import load_rts79_case


@dataclass(frozen=True)
class GcnTrainConfig:
    """GCN training config; GCN is graph convolutional network, 中文是“图卷积网络”。"""

    epochs: int = 200
    batch_size: int = 256
    learning_rate: float = 1e-3
    hidden_dim: int = 64
    validation_fraction: float = 0.2
    random_seed: int = 20260512


class DenseGcnLayer(nn.Module):
    """Dense GCN layer; layer 中文是“层”，dense 中文是“稠密矩阵形式”。"""

    def __init__(self, input_dim: int, output_dim: int) -> None:
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, node_features: torch.Tensor, normalized_adjacency: torch.Tensor) -> torch.Tensor:
        propagated = torch.einsum("ij,bjf->bif", normalized_adjacency, node_features)
        return self.linear(propagated)


class Rts79GcnClassifier(nn.Module):
    """RTS-79 GCN classifier; classifier 中文是“分类器”。"""

    def __init__(self, node_feature_dim: int, path_feature_dim: int, hidden_dim: int) -> None:
        super().__init__()
        self.gcn_1 = DenseGcnLayer(node_feature_dim, hidden_dim)
        self.gcn_2 = DenseGcnLayer(hidden_dim, hidden_dim)
        self.path_encoder = nn.Sequential(
            nn.Linear(path_feature_dim, hidden_dim),
            nn.ReLU(),
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.15),
            nn.Linear(hidden_dim, 1),
        )

    def forward(
        self,
        node_features: torch.Tensor,
        path_features: torch.Tensor,
        normalized_adjacency: torch.Tensor,
    ) -> torch.Tensor:
        h = torch.relu(self.gcn_1(node_features, normalized_adjacency))
        h = torch.relu(self.gcn_2(h, normalized_adjacency))
        graph_embedding = h.mean(dim=1)
        path_embedding = self.path_encoder(path_features)
        logits = self.classifier(torch.cat([graph_embedding, path_embedding], dim=1))
        return logits.squeeze(1)


def train_gcn_model(dataset_csv: str | Path, output_dir: str | Path, config: GcnTrainConfig) -> dict:
    """Train GCN model; train 中文是“训练”，model 中文是“模型”。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dataset = pd.read_csv(dataset_csv)
    clean = dataset.loc[dataset["error"].fillna("") == ""].copy()
    clean = clean.dropna(subset=["critical_label"])

    case = load_rts79_case()
    normalized_adjacency = torch.tensor(_build_normalized_adjacency(case), dtype=torch.float32)
    branch_table = _build_static_branch_table(case)

    train_index, validation_index = _split_by_scenario(clean, config)
    train_table = clean.loc[train_index].copy()
    validation_table = clean.loc[validation_index].copy()

    normalizer = _fit_feature_normalizer(train_table)
    x_node_train = _make_node_feature_tensor(train_table, branch_table, normalizer)
    x_path_train = _make_path_feature_tensor(train_table)
    y_train = train_table["critical_label"].to_numpy(dtype=np.float32)
    x_node_validation = _make_node_feature_tensor(validation_table, branch_table, normalizer)
    x_path_validation = _make_path_feature_tensor(validation_table)
    y_validation = validation_table["critical_label"].to_numpy(dtype=np.float32)

    torch.manual_seed(config.random_seed)
    model = Rts79GcnClassifier(
        node_feature_dim=x_node_train.shape[2],
        path_feature_dim=x_path_train.shape[1],
        hidden_dim=config.hidden_dim,
    )
    positives = max(float(y_train.sum()), 1.0)
    negatives = max(float(len(y_train) - y_train.sum()), 1.0)
    loss_function = nn.BCEWithLogitsLoss(pos_weight=torch.tensor([negatives / positives], dtype=torch.float32))
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)

    loader = DataLoader(
        TensorDataset(
            torch.tensor(x_node_train, dtype=torch.float32),
            torch.tensor(x_path_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.float32),
        ),
        batch_size=config.batch_size,
        shuffle=True,
    )
    for epoch in range(1, config.epochs + 1):
        model.train()
        running_loss = 0.0
        for node_batch, path_batch, label_batch in loader:
            optimizer.zero_grad()
            logits = model(node_batch, path_batch, normalized_adjacency)
            loss = loss_function(logits, label_batch)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.detach()) * len(label_batch)
        if epoch in {1, config.epochs} or epoch % 50 == 0:
            metrics = _evaluate_model(
                model,
                x_node_validation,
                x_path_validation,
                y_validation,
                normalized_adjacency,
                threshold=0.5,
            )
            print(
                "[GCN训练] "
                f"epoch={epoch}, "
                f"loss={running_loss / max(len(y_train), 1):.6f}, "
                f"validation_f1={metrics['f1']:.4f}, "
                f"validation_recall={metrics['recall']:.4f}"
            )

    validation_probability = _predict_probability(
        model,
        x_node_validation,
        x_path_validation,
        normalized_adjacency,
    )
    threshold = _find_best_threshold(y_validation, validation_probability)
    train_metrics = _evaluate_model(model, x_node_train, x_path_train, y_train, normalized_adjacency, threshold)
    validation_metrics = _evaluate_model(
        model,
        x_node_validation,
        x_path_validation,
        y_validation,
        normalized_adjacency,
        threshold,
    )

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(config),
            "normalizer": normalizer,
            "threshold": threshold,
            "node_feature_names": _node_feature_names(),
            "path_feature_names": _path_feature_names(),
            "normalized_adjacency": normalized_adjacency.numpy(),
        },
        out / "rts79_gcn_model.pt",
    )
    pd.DataFrame(
        [
            {"split": "train", "threshold": threshold, **train_metrics},
            {"split": "validation", "threshold": threshold, **validation_metrics},
        ]
    ).to_csv(out / "rts79_gcn_metrics.csv", index=False, encoding="utf-8-sig")
    _make_prediction_table(validation_table, validation_probability, threshold).to_csv(
        out / "rts79_gcn_validation_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (out / "rts79_gcn_train_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[GCN训练] 已保存模型: {out / 'rts79_gcn_model.pt'}")
    return {"train": train_metrics, "validation": validation_metrics}


def _build_static_branch_table(case: dict) -> pd.DataFrame:
    branch = case["branch"]
    return pd.DataFrame(
        {
            "line_label": [f"L{i:02d}" for i in range(1, branch.shape[0] + 1)],
            "from_bus": branch[:, F_BUS].astype(int),
            "to_bus": branch[:, T_BUS].astype(int),
            "F_max_MW": branch[:, RATE_A].astype(float),
        }
    )


def _build_normalized_adjacency(case: dict) -> np.ndarray:
    bus_count = case["bus"].shape[0]
    adjacency = np.eye(bus_count, dtype=np.float32)
    for row in case["branch"]:
        from_bus = int(row[F_BUS]) - 1
        to_bus = int(row[T_BUS]) - 1
        adjacency[from_bus, to_bus] = 1.0
        adjacency[to_bus, from_bus] = 1.0
    degree = adjacency.sum(axis=1)
    inv_sqrt_degree = np.diag(1.0 / np.sqrt(np.maximum(degree, 1e-8)))
    return inv_sqrt_degree @ adjacency @ inv_sqrt_degree


def _fit_feature_normalizer(train_table: pd.DataFrame) -> dict:
    values = {
        "P_D_new": _collect_columns(train_table, "P_D_new_B", "_MW"),
        "incident_loading_sum": None,
        "incident_loading_max": None,
    }
    branch_table = _build_static_branch_table(load_rts79_case())
    incident_sum, incident_max = _incident_loading_arrays(train_table, branch_table)
    values["incident_loading_sum"] = incident_sum
    values["incident_loading_max"] = incident_max
    return {
        name: {
            "mean": float(array.mean()),
            "std": float(max(array.std(), 1e-8)),
        }
        for name, array in values.items()
    }


def _make_node_feature_tensor(table: pd.DataFrame, branch_table: pd.DataFrame, normalizer: dict) -> np.ndarray:
    row_count = len(table)
    bus_count = 24
    node_features = np.zeros((row_count, bus_count, len(_node_feature_names())), dtype=np.float32)
    gamma = _bus_matrix(table, "gamma_B", "")
    p_load = _bus_matrix(table, "P_D_new_B", "_MW")
    incident_sum, incident_max = _incident_loading_arrays(table, branch_table)
    node_features[:, :, 0] = gamma
    node_features[:, :, 1] = _normalize(p_load, normalizer["P_D_new"])
    node_features[:, :, 2] = _normalize(incident_sum, normalizer["incident_loading_sum"])
    node_features[:, :, 3] = _normalize(incident_max, normalizer["incident_loading_max"])
    _mark_outage_endpoint_features(node_features, table, branch_table)
    return node_features


def _make_path_feature_tensor(table: pd.DataFrame) -> np.ndarray:
    features = np.zeros((len(table), len(_path_feature_names())), dtype=np.float32)
    first_indices = table["first_line_index"].to_numpy(dtype=int) - 1
    second_indices = table["second_line_index"].to_numpy(dtype=int) - 1
    features[np.arange(len(table)), first_indices] = 1.0
    features[np.arange(len(table)), 38 + second_indices] = 1.0
    features[:, 76] = table["first_line_index_norm"].to_numpy(dtype=np.float32)
    features[:, 77] = table["second_line_index_norm"].to_numpy(dtype=np.float32)
    features[:, 78] = table["line_order_delta_norm"].to_numpy(dtype=np.float32)
    return features


def _node_feature_names() -> list[str]:
    return [
        "gamma_i 负荷随机因子",
        "P_D_i_new 归一化新负荷",
        "incident_loading_sum 相邻线路初始负载率之和",
        "incident_loading_max 相邻线路初始最大负载率",
        "first_outage_endpoint 第一条故障线路端点标记",
        "second_outage_endpoint 第二条故障线路端点标记",
    ]


def _path_feature_names() -> list[str]:
    return [f"first_is_L{i:02d}" for i in range(1, 39)] + [f"second_is_L{i:02d}" for i in range(1, 39)] + [
        "first_line_index_norm",
        "second_line_index_norm",
        "line_order_delta_norm",
    ]


def _collect_columns(table: pd.DataFrame, prefix: str, suffix: str) -> np.ndarray:
    columns = [f"{prefix}{i:02d}{suffix}" for i in range(1, 25)]
    return table[columns].to_numpy(dtype=np.float32)


def _bus_matrix(table: pd.DataFrame, prefix: str, suffix: str) -> np.ndarray:
    return _collect_columns(table, prefix, suffix)


def _incident_loading_arrays(table: pd.DataFrame, branch_table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    row_count = len(table)
    bus_count = 24
    incident_sum = np.zeros((row_count, bus_count), dtype=np.float32)
    incident_max = np.zeros((row_count, bus_count), dtype=np.float32)
    for _, branch in branch_table.iterrows():
        line_label = branch["line_label"]
        loading = table[f"initial_loading_{line_label}"].to_numpy(dtype=np.float32)
        from_idx = int(branch["from_bus"]) - 1
        to_idx = int(branch["to_bus"]) - 1
        incident_sum[:, from_idx] += loading
        incident_sum[:, to_idx] += loading
        incident_max[:, from_idx] = np.maximum(incident_max[:, from_idx], loading)
        incident_max[:, to_idx] = np.maximum(incident_max[:, to_idx], loading)
    return incident_sum, incident_max


def _mark_outage_endpoint_features(node_features: np.ndarray, table: pd.DataFrame, branch_table: pd.DataFrame) -> None:
    branch_by_label = branch_table.set_index("line_label")
    for row_pos, row in enumerate(table.itertuples(index=False)):
        first = branch_by_label.loc[getattr(row, "first_line")]
        second = branch_by_label.loc[getattr(row, "second_line")]
        for bus in (int(first["from_bus"]), int(first["to_bus"])):
            node_features[row_pos, bus - 1, 4] = 1.0
        for bus in (int(second["from_bus"]), int(second["to_bus"])):
            node_features[row_pos, bus - 1, 5] = 1.0


def _normalize(values: np.ndarray, stats: dict) -> np.ndarray:
    return (values - float(stats["mean"])) / float(stats["std"])


def _split_by_scenario(clean: pd.DataFrame, config: GcnTrainConfig) -> tuple[pd.Index, pd.Index]:
    rng = np.random.default_rng(config.random_seed)
    scenario_ids = np.array(sorted(clean["scenario_id"].unique()))
    if len(scenario_ids) >= 2:
        rng.shuffle(scenario_ids)
        validation_count = max(1, int(round(len(scenario_ids) * config.validation_fraction)))
        validation_scenarios = set(scenario_ids[:validation_count])
        validation_mask = clean["scenario_id"].isin(validation_scenarios)
    else:
        validation_mask = pd.Series(False, index=clean.index)
        validation_size = max(1, int(round(len(clean) * config.validation_fraction)))
        validation_index = rng.choice(clean.index.to_numpy(), size=validation_size, replace=False)
        validation_mask.loc[validation_index] = True
    return clean.index[~validation_mask], clean.index[validation_mask]


def _predict_probability(
    model: nn.Module,
    node_features: np.ndarray,
    path_features: np.ndarray,
    normalized_adjacency: torch.Tensor,
) -> np.ndarray:
    model.eval()
    probabilities: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(node_features), 1024):
            end = start + 1024
            logits = model(
                torch.tensor(node_features[start:end], dtype=torch.float32),
                torch.tensor(path_features[start:end], dtype=torch.float32),
                normalized_adjacency,
            )
            probabilities.append(torch.sigmoid(logits).numpy())
    return np.concatenate(probabilities) if probabilities else np.array([], dtype=np.float32)


def _find_best_threshold(y: np.ndarray, probabilities: np.ndarray) -> float:
    best_threshold = 0.5
    best_f1 = -1.0
    for threshold in np.linspace(0.05, 0.95, 91):
        metrics = _classification_metrics(y, probabilities, float(threshold))
        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_threshold = float(threshold)
    return best_threshold


def _evaluate_model(
    model: nn.Module,
    node_features: np.ndarray,
    path_features: np.ndarray,
    y: np.ndarray,
    normalized_adjacency: torch.Tensor,
    threshold: float,
) -> dict:
    probabilities = _predict_probability(model, node_features, path_features, normalized_adjacency)
    return _classification_metrics(y, probabilities, threshold)


def _classification_metrics(y: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    prediction = (probabilities >= threshold).astype(int)
    truth = y.astype(int)
    tp = int(((prediction == 1) & (truth == 1)).sum())
    tn = int(((prediction == 0) & (truth == 0)).sum())
    fp = int(((prediction == 1) & (truth == 0)).sum())
    fn = int(((prediction == 0) & (truth == 1)).sum())
    accuracy = (tp + tn) / max(len(truth), 1)
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


def _make_prediction_table(validation_table: pd.DataFrame, probabilities: np.ndarray, threshold: float) -> pd.DataFrame:
    columns = [
        "scenario_id",
        "seed",
        "path",
        "first_line",
        "second_line",
        "critical_label",
        "total_load_shed_mw",
        "final_outage_count",
    ]
    table = validation_table[columns].copy()
    table["critical_probability"] = probabilities
    table["decision_threshold"] = threshold
    table["predicted_critical_label"] = (probabilities >= threshold).astype(int)
    return table.sort_values("critical_probability", ascending=False).reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="训练 RTS-79 GCN 关键路径识别模型。")
    parser.add_argument("--dataset-csv", required=True, help="训练集 CSV 文件路径。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "gcn_training"), help="输出目录。")
    parser.add_argument("--epochs", type=int, default=200, help="训练轮数。")
    parser.add_argument("--batch-size", type=int, default=256, help="批大小。")
    parser.add_argument("--hidden-dim", type=int, default=64, help="隐藏层维度。")
    parser.add_argument("--learning-rate", type=float, default=1e-3, help="学习率。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = GcnTrainConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        hidden_dim=args.hidden_dim,
        learning_rate=args.learning_rate,
    )
    metrics = train_gcn_model(args.dataset_csv, args.output_dir, config)
    print("[结果] train 是“训练集”，validation 是“验证集”。")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
