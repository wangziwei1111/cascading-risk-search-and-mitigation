from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .branch_graph import BranchGraph, build_branch_graph, normalized_adjacency_with_self_loops, static_branch_features


SPLITS = ("train", "val", "test")


@dataclass(frozen=True)
class RiskDataset:
    split: str
    scenario_ids: np.ndarray
    features: np.ndarray
    targets: np.ndarray
    outage_masks: np.ndarray
    true_risk: np.ndarray
    best_improvement: np.ndarray
    adjacency: np.ndarray
    normalized_adjacency: np.ndarray


def parse_outages(value) -> list[int]:
    if value is None:
        return []
    if isinstance(value, list):
        return [int(v) for v in value]
    text = str(value).strip()
    if not text:
        return []
    return [int(part.strip()) for part in text.split(",") if part.strip()]


def summarize_action_scan(csv_path: Path) -> dict[int, dict]:
    by_scenario: dict[int, list[dict]] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            by_scenario.setdefault(int(row["scenario_id"]), []).append(row)
    summaries = {}
    for scenario_id, rows in by_scenario.items():
        do_nothing = next(row for row in rows if int(row["action"]) == 0)
        valid = [row for row in rows if str(row.get("is_valid_action", "")).lower() == "true"]
        best = min(valid or rows, key=lambda row: float(row["negative_return"]))
        risk = float(do_nothing["negative_return"])
        best_negative_return = float(best["negative_return"])
        summaries[scenario_id] = {
            "scenario_id": scenario_id,
            "initial_outages": parse_outages(do_nothing["initial_outages"]),
            "initial_outage_type": do_nothing["initial_outage_type"],
            "initial_outage_order": int(do_nothing["initial_outage_order"]),
            "chronic_index": int(do_nothing["chronic_index"]),
            "load_scale": float(do_nothing["load_scale"]),
            "gen_scale": float(do_nothing["gen_scale"]),
            "do_nothing_negative_return": risk,
            "best_negative_return": best_negative_return,
            "best_improvement": risk - best_negative_return,
            "best_action": int(best["action"]),
            "best_action_line": "" if best.get("action_line", "") == "" else int(float(best["action_line"])),
            "pf_failed": str(do_nothing["pf_failed"]).lower() == "true",
            "num_line_outages": int(do_nothing["num_line_outages"]),
            "load_shed_MW": float(do_nothing["load_shed_MW"]),
        }
    return summaries


def build_split_dataset(case: dict, split: str, action_scan_csv: Path) -> tuple[RiskDataset, list[dict]]:
    graph = build_branch_graph(case)
    static_features = static_branch_features(case, graph)
    summaries = summarize_action_scan(action_scan_csv)
    scenario_rows = [summaries[sid] for sid in sorted(summaries)]
    features, targets, outage_masks, risks, improvements, scenario_ids = [], [], [], [], [], []
    risk_scale = max(1.0, max(float(row["do_nothing_negative_return"]) for row in scenario_rows))
    improvement_scale = max(1.0, max(float(row["best_improvement"]) for row in scenario_rows))
    for row in scenario_rows:
        outage_mask = np.zeros(len(graph.lines), dtype=np.float32)
        for line in row["initial_outages"]:
            outage_mask[line] = 1.0
        dynamic = np.column_stack([
            outage_mask,
            np.full(len(graph.lines), row["initial_outage_order"] / 2.0, dtype=np.float32),
            np.full(len(graph.lines), row["load_scale"], dtype=np.float32),
            np.full(len(graph.lines), row["gen_scale"], dtype=np.float32),
            np.full(len(graph.lines), row["best_improvement"] / improvement_scale, dtype=np.float32),
        ])
        features.append(np.concatenate([static_features, dynamic], axis=1))
        targets.append(outage_mask * (row["do_nothing_negative_return"] / risk_scale))
        outage_masks.append(outage_mask)
        risks.append(row["do_nothing_negative_return"])
        improvements.append(row["best_improvement"])
        scenario_ids.append(row["scenario_id"])
    dataset = RiskDataset(
        split=split,
        scenario_ids=np.asarray(scenario_ids, dtype=np.int64),
        features=np.asarray(features, dtype=np.float32),
        targets=np.asarray(targets, dtype=np.float32),
        outage_masks=np.asarray(outage_masks, dtype=np.float32),
        true_risk=np.asarray(risks, dtype=np.float32),
        best_improvement=np.asarray(improvements, dtype=np.float32),
        adjacency=graph.adjacency,
        normalized_adjacency=normalized_adjacency_with_self_loops(graph.adjacency),
    )
    return dataset, scenario_rows


def save_dataset(dataset: RiskDataset, rows: list[dict], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_dir / f"{dataset.split}_branch_gcn_samples.npz",
        scenario_ids=dataset.scenario_ids,
        features=dataset.features,
        targets=dataset.targets,
        outage_masks=dataset.outage_masks,
        true_risk=dataset.true_risk,
        best_improvement=dataset.best_improvement,
        adjacency=dataset.adjacency,
        normalized_adjacency=dataset.normalized_adjacency,
    )
    fields = [
        "scenario_id", "initial_outages", "initial_outage_type", "initial_outage_order",
        "chronic_index", "load_scale", "gen_scale", "do_nothing_negative_return",
        "best_negative_return", "best_improvement", "best_action", "best_action_line",
        "pf_failed", "num_line_outages", "load_shed_MW",
    ]
    with open(output_dir / f"{dataset.split}_risk_scenarios.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["initial_outages"] = ",".join(str(v) for v in row["initial_outages"])
            writer.writerow(out)


def load_dataset(path: Path, split: str) -> RiskDataset:
    data = np.load(path / f"{split}_branch_gcn_samples.npz")
    return RiskDataset(
        split=split,
        scenario_ids=data["scenario_ids"],
        features=data["features"],
        targets=data["targets"],
        outage_masks=data["outage_masks"],
        true_risk=data["true_risk"],
        best_improvement=data["best_improvement"],
        adjacency=data["adjacency"],
        normalized_adjacency=data["normalized_adjacency"],
    )


def write_manifest(output_dir: Path, graph: BranchGraph, config: dict, split_counts: dict[str, int]) -> None:
    payload = {
        "system": "PYPOWER IEEE14",
        "num_buses": 14,
        "num_branches": len(graph.lines),
        "branch_graph_edge_count_directed": int(graph.edge_index.shape[1]),
        "splits": split_counts,
        "label_definition": "do_nothing_negative_return on the same IEEE14 RL scenario; assigned to initially outaged branch nodes",
        "legacy_mapping": "none",
        "config": config,
    }
    with open(output_dir / "dataset_manifest.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

