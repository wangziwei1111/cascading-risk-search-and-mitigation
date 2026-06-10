from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def compare_ieee39_graphical_vs_simplified(
    inventory_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/ieee39_graphical_dynamic_model",
) -> dict[str, str]:
    inventory = pd.read_csv(inventory_csv)
    primary = inventory[inventory.get("can_open_in_matlab", False).astype(bool)].head(1)
    if primary.empty and not inventory.empty:
        primary = inventory.head(1)
    row = primary.iloc[0].to_dict() if not primary.empty else {}
    comparison = pd.DataFrame(
        [
            {
                "model_family": "IEEE39 graphical model",
                "role": "preferred future dynamic-label backend",
                "network": "IEEE 39-bus / New England 10-machine",
                "graphical_blocks": True,
                "contains_generators": bool(row.get("contains_generators", False)),
                "contains_exciters": bool(row.get("contains_exciters", False)),
                "contains_governors": bool(row.get("contains_governors", False)),
                "contains_loads": bool(row.get("contains_loads", False)),
                "protection_status": "wrapper needed; protection not yet engineering-grade",
                "claim_boundary": "preliminary dynamic-label source, not an engineering-grade conclusion",
            },
            {
                "model_family": "RTS-79 simplified swing-equation prototype",
                "role": "baseline diagnostic prototype",
                "network": "IEEE RTS-79",
                "graphical_blocks": False,
                "contains_generators": "assumed aggregate swing states",
                "contains_exciters": False,
                "contains_governors": False,
                "contains_loads": "simplified loads",
                "protection_status": "prototype relay/security approximations",
                "claim_boundary": "baseline only; no EMT or full OPF dynamic conclusion",
            },
        ]
    )
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "ieee39_vs_simplified_comparison.csv"
    json_path = out / "ieee39_vs_simplified_comparison.json"
    comparison.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(comparison.to_dict(orient="records"), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare IEEE39 graphical dynamic model with simplified RTS-79 prototype.")
    parser.add_argument("--inventory-csv", default="results/gcn_search/ieee39_graphical_dynamic_model/model_inventory.csv")
    parser.add_argument("--output-dir", default="results/gcn_search/ieee39_graphical_dynamic_model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(compare_ieee39_graphical_vs_simplified(args.inventory_csv, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
