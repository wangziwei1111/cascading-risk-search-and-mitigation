from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(IEEE118_DIR))
sys.path.insert(0, str(LEGACY_DIR))

from build_ieee118_base_state_for_rts79_gcn import (
    build_paper_x_from_case,
    load_normalizer,
)
from case_adapter import build_case_adapter
from convert_ieee118_step2_to_rts79_gcn_format import (
    PAPER_FEATURE_NAMES,
    normalize_x,
)
from generate_ieee118_ordered_n2_fulltruth import (
    apply_ieee118_load_scenario,
    apply_thermal_limit_mode,
)
from run_ieee118_active_label_replay import (
    DEFAULT_DATASET,
    _fit_one_model,
)
from train_ieee118_paper_aligned_gcn import predict_probability, split_metrics
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
)


DEFAULT_NORMALIZER = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_feature_normalizer.json"
)
DEFAULT_FIRST_STEP = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_flow_scaled_800_fulltruth_earlystop_seed20260708"
    / "ieee118_first_step_summary.csv"
)
DEFAULT_OUTPUT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "n1_gate_original_rts79_gcn"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train an IEEE118 N-1 gate head with the unchanged RTS-79 "
            "PaperStyleRts79Gcn, using S0 labels only."
        )
    )
    parser.add_argument("--dataset-npz", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--normalizer-json", type=Path, default=DEFAULT_NORMALIZER)
    parser.add_argument(
        "--deployment-first-step-summary-csv",
        type=Path,
        default=DEFAULT_FIRST_STEP,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=0.005)
    parser.add_argument(
        "--positive-weights",
        type=float,
        nargs="+",
        default=[5.0, 10.0, 20.0, 50.0],
    )
    parser.add_argument(
        "--training-seeds",
        type=int,
        nargs="+",
        default=[20260730, 20260731, 20260732],
    )
    parser.add_argument("--max-train-s0-states", type=int, default=None)
    parser.add_argument("--k-gcn", type=int, default=6)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--deployment-seed", type=int, default=20260708)
    parser.add_argument("--deployment-load-scale", type=float, default=1.0)
    parser.add_argument(
        "--limit-mode",
        choices=["original_rate_a", "flow_scaled"],
        default="flow_scaled",
    )
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    return parser.parse_args(argv)


def _average_precision(truth: np.ndarray, score: np.ndarray) -> float:
    truth = np.asarray(truth, dtype=bool)
    score = np.asarray(score, dtype=np.float64)
    order = np.argsort(-score, kind="stable")
    ranked_truth = truth[order]
    if not ranked_truth.any():
        return 0.0
    precision_at_hit = np.cumsum(ranked_truth) / (
        np.arange(len(ranked_truth)) + 1
    )
    return float(precision_at_hit[ranked_truth].mean())


def train_n1_gate(args: argparse.Namespace) -> dict[str, Any]:
    for path, name in (
        (args.dataset_npz, "residual GCN dataset"),
        (args.normalizer_json, "feature normalizer"),
        (args.deployment_first_step_summary_csv, "deployment first-step summary"),
    ):
        if not path.exists():
            raise FileNotFoundError(
                f"Missing local {name}: {path}. This trainer will not "
                "regenerate large cascade artifacts."
            )
    if args.epochs <= 0 or args.batch_size <= 0:
        raise ValueError("--epochs and --batch-size must be positive.")
    if not args.positive_weights or min(args.positive_weights) <= 0.0:
        raise ValueError("--positive-weights must contain positive values.")
    if not args.training_seeds:
        raise ValueError("--training-seeds must be non-empty.")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    data = np.load(args.dataset_npz, allow_pickle=True)
    required = {
        "x_gcn",
        "source_y_gcn",
        "source_loss_mask",
        "split",
        "sample_type",
        "seed",
        "line_labels",
        "branch_from_bus",
        "branch_to_bus",
        "feature_names",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"N-1 gate dataset is missing arrays: {missing}")
    s0_rows = np.where(data["sample_type"].astype(str) == "S0")[0]
    x = data["x_gcn"][s0_rows].astype(np.float32)
    y = data["source_y_gcn"][s0_rows].astype(np.int64)
    valid_mask = data["source_loss_mask"][s0_rows].astype(bool)
    split = data["split"][s0_rows].astype(str)
    state_seed = data["seed"][s0_rows].astype(np.int64)
    if args.max_train_s0_states is not None:
        if args.max_train_s0_states <= 0:
            raise ValueError("--max-train-s0-states must be positive.")
        train_rows = np.where(split == "train")[0]
        keep_train = train_rows[: int(args.max_train_s0_states)]
        keep = np.concatenate(
            (
                keep_train,
                np.where(split == "validation")[0],
                np.where(split == "test")[0],
            )
        )
        keep = np.sort(keep)
        x = x[keep]
        y = y[keep]
        valid_mask = valid_mask[keep]
        split = split[keep]
        state_seed = state_seed[keep]
    if not (split == "train").any() or not (split == "validation").any():
        raise ValueError("N-1 gate training requires train and validation S0 states.")

    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    adjacency = build_branch_graph_adjacency_from_endpoints(
        data["branch_from_bus"],
        data["branch_to_bus"],
    )
    adjacency_powers = torch.tensor(
        symbols["_build_adjacency_powers"](adjacency, int(args.k_gcn)),
        dtype=torch.float32,
    )
    fit_args = SimpleNamespace(
        epochs_per_round=int(args.epochs),
        batch_size=int(args.batch_size),
        learning_rate=float(args.learning_rate),
        k_gcn=int(args.k_gcn),
        first_layer_channels=int(args.first_layer_channels),
        second_layer_channels=int(args.second_layer_channels),
        positive_weight=20.0,
    )
    query_mask = valid_mask & (split == "train")[:, None]
    sweep_rows = []
    states_by_weight: dict[float, list[dict[str, Any]]] = {}
    for positive_weight in args.positive_weights:
        states_by_weight[float(positive_weight)] = []
        for training_seed in args.training_seeds:
            model, logs = _fit_one_model(
                x,
                y,
                query_mask,
                valid_mask,
                split,
                adjacency_powers,
                symbols,
                fit_args,
                member_seed=int(training_seed),
                positive_weight_override=float(positive_weight),
            )
            probability = predict_probability(
                model,
                x,
                adjacency_powers,
                torch,
            )
            validation_rows = split == "validation"
            test_rows = split == "test"
            validation_metrics = split_metrics(
                y[validation_rows],
                probability[validation_rows],
                valid_mask[validation_rows],
            )
            test_metrics = split_metrics(
                y[test_rows],
                probability[test_rows],
                valid_mask[test_rows],
            )
            states_by_weight[float(positive_weight)].append(
                {
                    name: value.detach().cpu().clone()
                    for name, value in model.state_dict().items()
                }
            )
            sweep_rows.append(
                {
                    "positive_weight": float(positive_weight),
                    "training_seed": int(training_seed),
                    "num_train_s0_states": int((split == "train").sum()),
                    "num_training_n1_labels": int(query_mask.sum()),
                    "num_training_n1_positive": int(y[query_mask].sum()),
                    "validation_average_precision": float(
                        validation_metrics["average_precision"]
                    ),
                    "test_training_distribution_average_precision": float(
                        test_metrics["average_precision"]
                    ),
                    "best_validation_average_precision_during_training": max(
                        float(row["validation_average_precision"])
                        for row in logs
                    ),
                }
            )
    sweep = pd.DataFrame(sweep_rows)
    mean_validation = sweep.groupby("positive_weight")[
        "validation_average_precision"
    ].mean()
    selected_weight = float(
        max(
            mean_validation.index.tolist(),
            key=lambda weight: (float(mean_validation.loc[weight]), -weight),
        )
    )

    adapter = build_case_adapter("ieee118")
    deployment_case = apply_ieee118_load_scenario(
        adapter.case,
        seed=int(args.deployment_seed),
        load_scale=float(args.deployment_load_scale),
    )
    deployment_case = apply_thermal_limit_mode(
        deployment_case,
        limit_mode=str(args.limit_mode),
        flow_limit_scale=float(args.flow_limit_scale),
        min_rate_a=float(args.min_rate_a),
    )
    deployment_raw, from_bus, to_bus = build_paper_x_from_case(
        deployment_case,
        adapter.line_labels,
        float(args.beta),
    )
    normalizer = load_normalizer(args.normalizer_json)
    deployment_x = normalize_x(
        deployment_raw[None, :, :],
        normalizer,
        PAPER_FEATURE_NAMES,
    ).astype(np.float32)
    deployment_probability = []
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    model_config = PaperGcnTrainConfig(
        epochs=int(args.epochs),
        batch_size=int(args.batch_size),
        learning_rate=float(args.learning_rate),
        k_gcn=int(args.k_gcn),
        first_layer_channels=int(args.first_layer_channels),
        second_layer_channels=int(args.second_layer_channels),
        positive_weight=selected_weight,
        validation_fraction=0.0,
        random_seed=int(args.training_seeds[0]),
    )
    for model_state in states_by_weight[selected_weight]:
        model = PaperStyleRts79Gcn(
            input_channels=deployment_x.shape[2],
            config=model_config,
        )
        model.load_state_dict(model_state)
        deployment_probability.append(
            predict_probability(
                model,
                deployment_x,
                adjacency_powers,
                torch,
            )[0]
        )
    deployment_score = np.stack(deployment_probability).mean(axis=0)
    line_labels = data["line_labels"].astype(str)
    deployment = pd.DataFrame(
        {
            "seed": int(args.deployment_seed),
            "line_label": line_labels,
            "n1_gate_probability": deployment_score,
        }
    ).sort_values(
        ["n1_gate_probability", "line_label"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    deployment["n1_gate_rank"] = np.arange(1, len(deployment) + 1)
    deployment.to_csv(
        args.output_dir / "ieee118_n1_gate_gcn_deployment_scores.csv",
        index=False,
        encoding="utf-8-sig",
    )

    first_step = pd.read_csv(args.deployment_first_step_summary_csv)
    truth_by_line = dict(
        zip(
            first_step["first_line"].astype(str),
            first_step["first_step_critical"].astype(str)
            .str.lower()
            .eq("true")
            .astype(int),
        )
    )
    if set(line_labels) - set(truth_by_line):
        raise ValueError("Deployment first-step summary does not cover every line.")
    audit = deployment.copy()
    audit["n1_critical_audit_only"] = [
        truth_by_line[label] for label in audit["line_label"]
    ]
    deployment_ap = _average_precision(
        audit["n1_critical_audit_only"].to_numpy(),
        audit["n1_gate_probability"].to_numpy(),
    )
    audit.to_csv(
        args.output_dir / "ieee118_n1_gate_gcn_deployment_audit.csv",
        index=False,
        encoding="utf-8-sig",
    )
    sweep.to_csv(
        args.output_dir / "ieee118_n1_gate_gcn_validation_sweep.csv",
        index=False,
        encoding="utf-8-sig",
    )
    torch.save(
        {
            "source_model_class": "PaperStyleRts79Gcn",
            "selected_positive_weight": selected_weight,
            "model_config": vars(model_config),
            "ensemble_model_state_dicts": states_by_weight[selected_weight],
        },
        args.output_dir / "ieee118_n1_gate_gcn_local_checkpoint.pt",
    )

    selected_sweep = sweep.loc[
        sweep["positive_weight"].eq(selected_weight)
    ]
    summary = {
        "status": "complete",
        "research_stage": "Phase 3 original RTS-79 GCN N-1 deployment gate",
        "model_class": "PaperStyleRts79Gcn",
        "source_model_file": (
            "src/gcn_search/legacy_rts79/train_rts79_paper_gcn.py"
        ),
        "model_core_modified": False,
        "target": "S0 direct N-1 critical",
        "n2_outcome_labels_used_for_training": False,
        "num_train_s0_states": int((split == "train").sum()),
        "num_training_n1_labels": int(query_mask.sum()),
        "num_training_n1_positive": int(y[query_mask].sum()),
        "selected_positive_weight_by_validation_ap": selected_weight,
        "selected_validation_average_precision_mean": float(
            selected_sweep["validation_average_precision"].mean()
        ),
        "selected_validation_average_precision_std": float(
            selected_sweep["validation_average_precision"].std(ddof=0)
        ),
        "training_distribution_test_average_precision_mean": float(
            selected_sweep[
                "test_training_distribution_average_precision"
            ].mean()
        ),
        "deployment_load_scale": float(args.deployment_load_scale),
        "deployment_seed": int(args.deployment_seed),
        "deployment_num_n1_critical": int(
            audit["n1_critical_audit_only"].sum()
        ),
        "deployment_average_precision_audit_only": deployment_ap,
        "deployment_score_file_has_high_fidelity_labels": False,
        "deployment_requires_n1_state_construction": False,
        "training_cost": {
            "high_fidelity_n1_labels": int(query_mask.sum()),
            "high_fidelity_n2_labels": 0,
        },
        "interpretation_limit": (
            "The N-1 head removes deployment-time exhaustive N-1 simulation, "
            "but its current offline training labels were previously generated "
            "with N-1 cascade simulations. Active N-1 acquisition remains a "
            "future reduction."
        ),
    }
    (args.output_dir / "ieee118_n1_gate_gcn_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> None:
    print(json.dumps(train_n1_gate(parse_args()), indent=2))


if __name__ == "__main__":
    main()
