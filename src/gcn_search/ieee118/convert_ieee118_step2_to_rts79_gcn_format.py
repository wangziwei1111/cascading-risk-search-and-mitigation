from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

LEAKAGE_COLUMNS = {
    "critical",
    "critical_mechanism",
    "has_overload_cascade",
    "relay_cascade",
    "total_load_shed_mw",
    "num_relay_trips",
    "max_event_loading_ratio",
    "max_pre_redispatch_loading_ratio",
    "label_critical",
    "label_relay_cascade",
    "label_load_shed_positive",
}

PIO_PHYSICS_FEATURE_NAMES = [
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

REQUIRED_COLUMNS = {
    "scenario_id",
    "seed",
    "path",
    "first_line",
    "second_line",
    "label_critical",
    "label_relay_cascade",
    "edge_features_json",
    "node_features_json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert IEEE118 Step2-State CSV to the original RTS-79 GCN NPZ shape.")
    parser.add_argument(
        "--step2-csv",
        type=Path,
        default=ROOT
        / "results"
        / "gcn_search"
        / "ieee118_flow_scaled_800_step2_state"
        / "ieee118_step2_state_samples.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_original_rts79_gcn_eval",
    )
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--max-first-lines", type=int, default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    return parser.parse_args()


def require_step2_csv(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing IEEE118 Step2-State CSV: {path}. Generate or place the local large CSV first; "
            "this converter will not regenerate the 34,410-row graph dataset automatically."
        )


def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return False
    return str(value).strip().lower() in {"true", "1", "yes"}


def load_step2_rows(path: Path, max_first_lines: int | None, max_samples: int | None) -> pd.DataFrame:
    require_step2_csv(path)
    table = pd.read_csv(path, nrows=max_samples)
    missing = sorted(REQUIRED_COLUMNS - set(table.columns))
    if missing:
        raise ValueError(f"IEEE118 Step2-State CSV missing required columns: {missing}")
    if max_first_lines is not None:
        first_lines = list(dict.fromkeys(table["first_line"].astype(str).tolist()))[:max_first_lines]
        table = table.loc[table["first_line"].astype(str).isin(first_lines)].copy()
    return table.reset_index(drop=True)


def build_x_from_json(edge_json: str, node_json: str, *, beta: float, security_limit: float) -> tuple[np.ndarray, list[str], np.ndarray, np.ndarray]:
    edges = json.loads(edge_json)
    nodes = json.loads(node_json)
    load_by_bus = {int(node["bus_id"]): float(node.get("Pd", 0.0)) for node in nodes}
    x = np.zeros((len(edges), len(PIO_PHYSICS_FEATURE_NAMES)), dtype=np.float32)
    line_labels: list[str] = []
    from_bus = np.zeros(len(edges), dtype=np.int64)
    to_bus = np.zeros(len(edges), dtype=np.int64)
    for idx, edge in enumerate(edges):
        label = str(edge["line_label"])
        f_bus = int(edge["from_bus"])
        t_bus = int(edge["to_bus"])
        rate_a = max(float(edge.get("rate_a", 0.0)), 1e-8)
        abs_flow = abs(float(edge.get("abs_pf_after_first_outage", 0.0)))
        loading_ratio = float(edge.get("loading_ratio_after_first_outage", abs_flow / rate_a))
        offline = coerce_bool(edge.get("is_first_outage", False))
        is_online = 0.0 if offline else 1.0
        line_labels.append(label)
        from_bus[idx] = f_bus
        to_bus[idx] = t_bus
        x[idx, 0] = 1.0 if offline else 0.0
        x[idx, 1] = abs_flow / max(beta * rate_a, 1e-8)
        x[idx, 2] = abs_flow
        x[idx, 3] = max(load_by_bus.get(f_bus, 0.0), load_by_bus.get(t_bus, 0.0))
        x[idx, 4] = loading_ratio
        x[idx, 5] = float(security_limit) - loading_ratio
        x[idx, 6] = float(beta) - loading_ratio
        x[idx, 7] = is_online
        x[idx, 8] = is_online
    if not np.isfinite(x).all():
        raise ValueError("Converted IEEE118 GCN features contain NaN or Inf.")
    return x, line_labels, from_bus, to_bus


def fit_normalizer(x_raw: np.ndarray) -> dict[str, dict[str, float]]:
    normalizer: dict[str, dict[str, float]] = {}
    for idx, name in enumerate(PIO_PHYSICS_FEATURE_NAMES):
        values = x_raw[:, :, idx]
        if name in {"branch_status_offline", "is_online", "is_candidate"}:
            normalizer[name] = {"mean": 0.0, "std": 1.0}
        else:
            normalizer[name] = {"mean": float(values.mean()), "std": float(max(values.std(), 1e-8))}
    return normalizer


def normalize_x(x_raw: np.ndarray, normalizer: dict[str, dict[str, float]]) -> np.ndarray:
    x = x_raw.copy()
    for idx, name in enumerate(PIO_PHYSICS_FEATURE_NAMES):
        x[:, :, idx] = (x[:, :, idx] - normalizer[name]["mean"]) / normalizer[name]["std"]
    return x


def convert_step2_to_rts79_gcn_format(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table = load_step2_rows(args.step2_csv, args.max_first_lines, args.max_samples)
    grouped = table.groupby(["scenario_id", "seed", "first_line"], sort=True)
    x_states: list[np.ndarray] = []
    y_critical: list[np.ndarray] = []
    y_relay: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    sample_rows: list[dict[str, Any]] = []
    path_rows: list[dict[str, Any]] = []
    line_labels: list[str] | None = None
    from_bus: np.ndarray | None = None
    to_bus: np.ndarray | None = None

    for sample_idx, ((scenario_id, seed, first_line), group) in enumerate(grouped):
        first = group.iloc[0]
        x_raw, labels, branch_from_bus, branch_to_bus = build_x_from_json(
            str(first["edge_features_json"]),
            str(first["node_features_json"]),
            beta=float(args.beta),
            security_limit=float(args.security_limit),
        )
        if line_labels is None:
            line_labels = labels
            from_bus = branch_from_bus
            to_bus = branch_to_bus
        elif labels != line_labels:
            raise ValueError(f"Line label order changed for first_line={first_line}.")

        label_to_idx = {label: idx for idx, label in enumerate(labels)}
        y_c = np.zeros(len(labels), dtype=np.int64)
        y_r = np.zeros(len(labels), dtype=np.int64)
        mask = np.zeros(len(labels), dtype=bool)
        for _, row in group.iterrows():
            second_line = str(row["second_line"])
            if second_line not in label_to_idx:
                raise ValueError(f"Unknown second_line label {second_line}")
            line_idx = label_to_idx[second_line]
            y_c[line_idx] = int(coerce_bool(row["label_critical"]))
            y_r[line_idx] = int(coerce_bool(row["label_relay_cascade"]))
            mask[line_idx] = second_line != str(first_line)
            path_rows.append(
                {
                    "sample_index": sample_idx,
                    "scenario_id": int(scenario_id),
                    "seed": int(seed),
                    "path": str(row["path"]),
                    "first_line": str(first_line),
                    "second_line": second_line,
                    "line_index": int(line_idx),
                    "label_critical": int(y_c[line_idx]),
                    "label_relay_cascade": int(y_r[line_idx]),
                }
            )
        x_states.append(x_raw)
        y_critical.append(y_c)
        y_relay.append(y_r)
        masks.append(mask)
        sample_rows.append(
            {
                "sample_index": sample_idx,
                "scenario_id": int(scenario_id),
                "seed": int(seed),
                "first_line": str(first_line),
                "num_candidate_labels": int(mask.sum()),
                "num_critical_labels": int(y_c[mask].sum()),
                "num_relay_cascade_labels": int(y_r[mask].sum()),
            }
        )

    if not x_states or line_labels is None or from_bus is None or to_bus is None:
        raise ValueError("No IEEE118 Step2-State rows were available for conversion.")

    x_raw_array = np.stack(x_states).astype(np.float32)
    normalizer = fit_normalizer(x_raw_array)
    x_array = normalize_x(x_raw_array, normalizer).astype(np.float32)
    y_critical_array = np.stack(y_critical).astype(np.int64)
    y_relay_array = np.stack(y_relay).astype(np.int64)
    mask_array = np.stack(masks).astype(bool)
    sample_table = pd.DataFrame(sample_rows)
    path_table = pd.DataFrame(path_rows)

    npz_path = args.output_dir / "ieee118_rts79_gcn_dataset.npz"
    np.savez(
        npz_path,
        x_gcn=x_array,
        physics_raw_features=x_raw_array,
        y_gcn=y_critical_array,
        y_critical=y_critical_array,
        y_relay_cascade=y_relay_array,
        y_reachable=y_critical_array,
        loss_mask=mask_array,
        scenario_id=sample_table["scenario_id"].to_numpy(dtype=np.int64),
        seed=sample_table["seed"].to_numpy(dtype=np.int64),
        first_line=sample_table["first_line"].to_numpy(dtype=str),
        line_labels=np.asarray(line_labels, dtype=str),
        branch_from_bus=from_bus,
        branch_to_bus=to_bus,
        feature_names=np.asarray(PIO_PHYSICS_FEATURE_NAMES, dtype=str),
    )
    sample_table.to_csv(args.output_dir / "ieee118_rts79_gcn_sample_summary.csv", index=False, encoding="utf-8-sig")
    path_table.to_csv(args.output_dir / "ieee118_rts79_gcn_path_index.csv", index=False, encoding="utf-8-sig")
    (args.output_dir / "ieee118_rts79_gcn_feature_normalizer.json").write_text(
        json.dumps(normalizer, indent=2),
        encoding="utf-8",
    )
    metadata = {
        "dataset_npz": str(npz_path),
        "source_step2_csv": str(args.step2_csv),
        "num_state_samples": int(x_array.shape[0]),
        "num_line_labels": int(x_array.shape[1]),
        "num_path_samples": int(len(path_table)),
        "feature_names": PIO_PHYSICS_FEATURE_NAMES,
        "excluded_leakage_columns": sorted(LEAKAGE_COLUMNS),
        "model_contract": "Prepared for the original RTS-79 PaperStyleRts79Gcn/Pio-GCN input tensor shape: samples x branches x features.",
    }
    (args.output_dir / "ieee118_rts79_gcn_dataset_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return metadata


def main() -> None:
    args = parse_args()
    metadata = convert_step2_to_rts79_gcn_format(args)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
