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

from pypower.idx_brch import BR_STATUS, F_BUS, PF, RATE_A, T_BUS
from pypower.idx_bus import BUS_I, PD

from rts79_cascade import (
    Rts79InitialConfig,
    line_label_to_index_1based,
    load_rts79_case,
    run_sequential_initial_outages_dcpf,
)


@dataclass(frozen=True)
class PaperGcnDatasetConfig:
    """论文式 GCN 数据集配置；dataset 是“数据集”，config 是“配置”。"""

    load_scale: float = 1.1
    load_random_low: float = 0.9
    load_random_high: float = 1.1
    relay_threshold_beta: float = 1.2
    security_limit: float = 1.0


@dataclass(frozen=True)
class PaperGcnTrainConfig:
    """论文式 GCN 训练配置；epoch 是“一轮完整训练”。"""

    epochs: int = 20
    batch_size: int = 32
    learning_rate: float = 0.005
    k_gcn: int = 3
    first_layer_channels: int = 16
    second_layer_channels: int = 4
    positive_weight: float = 20.0
    validation_fraction: float = 0.2
    random_seed: int = 20260512


class PaperGraphConvolution(nn.Module):
    """论文公式 (8) 的图卷积层；graph convolution 是“图卷积”。"""

    def __init__(self, input_channels: int, output_channels: int, k_gcn: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.empty(input_channels, output_channels, k_gcn + 1))
        self.bias = nn.Parameter(torch.zeros(output_channels))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, x: torch.Tensor, adjacency_powers: torch.Tensor) -> torch.Tensor:
        # x: batch x L x C; adjacency_powers: (K+1) x L x L.
        filtered = torch.einsum("kij,bjc->bikc", adjacency_powers, x)
        return torch.einsum("bikc,cfk->bif", filtered, self.weight) + self.bias


class PaperStyleRts79Gcn(nn.Module):
    """论文式 RTS-79 GCN；branch 是“支路”，node 是“图节点”。"""

    def __init__(self, input_channels: int, config: PaperGcnTrainConfig) -> None:
        super().__init__()
        self.graph_1 = PaperGraphConvolution(input_channels, config.first_layer_channels, config.k_gcn)
        self.graph_2 = PaperGraphConvolution(
            config.first_layer_channels,
            config.second_layer_channels,
            config.k_gcn,
        )
        self.classifier = nn.Linear(config.second_layer_channels, 2)

    def forward(self, x: torch.Tensor, adjacency_powers: torch.Tensor) -> torch.Tensor:
        h = torch.relu(self.graph_1(x, adjacency_powers))
        h = torch.relu(self.graph_2(h, adjacency_powers))
        return self.classifier(h)


def build_paper_gcn_dataset(
    path_dataset_csv: str | Path,
    output_dir: str | Path,
    config: PaperGcnDatasetConfig,
) -> dict[str, np.ndarray | list[str]]:
    """构造论文式 X_GCN 和 y_GCN；X_GCN 是“当前状态”，y_GCN 是“支路标签向量”。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path_table = pd.read_csv(path_dataset_csv)
    clean = path_table.loc[path_table["error"].fillna("") == ""].copy()
    samples: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    sample_records: list[dict] = []

    grouped = clean.groupby(["scenario_id", "seed", "first_line"], sort=True)
    for sample_id, ((scenario_id, seed, first_line), group) in enumerate(grouped, start=1):
        print(f"[论文GCN数据集] 样本 {sample_id}: scenario={scenario_id}, first_line={first_line}")
        initial_config = Rts79InitialConfig(
            random_seed=int(seed),
            load_scale=config.load_scale,
            load_random_low=config.load_random_low,
            load_random_high=config.load_random_high,
        )
        state = run_sequential_initial_outages_dcpf(
            [first_line],
            config=initial_config,
            relay_threshold_beta=config.relay_threshold_beta,
            security_limit=config.security_limit,
        )
        x_gcn = _make_x_gcn(state.case, config.relay_threshold_beta)
        y_gcn, mask = _make_y_gcn_and_mask(group, first_line)
        samples.append(x_gcn)
        labels.append(y_gcn)
        masks.append(mask)
        sample_records.append(
            {
                "sample_id": sample_id,
                "scenario_id": int(scenario_id),
                "seed": int(seed),
                "first_line": first_line,
                "num_positive_labels": int(y_gcn[mask].sum()),
                "num_candidate_labels": int(mask.sum()),
                "current_outage_labels": ",".join(state.final_outage_labels),
            }
        )

    x = np.stack(samples).astype(np.float32)
    y = np.stack(labels).astype(np.int64)
    loss_mask = np.stack(masks).astype(bool)
    sample_table = pd.DataFrame(sample_records)
    normalizer = _fit_x_normalizer(x)
    x_normalized = _normalize_x(x, normalizer)
    np.savez(
        out / "rts79_paper_gcn_dataset.npz",
        x_gcn=x_normalized,
        y_gcn=y,
        loss_mask=loss_mask,
        scenario_id=sample_table["scenario_id"].to_numpy(dtype=np.int64),
        seed=sample_table["seed"].to_numpy(dtype=np.int64),
        first_line=sample_table["first_line"].to_numpy(dtype=str),
    )
    sample_table.to_csv(out / "rts79_paper_gcn_sample_summary.csv", index=False, encoding="utf-8-sig")
    (out / "rts79_paper_gcn_feature_normalizer.json").write_text(
        json.dumps(normalizer, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "rts79_paper_gcn_dataset_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "x_gcn": x_normalized,
        "y_gcn": y,
        "loss_mask": loss_mask,
        "scenario_id": sample_table["scenario_id"].to_numpy(dtype=np.int64),
        "first_line": sample_table["first_line"].tolist(),
    }


def train_paper_gcn_model(
    dataset: dict[str, np.ndarray | list[str]],
    output_dir: str | Path,
    config: PaperGcnTrainConfig,
) -> dict:
    """训练论文式 GCN；output 是长度为 38 的支路脆弱性向量。"""

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    x = dataset["x_gcn"]
    y = dataset["y_gcn"]
    loss_mask = dataset["loss_mask"]
    scenario_id = dataset["scenario_id"]
    assert isinstance(x, np.ndarray)
    assert isinstance(y, np.ndarray)
    assert isinstance(loss_mask, np.ndarray)
    assert isinstance(scenario_id, np.ndarray)

    train_index, validation_index = _split_samples_by_scenario(scenario_id, config)
    x_train, y_train, mask_train = x[train_index], y[train_index], loss_mask[train_index]
    x_validation, y_validation, mask_validation = x[validation_index], y[validation_index], loss_mask[validation_index]

    adjacency = _build_branch_graph_adjacency(load_rts79_case())
    adjacency_powers = torch.tensor(_build_adjacency_powers(adjacency, config.k_gcn), dtype=torch.float32)
    torch.manual_seed(config.random_seed)
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=config)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    class_weight = torch.tensor([1.0, config.positive_weight], dtype=torch.float32)
    loss_function = nn.CrossEntropyLoss(weight=class_weight, reduction="none")
    loader = DataLoader(
        TensorDataset(
            torch.tensor(x_train, dtype=torch.float32),
            torch.tensor(y_train, dtype=torch.long),
            torch.tensor(mask_train, dtype=torch.bool),
        ),
        batch_size=config.batch_size,
        shuffle=True,
    )

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        total_count = 0
        for xb, yb, mb in loader:
            optimizer.zero_grad()
            logits = model(xb, adjacency_powers)
            loss_matrix = loss_function(logits.reshape(-1, 2), yb.reshape(-1)).reshape_as(yb)
            loss = loss_matrix[mb].mean()
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach()) * int(mb.sum())
            total_count += int(mb.sum())
        metrics = _evaluate_paper_gcn(model, x_validation, y_validation, mask_validation, adjacency_powers)
        print(
            "[论文GCN训练] "
            f"epoch={epoch}, "
            f"loss={total_loss / max(total_count, 1):.6f}, "
            f"validation_hit_rate={metrics['hit_rate']:.4f}, "
            f"validation_cover_rate={metrics['cover_rate']:.4f}"
        )

    train_metrics = _evaluate_paper_gcn(model, x_train, y_train, mask_train, adjacency_powers)
    validation_metrics = _evaluate_paper_gcn(model, x_validation, y_validation, mask_validation, adjacency_powers)
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "train_config": asdict(config),
            "feature_names": _x_gcn_feature_names(),
            "adjacency_powers": adjacency_powers.numpy(),
            "class_order": ["normal 不切负荷", "shed 切负荷"],
        },
        out / "rts79_paper_gcn_model.pt",
    )
    pd.DataFrame(
        [
            {"split": "train", **train_metrics},
            {"split": "validation", **validation_metrics},
        ]
    ).to_csv(out / "rts79_paper_gcn_metrics.csv", index=False, encoding="utf-8-sig")
    _make_validation_prediction_table(model, dataset, validation_index, adjacency_powers).to_csv(
        out / "rts79_paper_gcn_validation_predictions.csv",
        index=False,
        encoding="utf-8-sig",
    )
    (out / "rts79_paper_gcn_train_config.json").write_text(
        json.dumps(asdict(config), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[论文GCN训练] 已保存模型: {out / 'rts79_paper_gcn_model.pt'}")
    return {"train": train_metrics, "validation": validation_metrics}


def _make_x_gcn(case: dict, relay_threshold_beta: float) -> np.ndarray:
    branch = case["branch"]
    bus = case["bus"]
    bus_load_by_number = {int(row[BUS_I]): float(row[PD]) for row in bus}
    features = np.zeros((branch.shape[0], 4), dtype=np.float32)
    for idx, row in enumerate(branch):
        status = int(row[BR_STATUS])
        f_bus = int(row[F_BUS])
        t_bus = int(row[T_BUS])
        rate_a = float(row[RATE_A])
        flow = 0.0 if status == 0 or len(row) <= PF else abs(float(row[PF]))
        features[idx, 0] = 1.0 if status == 0 else 0.0
        features[idx, 1] = flow / max(relay_threshold_beta * rate_a, 1e-8)
        features[idx, 2] = flow
        features[idx, 3] = max(bus_load_by_number[f_bus], bus_load_by_number[t_bus])
    return features


def _make_x_gcn_physics(case: dict, beta: float, security_limit: float = 1.0) -> np.ndarray:
    branch = case["branch"]
    bus = case["bus"]
    bus_load_by_number = {int(row[BUS_I]): float(row[PD]) for row in bus}
    features = np.zeros((branch.shape[0], len(_x_gcn_physics_feature_names())), dtype=np.float32)
    for idx, row in enumerate(branch):
        status = int(row[BR_STATUS])
        f_bus = int(row[F_BUS])
        t_bus = int(row[T_BUS])
        rate_a = max(float(row[RATE_A]), 1e-8)
        flow = 0.0 if status == 0 or len(row) <= PF else abs(float(row[PF]))
        loading_ratio = flow / rate_a
        is_online = 1.0 if status == 1 else 0.0
        features[idx, 0] = 1.0 if status == 0 else 0.0
        features[idx, 1] = flow / max(beta * rate_a, 1e-8)
        features[idx, 2] = flow
        features[idx, 3] = max(bus_load_by_number.get(f_bus, 0.0), bus_load_by_number.get(t_bus, 0.0))
        features[idx, 4] = loading_ratio
        features[idx, 5] = security_limit - loading_ratio
        features[idx, 6] = beta - loading_ratio
        features[idx, 7] = is_online
        features[idx, 8] = is_online
    if not np.isfinite(features).all():
        raise ValueError("_make_x_gcn_physics produced NaN/Inf features.")
    for binary_idx in (0, 7, 8):
        if not np.isin(features[:, binary_idx], [0.0, 1.0]).all():
            raise ValueError(f"Physics binary feature {binary_idx} must be 0/1.")
    return features


def _make_y_gcn_and_mask(group: pd.DataFrame, first_line: str) -> tuple[np.ndarray, np.ndarray]:
    y = np.zeros(38, dtype=np.int64)
    mask = np.ones(38, dtype=bool)
    mask[line_label_to_index_1based(first_line) - 1] = False
    for _, row in group.iterrows():
        idx = line_label_to_index_1based(str(row["second_line"])) - 1
        y[idx] = int(bool(row["critical"]))
    return y, mask


def _fit_x_normalizer(x: np.ndarray) -> dict:
    normalizer: dict[str, dict[str, float]] = {}
    for idx, name in enumerate(_feature_names_for_x(x)):
        values = x[:, :, idx]
        if name in {"branch_status_offline", "is_online", "is_candidate"} or idx == 0:
            normalizer[name] = {"mean": 0.0, "std": 1.0}
        else:
            normalizer[name] = {"mean": float(values.mean()), "std": float(max(values.std(), 1e-8))}
    return normalizer


def _normalize_x(x: np.ndarray, normalizer: dict) -> np.ndarray:
    normalized = x.copy()
    for idx, name in enumerate(_feature_names_for_x(x)):
        normalized[:, :, idx] = (normalized[:, :, idx] - normalizer[name]["mean"]) / normalizer[name]["std"]
    return normalized


def _x_gcn_feature_names() -> list[str]:
    return [
        "x_t 拓扑状态，支路断开为1，在线为0",
        "x_p 保护继电器指标，等于 |L_k|/(beta L_k^max)",
        "x_b 支路潮流绝对值",
        "x_l 支路两端母线较大负荷",
    ]


def _x_gcn_physics_feature_names() -> list[str]:
    return [
        "branch_status_offline",
        "relay_loading_ratio",
        "abs_flow",
        "max_terminal_load",
        "loading_ratio",
        "security_margin",
        "relay_margin",
        "is_online",
        "is_candidate",
    ]


def _feature_names_for_x(x: np.ndarray) -> list[str]:
    if x.shape[2] == 4:
        return _x_gcn_feature_names()
    if x.shape[2] == len(_x_gcn_physics_feature_names()):
        return _x_gcn_physics_feature_names()
    return [f"feature_{idx}" for idx in range(x.shape[2])]


def _build_branch_graph_adjacency(case: dict) -> np.ndarray:
    branch = case["branch"]
    line_count = branch.shape[0]
    adjacency = np.zeros((line_count, line_count), dtype=np.float32)
    endpoints = [set([int(row[F_BUS]), int(row[T_BUS])]) for row in branch]
    for i in range(line_count):
        for j in range(line_count):
            if i == j:
                continue
            if endpoints[i] & endpoints[j]:
                adjacency[i, j] = 1.0
    degree = adjacency.sum(axis=1)
    inv_sqrt_degree = np.diag(1.0 / np.sqrt(np.maximum(degree, 1e-8)))
    return inv_sqrt_degree @ adjacency @ inv_sqrt_degree


def _build_adjacency_powers(adjacency: np.ndarray, k_gcn: int) -> np.ndarray:
    powers = [np.eye(adjacency.shape[0], dtype=np.float32)]
    for _ in range(1, k_gcn + 1):
        powers.append(powers[-1] @ adjacency)
    return np.stack(powers).astype(np.float32)


def _split_samples_by_scenario(scenario_id: np.ndarray, config: PaperGcnTrainConfig) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(config.random_seed)
    scenarios = np.array(sorted(set(int(value) for value in scenario_id)))
    if len(scenarios) >= 2:
        rng.shuffle(scenarios)
        validation_count = max(1, int(round(len(scenarios) * config.validation_fraction)))
        validation_scenarios = set(scenarios[:validation_count])
        validation_mask = np.array([int(value) in validation_scenarios for value in scenario_id])
    else:
        validation_mask = np.zeros(len(scenario_id), dtype=bool)
        validation_size = max(1, int(round(len(scenario_id) * config.validation_fraction)))
        validation_mask[rng.choice(np.arange(len(scenario_id)), size=validation_size, replace=False)] = True
    return np.where(~validation_mask)[0], np.where(validation_mask)[0]


def _predict_shed_probability(model: nn.Module, x: np.ndarray, adjacency_powers: torch.Tensor) -> np.ndarray:
    model.eval()
    probabilities: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(x), 128):
            batch = torch.tensor(x[start : start + 128], dtype=torch.float32)
            logits = model(batch, adjacency_powers)
            probabilities.append(torch.softmax(logits, dim=2)[:, :, 1].numpy())
    return np.concatenate(probabilities) if probabilities else np.zeros((0, 38), dtype=np.float32)


def _evaluate_paper_gcn(
    model: nn.Module,
    x: np.ndarray,
    y: np.ndarray,
    mask: np.ndarray,
    adjacency_powers: torch.Tensor,
) -> dict:
    probability = _predict_shed_probability(model, x, adjacency_powers)
    prediction = (probability >= 0.5).astype(int)
    truth = y.astype(int)
    active = mask.astype(bool)
    tp = int(((prediction == 1) & (truth == 1) & active).sum())
    tn = int(((prediction == 0) & (truth == 0) & active).sum())
    fp = int(((prediction == 1) & (truth == 0) & active).sum())
    fn = int(((prediction == 0) & (truth == 1) & active).sum())
    total = max(int(active.sum()), 1)
    total_accuracy = (tp + tn) / total
    hit_rate = tp / max(tp + fp, 1)
    cover_rate = tp / max(tp + fn, 1)
    f1 = 2 * hit_rate * cover_rate / max(hit_rate + cover_rate, 1e-12)
    return {
        "total_accuracy": float(total_accuracy),
        "hit_rate": float(hit_rate),
        "cover_rate": float(cover_rate),
        "f1": float(f1),
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def _make_validation_prediction_table(
    model: nn.Module,
    dataset: dict,
    validation_index: np.ndarray,
    adjacency_powers: torch.Tensor,
) -> pd.DataFrame:
    x = dataset["x_gcn"][validation_index]
    y = dataset["y_gcn"][validation_index]
    mask = dataset["loss_mask"][validation_index]
    scenario_id = dataset["scenario_id"][validation_index]
    first_line = np.array(dataset["first_line"], dtype=object)[validation_index]
    probability = _predict_shed_probability(model, x, adjacency_powers)
    records: list[dict] = []
    for sample_pos in range(len(validation_index)):
        for line_idx in range(38):
            if not mask[sample_pos, line_idx]:
                continue
            records.append(
                {
                    "scenario_id": int(scenario_id[sample_pos]),
                    "first_line": str(first_line[sample_pos]),
                    "candidate_line": f"L{line_idx + 1:02d}",
                    "critical_label": int(y[sample_pos, line_idx]),
                    "shed_probability": float(probability[sample_pos, line_idx]),
                    "predicted_critical_label": int(probability[sample_pos, line_idx] >= 0.5),
                }
            )
    return pd.DataFrame(records).sort_values("shed_probability", ascending=False).reset_index(drop=True)


def load_paper_gcn_dataset(npz_path: str | Path) -> dict:
    data = np.load(npz_path, allow_pickle=True)
    return {
        "x_gcn": data["x_gcn"],
        "y_gcn": data["y_gcn"],
        "loss_mask": data["loss_mask"],
        "scenario_id": data["scenario_id"],
        "first_line": data["first_line"].tolist(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成并训练论文式 RTS-79 GCN。")
    parser.add_argument("--path-dataset-csv", help="已有路径训练集 CSV，用于生成论文式 GCN 数据集。")
    parser.add_argument("--paper-dataset-npz", help="已有论文式 GCN 数据集 NPZ；如果提供则跳过数据集生成。")
    parser.add_argument("--output-dir", default=str(Path("outputs") / "paper_gcn_training"), help="输出目录。")
    parser.add_argument("--beta", type=float, default=1.2, help="保护继电器动作阈值 beta。")
    parser.add_argument("--security-limit", type=float, default=1.0, help="再调度安全约束阈值。")
    parser.add_argument("--epochs", type=int, default=20, help="训练轮数。")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out = Path(args.output_dir)
    dataset_config = PaperGcnDatasetConfig(
        relay_threshold_beta=args.beta,
        security_limit=args.security_limit,
    )
    train_config = PaperGcnTrainConfig(epochs=args.epochs)
    if args.paper_dataset_npz:
        dataset = load_paper_gcn_dataset(args.paper_dataset_npz)
        print(f"[论文GCN数据集] 已读取: {args.paper_dataset_npz}")
    else:
        if not args.path_dataset_csv:
            raise ValueError("必须提供 --path-dataset-csv 或 --paper-dataset-npz")
        dataset = build_paper_gcn_dataset(args.path_dataset_csv, out, dataset_config)
    metrics = train_paper_gcn_model(dataset, out, train_config)
    print("[结果] hit_rate 是“命中率”，cover_rate 是“覆盖率”。")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
