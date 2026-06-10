from __future__ import annotations

import argparse
import json
from pathlib import Path

from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases


GROUPS = [
    "learned_mlp_top50",
    "learned_mlp_top100",
    "pio_gcn_top50",
    "pio_gcn_top100",
    "lodf_top50",
    "lodf_top100",
]


def export_dynamic_method_comparison_cases(
    input_root: str | Path,
    output_root: str | Path = "results/gcn_search/simulink_dynamic_method_comparison_cases",
    top_k: tuple[int, ...] = (50, 100),
    event_1_time: float = 1.0,
    event_2_time: float = 5.0,
    simulation_end_time: float = 10.0,
) -> dict:
    in_root = Path(input_root)
    out_root = Path(output_root)
    out_root.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, dict] = {}
    warnings: list[str] = []
    for method in ["learned_mlp", "pio_gcn", "lodf"]:
        for k in top_k:
            input_csv = in_root / f"{method}_top{k}_input_paths.csv"
            group = f"{method}_top{k}"
            if not input_csv.exists():
                warnings.append(f"Skipped {group}: missing {input_csv}.")
                continue
            outputs[group] = export_simulink_dynamic_cases(
                SimulinkDynamicCaseExportConfig(
                    input_csv=str(input_csv),
                    output_dir=str(out_root / group),
                    top_k=(int(k),),
                    event_1_time=event_1_time,
                    event_2_time=event_2_time,
                    simulation_end_time=simulation_end_time,
                    method=group,
                )
            )
    config = {
        "input_root": str(in_root),
        "output_root": str(out_root),
        "top_k": list(top_k),
        "event_1_time": event_1_time,
        "event_2_time": event_2_time,
        "simulation_end_time": simulation_end_time,
        "outputs": outputs,
        "warnings": warnings,
    }
    (out_root / "method_comparison_case_export_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Simulink cases for learned/PIO/LODF dynamic comparison.")
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-root", default="results/gcn_search/simulink_dynamic_method_comparison_cases")
    parser.add_argument("--top-k", type=int, nargs="+", default=[50, 100])
    parser.add_argument("--event-1-time", type=float, default=1.0)
    parser.add_argument("--event-2-time", type=float, default=5.0)
    parser.add_argument("--simulation-end-time", type=float, default=10.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_dynamic_method_comparison_cases(args.input_root, args.output_root, tuple(args.top_k), args.event_1_time, args.event_2_time, args.simulation_end_time)


if __name__ == "__main__":
    main()
