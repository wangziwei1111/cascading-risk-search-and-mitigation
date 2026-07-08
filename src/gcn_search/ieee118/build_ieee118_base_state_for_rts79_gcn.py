from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_adapter import build_case_adapter
from convert_ieee118_step2_to_rts79_gcn_format import PAPER_FEATURE_NAMES, normalize_x
from generate_ieee118_ordered_n2_fulltruth import apply_ieee118_load_scenario, apply_thermal_limit_mode
from train_ieee118_with_original_rts79_gcn import build_branch_graph_adjacency_from_endpoints, load_original_rts79_gcn_symbols

from pypower.idx_brch import BR_STATUS, F_BUS, PF, RATE_A, T_BUS
from pypower.idx_bus import BUS_I, PD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build IEEE118 S0 base state for original RTS-79 paper-style GCN.")
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument("--load-scale", type=float, default=1.0)
    parser.add_argument("--limit-mode", choices=["original_rate_a", "flow_scaled"], default="flow_scaled")
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--normalizer-json", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_rts79_protocol_eval",
    )
    return parser.parse_args()


def build_paper_x_from_case(case: dict, line_labels: tuple[str, ...], beta: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    branch = case["branch"]
    bus = case["bus"]
    load_by_bus = {int(row[BUS_I]): float(row[PD]) for row in bus}
    x = np.zeros((branch.shape[0], len(PAPER_FEATURE_NAMES)), dtype=np.float32)
    from_bus = np.zeros(branch.shape[0], dtype=np.int64)
    to_bus = np.zeros(branch.shape[0], dtype=np.int64)
    for idx, row in enumerate(branch):
        status = int(row[BR_STATUS])
        f_bus = int(row[F_BUS])
        t_bus = int(row[T_BUS])
        rate_a = max(float(row[RATE_A]), 1e-8)
        flow = 0.0 if status == 0 or len(row) <= PF else abs(float(row[PF]))
        from_bus[idx] = f_bus
        to_bus[idx] = t_bus
        x[idx, 0] = 1.0 if status == 0 else 0.0
        x[idx, 1] = flow / max(float(beta) * rate_a, 1e-8)
        x[idx, 2] = flow
        x[idx, 3] = max(load_by_bus.get(f_bus, 0.0), load_by_bus.get(t_bus, 0.0))
    if len(line_labels) != x.shape[0]:
        raise ValueError(f"Line label count {len(line_labels)} does not match branch count {x.shape[0]}")
    return x, from_bus, to_bus


def load_normalizer(path: Path) -> dict[str, dict[str, float]]:
    if not path.exists():
        raise FileNotFoundError(f"Missing feature normalizer JSON: {path}")
    normalizer = json.loads(path.read_text(encoding="utf-8"))
    missing = [name for name in PAPER_FEATURE_NAMES if name not in normalizer]
    if missing:
        raise ValueError(f"Normalizer missing paper-style feature keys: {missing}")
    return normalizer


def predict_first_probabilities(model_path: Path, x: np.ndarray, from_bus: np.ndarray, to_bus: np.ndarray) -> np.ndarray:
    symbols = load_original_rts79_gcn_symbols()
    torch = symbols["torch"]
    PaperGcnTrainConfig = symbols["PaperGcnTrainConfig"]
    PaperStyleRts79Gcn = symbols["PaperStyleRts79Gcn"]
    build_adjacency_powers = symbols["_build_adjacency_powers"]
    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    train_config = PaperGcnTrainConfig(**checkpoint["train_config"])
    model = PaperStyleRts79Gcn(input_channels=x.shape[2], config=train_config)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    adjacency = build_branch_graph_adjacency_from_endpoints(from_bus, to_bus)
    adjacency_powers = torch.tensor(build_adjacency_powers(adjacency, train_config.k_gcn), dtype=torch.float32)
    with torch.no_grad():
        logits = model(torch.tensor(x, dtype=torch.float32), adjacency_powers)
        return torch.softmax(logits, dim=2)[0, :, 1].detach().cpu().numpy()


def build_base_state(args: argparse.Namespace) -> dict[str, Any]:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    adapter = build_case_adapter("ieee118")
    scenario_case = apply_ieee118_load_scenario(adapter.case, seed=args.seed, load_scale=args.load_scale)
    scenario_case = apply_thermal_limit_mode(
        scenario_case,
        limit_mode=args.limit_mode,
        flow_limit_scale=args.flow_limit_scale,
        min_rate_a=args.min_rate_a,
    )
    x_raw, from_bus, to_bus = build_paper_x_from_case(scenario_case, adapter.line_labels, args.beta)
    normalizer = load_normalizer(args.normalizer_json)
    x = normalize_x(x_raw[None, :, :], normalizer, PAPER_FEATURE_NAMES).astype(np.float32)
    np.savez(
        args.output_dir / "ieee118_rts79_gcn_base_state.npz",
        x_gcn=x,
        x_gcn_raw=x_raw[None, :, :],
        line_labels=np.asarray(adapter.line_labels, dtype=str),
        branch_from_bus=from_bus,
        branch_to_bus=to_bus,
        feature_names=np.asarray(PAPER_FEATURE_NAMES, dtype=str),
    )
    line_index = pd.DataFrame({"line_index": np.arange(len(adapter.line_labels)), "line_label": adapter.line_labels})
    line_index.to_csv(args.output_dir / "ieee118_rts79_gcn_base_line_index.csv", index=False, encoding="utf-8-sig")
    result: dict[str, Any] = {
        "num_base_states": 1,
        "num_line_labels": len(adapter.line_labels),
        "feature_names": PAPER_FEATURE_NAMES,
        "feature_mode": "paper",
        "model_path": str(args.model_path) if args.model_path else None,
    }
    if args.model_path is not None:
        if not args.model_path.exists():
            raise FileNotFoundError(f"Missing trained original RTS-79 GCN model checkpoint: {args.model_path}")
        prob = predict_first_probabilities(args.model_path, x, from_bus, to_bus)
        first = pd.DataFrame({"line_label": adapter.line_labels, "p_shed_first": prob})
        first = first.sort_values(["p_shed_first", "line_label"], ascending=[False, True]).reset_index(drop=True)
        first["rank_first"] = np.arange(1, len(first) + 1)
        first.to_csv(args.output_dir / "ieee118_rts79_gcn_first_step_probabilities.csv", index=False, encoding="utf-8-sig")
        result["first_step_probability_csv"] = str(args.output_dir / "ieee118_rts79_gcn_first_step_probabilities.csv")
    (args.output_dir / "ieee118_rts79_gcn_base_state_metadata.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    args = parse_args()
    print(json.dumps(build_base_state(args), indent=2))


if __name__ == "__main__":
    main()
