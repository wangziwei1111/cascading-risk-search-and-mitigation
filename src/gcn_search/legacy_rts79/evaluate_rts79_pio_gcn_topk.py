from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from gcn_physics_constraints import apply_candidate_probability_mask, make_candidate_mask
from online_state_update import apply_measured_state_to_case, load_measured_state_json
from rts79_cascade import (
    Rts79InitialConfig,
    run_initial_dcopf,
)
from rts79_cascade_from_case import offline_line_labels, run_sequential_outages_from_case, simulate_cascade_path_from_case
from train_rts79_paper_gcn import PaperGcnTrainConfig, PaperStyleRts79Gcn, _make_x_gcn_physics


@dataclass(frozen=True)
class PioTopkConfig:
    model: str
    normalizer: str
    output_dir: str
    seed: int = 20260722
    beta: float = 1.2
    security_limit: float = 1.0
    top_k: tuple[int, ...] = (20,)
    measured_state_json: str | None = None
    run_full_truth: bool = False
    max_paths_for_smoke_test: int | None = None
    use_candidate_probability_mask: bool = True


def evaluate_pio_gcn_topk(config: PioTopkConfig) -> dict:
    start_time = time.time()
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model, adjacency_powers = _load_model(config.model)
    normalizer = json.loads(Path(config.normalizer).read_text(encoding="utf-8"))
    initial_config = Rts79InitialConfig(random_seed=config.seed)
    root_case = run_initial_dcopf(initial_config).case
    measured_state = load_measured_state_json(config.measured_state_json) if config.measured_state_json else None
    if measured_state is not None:
        root_case = apply_measured_state_to_case(root_case, measured_state)
    initial_offline = offline_line_labels(root_case)
    order = _make_path_order(model, adjacency_powers, normalizer, root_case, config)
    if config.max_paths_for_smoke_test:
        order = order[: config.max_paths_for_smoke_test]
    for row in order:
        row["used_measured_state"] = measured_state is not None
        row["initial_offline_lines"] = ",".join(initial_offline)
        row["simulation_initial_source"] = "measured_state_updated_case" if measured_state is not None else "seed_initial_dcopf_case"
    pd.DataFrame(order).to_csv(out / "pio_gcn_topk_order.csv", index=False, encoding="utf-8-sig")
    max_top_k = min(max(config.top_k), len(order))
    simulation_rows = []
    for row in order[:max_top_k]:
        first, second = row["path"].split("->")
        result = simulate_cascade_path_from_case(root_case, [first, second], beta=config.beta, security_limit=config.security_limit)
        simulation_rows.append(
            {
                "path": row["path"],
                "rank": row["rank"],
                "score": row["score"],
                "used_measured_state": measured_state is not None,
                "initial_offline_lines": ",".join(initial_offline),
                "simulation_initial_source": "measured_state_updated_case" if measured_state is not None else "seed_initial_dcopf_case",
                "total_load_shed_mw": float(result.total_load_shed_mw),
                "critical": bool(result.total_load_shed_mw > 1e-7),
                "final_outage_labels": ",".join(result.final_outage_labels),
            }
        )
    sim_table = pd.DataFrame(simulation_rows)
    sim_table.to_csv(out / "pio_gcn_topk_simulation_results.csv", index=False, encoding="utf-8-sig")
    truth_table = None
    if config.run_full_truth:
        truth_table = _make_full_truth(root_case, config)
        truth_table.to_csv(out / "pio_gcn_topk_full_truth.csv", index=False, encoding="utf-8-sig")
    elif config.max_paths_for_smoke_test:
        truth_table = _make_smoke_truth(order, root_case, config)
        truth_table.to_csv(out / "pio_gcn_topk_smoke_truth.csv", index=False, encoding="utf-8-sig")
    summary_rows = []
    for k in config.top_k:
        subset = sim_table.head(min(k, len(sim_table)))
        found = int(subset["critical"].sum()) if not subset.empty else 0
        critical_path_recall = ""
        smoke_recall = ""
        if truth_table is not None:
            truth_set = set(truth_table.loc[truth_table["critical"], "path"].tolist())
            found_set = set(subset.loc[subset["critical"], "path"].tolist()) if not subset.empty else set()
            if config.run_full_truth and not config.max_paths_for_smoke_test:
                critical_path_recall = float(len(found_set & truth_set) / max(len(truth_set), 1))
            else:
                smoke_recall = float(len(found_set & truth_set) / max(len(truth_set), 1))
        summary_rows.append(
            {
                "method": "pio_gcn_topk",
                "top_k": int(k),
                "num_simulated_paths": int(len(subset)),
                "num_critical_found": found,
                "critical_path_recall": critical_path_recall,
                "smoke_recall": smoke_recall,
                "used_measured_state": measured_state is not None,
                "initial_offline_lines": ",".join(initial_offline),
                "simulation_initial_source": "measured_state_updated_case" if measured_state is not None else "seed_initial_dcopf_case",
                "runtime_seconds": float(time.time() - start_time),
                "notes": "smoke truth only" if config.max_paths_for_smoke_test else "",
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out / "pio_gcn_topk_summary.csv", index=False, encoding="utf-8-sig")
    (out / "pio_gcn_topk_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output_dir": str(out), "summary": summary_rows}


def _load_model(path: str | Path) -> tuple[PaperStyleRts79Gcn, torch.Tensor]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    train_config = PaperGcnTrainConfig(**checkpoint["train_config"])
    first_weight = checkpoint["model_state_dict"]["graph_1.weight"]
    model = PaperStyleRts79Gcn(input_channels=int(first_weight.shape[0]), config=train_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, torch.tensor(checkpoint["adjacency_powers"], dtype=torch.float32)


def _make_path_order(model, adjacency_powers, normalizer, root_case, config: PioTopkConfig) -> list[dict]:
    first_prob = _predict(model, adjacency_powers, normalizer, root_case, config)
    first_mask = make_candidate_mask(root_case)
    if config.use_candidate_probability_mask:
        first_prob = apply_candidate_probability_mask(first_prob, first_mask)
    records = []
    for first_idx in np.where(first_mask)[0]:
        first_line = f"L{first_idx + 1:02d}"
        state = run_sequential_outages_from_case(root_case, [first_line], beta=config.beta, security_limit=config.security_limit)
        second_case = state["case"]
        second_prob = _predict(model, adjacency_powers, normalizer, second_case, config)
        second_mask = make_candidate_mask(second_case, used_lines=[first_line])
        if config.use_candidate_probability_mask:
            second_prob = apply_candidate_probability_mask(second_prob, second_mask)
        for second_idx in np.where(second_mask)[0]:
            second_line = f"L{second_idx + 1:02d}"
            score = float(first_prob[first_idx] * second_prob[second_idx])
            records.append(
                {
                    "path": f"{first_line}->{second_line}",
                    "score": score,
                    "first_probability": float(first_prob[first_idx]),
                    "second_probability": float(second_prob[second_idx]),
                }
            )
    records.sort(key=lambda row: (-row["score"], row["path"]))
    for rank, row in enumerate(records, start=1):
        row["rank"] = rank
    return records


def _predict(model, adjacency_powers, normalizer, case, config: PioTopkConfig) -> np.ndarray:
    x_raw = _make_x_gcn_physics(case, config.beta, config.security_limit)[None, :, :]
    x = x_raw.copy()
    for idx, name in enumerate(normalizer):
        if idx >= x.shape[2]:
            break
        x[:, :, idx] = (x[:, :, idx] - normalizer[name]["mean"]) / normalizer[name]["std"]
    with torch.no_grad():
        logits = model(torch.tensor(x, dtype=torch.float32), adjacency_powers)
        return torch.softmax(logits, dim=2)[0, :, 1].numpy()


def _make_smoke_truth(order: list[dict], root_case: dict, config: PioTopkConfig) -> pd.DataFrame:
    rows = []
    limit = config.max_paths_for_smoke_test or len(order)
    for row in order[:limit]:
        first, second = row["path"].split("->")
        result = simulate_cascade_path_from_case(root_case, [first, second], beta=config.beta, security_limit=config.security_limit)
        rows.append({"path": row["path"], "critical": bool(result.total_load_shed_mw > 1e-7)})
    return pd.DataFrame(rows)


def _make_full_truth(root_case: dict, config: PioTopkConfig) -> pd.DataFrame:
    rows = []
    first_mask = make_candidate_mask(root_case)
    for first_idx in np.where(first_mask)[0]:
        first = f"L{first_idx + 1:02d}"
        first_state = run_sequential_outages_from_case(root_case, [first], beta=config.beta, security_limit=config.security_limit)
        second_mask = make_candidate_mask(first_state["case"], used_lines=[first])
        for second_idx in np.where(second_mask)[0]:
            second = f"L{second_idx + 1:02d}"
            result = simulate_cascade_path_from_case(root_case, [first, second], beta=config.beta, security_limit=config.security_limit)
            rows.append({"path": f"{first}->{second}", "critical": bool(result.total_load_shed_mw > 1e-7), "total_load_shed_mw": float(result.total_load_shed_mw)})
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate PIO-GCN Top-K RTS-79 cascade path search.")
    parser.add_argument("--model", required=True)
    parser.add_argument("--normalizer", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=20260722)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--top-k", type=int, nargs="+", default=[20])
    parser.add_argument("--measured-state-json")
    parser.add_argument("--run-full-truth", action="store_true")
    parser.add_argument("--max-paths-for-smoke-test", type=int)
    parser.add_argument("--disable-candidate-probability-mask", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    evaluate_pio_gcn_topk(
        PioTopkConfig(
            model=args.model,
            normalizer=args.normalizer,
            output_dir=args.output_dir,
            seed=args.seed,
            beta=args.beta,
            security_limit=args.security_limit,
            top_k=tuple(args.top_k),
            measured_state_json=args.measured_state_json,
            run_full_truth=args.run_full_truth,
            max_paths_for_smoke_test=args.max_paths_for_smoke_test,
            use_candidate_probability_mask=not args.disable_candidate_probability_mask,
        )
    )


if __name__ == "__main__":
    main()
