from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
DEFAULT_EXTENDED_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv"
DEFAULT_OUTPUT_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full.csv"
DEFAULT_OUTPUT_SUMMARY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_full_summary.json"


def build_full_line_map(
    inventory_csv: str | Path = DEFAULT_INVENTORY,
    existing_map_csv: str | Path = DEFAULT_EXTENDED_MAP,
    output_map_csv: str | Path = DEFAULT_OUTPUT_MAP,
    output_summary_json: str | Path = DEFAULT_OUTPUT_SUMMARY,
) -> dict:
    inventory_path = Path(inventory_csv)
    existing_path = Path(existing_map_csv)
    output_map = Path(output_map_csv)
    output_summary = Path(output_summary_json)
    inventory = pd.read_csv(inventory_path)
    existing = pd.read_csv(existing_path)

    required_inventory = {"inventory_index", "block_path", "bus_from_candidate", "bus_to_candidate", "is_line_like_candidate"}
    missing_inventory = required_inventory - set(inventory.columns)
    if missing_inventory:
        raise RuntimeError(f"Inventory missing columns: {sorted(missing_inventory)}")
    required_map = {
        "line_id",
        "from_bus",
        "to_bus",
        "line_block_path",
        "breaker_block_path",
        "current_measurement_block_path",
        "voltage_measurement_block_path",
        "fault_injection_bus_or_line",
        "mapping_status",
        "note",
    }
    missing_map = required_map - set(existing.columns)
    if missing_map:
        raise RuntimeError(f"Existing map missing columns: {sorted(missing_map)}")

    preserved = existing.copy()
    used_paths = set(preserved["line_block_path"].astype(str))
    used_ids = preserved["line_id"].astype(str).tolist()
    next_index = max(_line_number(line_id) for line_id in used_ids) + 1
    candidates = inventory[
        (inventory["is_line_like_candidate"].astype(str).str.lower().isin({"1", "true"}))
        & (~inventory["block_path"].astype(str).isin(used_paths))
    ].copy()
    candidates = candidates.sort_values("inventory_index")

    new_rows = []
    warnings: list[str] = []
    for _, row in candidates.iterrows():
        block_path = str(row["block_path"])
        from_bus = str(row.get("bus_from_candidate", "")).strip()
        to_bus = str(row.get("bus_to_candidate", "")).strip()
        if not block_path.startswith("IEEE39BusSystem_dynamic_experiment_wrapper/Grid/"):
            warnings.append(f"Skipped non-Grid candidate: {block_path}")
            continue
        if not from_bus or not to_bus or from_bus.lower() == "nan" or to_bus.lower() == "nan":
            warnings.append(f"Skipped candidate without parsed buses: {block_path}")
            continue
        line_id = f"L{next_index:02d}"
        next_index += 1
        new_rows.append(
            {
                "line_id": line_id,
                "from_bus": from_bus,
                "to_bus": to_bus,
                "line_block_path": block_path,
                "breaker_block_path": pd.NA,
                "current_measurement_block_path": pd.NA,
                "voltage_measurement_block_path": pd.NA,
                "fault_injection_bus_or_line": from_bus,
                "mapping_status": "pilot_line_block_disable",
                "note": "Full map extension from real IEEE39 wrapper Grid inventory; no explicit breaker found; pilot trip disables the line block before simulation.",
            }
        )

    full_map = pd.concat([preserved, pd.DataFrame(new_rows, columns=preserved.columns)], ignore_index=True)
    output_map.parent.mkdir(parents=True, exist_ok=True)
    full_map.to_csv(output_map, index=False, encoding="utf-8-sig")
    summary = {
        "preserved_line_ids": preserved["line_id"].astype(str).tolist(),
        "newly_mapped_line_ids": [row["line_id"] for row in new_rows],
        "num_preserved_lines": int(len(preserved)),
        "num_newly_mapped_lines": int(len(new_rows)),
        "mapping_rule": "Preserve existing L01-L10 map; append unused inventory line-like Grid blocks by ascending inventory_index.",
        "source_inventory_path": str(inventory_path),
        "source_existing_map_path": str(existing_path),
        "output_map_path": str(output_map),
        "warnings": warnings,
    }
    output_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _line_number(line_id: str) -> int:
    match = re.fullmatch(r"L(\d+)", str(line_id).strip().upper())
    return int(match.group(1)) if match else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the full IEEE39 line map from wrapper Grid inventory.")
    parser.add_argument("--inventory-csv", default=str(DEFAULT_INVENTORY))
    parser.add_argument("--existing-map-csv", default=str(DEFAULT_EXTENDED_MAP))
    parser.add_argument("--output-map-csv", default=str(DEFAULT_OUTPUT_MAP))
    parser.add_argument("--output-summary-json", default=str(DEFAULT_OUTPUT_SUMMARY))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_full_line_map(
        args.inventory_csv,
        args.existing_map_csv,
        args.output_map_csv,
        args.output_summary_json,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
