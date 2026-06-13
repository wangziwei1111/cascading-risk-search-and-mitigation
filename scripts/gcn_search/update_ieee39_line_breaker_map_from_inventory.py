from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CURRENT_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map.csv"
INVENTORY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_wrapper_grid_line_block_inventory.csv"
OUTPUT_MAP = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extended.csv"
OUTPUT_SUMMARY = ROOT / "results/gcn_search/ieee39_graphical_dynamic_model/wrapper/ieee39_line_breaker_map_extension_summary.json"

PRESERVED_LINE_IDS = ["L01", "L02", "L03", "L04", "L05"]
TARGET_LINE_IDS = [f"L{idx:02d}" for idx in range(1, 11)]
MAPPING_RULE = (
    "Preserve L01-L05 exactly from ieee39_line_breaker_map.csv. "
    "For L06-L10, use unused real line-like Grid blocks from "
    "ieee39_wrapper_grid_line_block_inventory.csv in ascending inventory_index order."
)


def update_line_map(
    current_map_path: Path = CURRENT_MAP,
    inventory_path: Path = INVENTORY,
    output_map_path: Path = OUTPUT_MAP,
    output_summary_path: Path = OUTPUT_SUMMARY,
) -> dict:
    current = pd.read_csv(current_map_path)
    inventory = pd.read_csv(inventory_path)
    _validate_inputs(current, inventory)

    preserved = _preserved_rows(current)
    used_paths = set(preserved["line_block_path"].astype(str))
    candidates = _line_like_candidates(inventory, used_paths)

    rows = []
    rows.extend(preserved.to_dict(orient="records"))
    newly_mapped: list[str] = []
    unmapped: list[str] = []
    warnings: list[str] = []
    candidate_iter = iter(candidates.to_dict(orient="records"))

    for line_id in TARGET_LINE_IDS:
        if line_id in PRESERVED_LINE_IDS:
            continue
        candidate = next(candidate_iter, None)
        if candidate is None:
            rows.append(_unmapped_row(line_id))
            unmapped.append(line_id)
            warnings.append(f"{line_id} left not_in_current_line_map because inventory candidates were exhausted.")
            continue
        rows.append(_row_from_candidate(line_id, candidate))
        newly_mapped.append(line_id)

    extended = pd.DataFrame(rows, columns=current.columns)
    output_map_path.parent.mkdir(parents=True, exist_ok=True)
    extended.to_csv(output_map_path, index=False, encoding="utf-8-sig")

    summary = {
        "existing_mapped_line_ids": current["line_id"].astype(str).tolist(),
        "preserved_line_ids": PRESERVED_LINE_IDS,
        "newly_mapped_line_ids": newly_mapped,
        "unmapped_line_ids": unmapped,
        "mapping_rule": MAPPING_RULE,
        "source_inventory_path": str(inventory_path.relative_to(ROOT)),
        "output_map_path": str(output_map_path.relative_to(ROOT)),
        "warnings": warnings,
    }
    output_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _validate_inputs(current: pd.DataFrame, inventory: pd.DataFrame) -> None:
    required_current = {"line_id", "from_bus", "to_bus", "line_block_path", "mapping_status", "note"}
    missing_current = required_current - set(current.columns)
    if missing_current:
        raise ValueError(f"Current map missing required columns: {sorted(missing_current)}")
    required_inventory = {
        "inventory_index",
        "block_name",
        "block_path",
        "bus_from_candidate",
        "bus_to_candidate",
        "is_line_like_candidate",
    }
    missing_inventory = required_inventory - set(inventory.columns)
    if missing_inventory:
        raise ValueError(f"Inventory missing required columns: {sorted(missing_inventory)}")


def _preserved_rows(current: pd.DataFrame) -> pd.DataFrame:
    preserved = current[current["line_id"].astype(str).isin(PRESERVED_LINE_IDS)].copy()
    missing = sorted(set(PRESERVED_LINE_IDS) - set(preserved["line_id"].astype(str)))
    if missing:
        raise ValueError(f"Cannot preserve missing line IDs: {missing}")
    order = {line_id: idx for idx, line_id in enumerate(PRESERVED_LINE_IDS)}
    preserved["_order"] = preserved["line_id"].map(order)
    preserved = preserved.sort_values("_order").drop(columns=["_order"])
    return preserved


def _line_like_candidates(inventory: pd.DataFrame, used_paths: set[str]) -> pd.DataFrame:
    candidate_mask = inventory["is_line_like_candidate"].astype(str).str.lower().isin({"1", "true", "yes"})
    candidates = inventory[candidate_mask].copy()
    candidates["inventory_index"] = pd.to_numeric(candidates["inventory_index"], errors="coerce")
    candidates = candidates.dropna(subset=["inventory_index", "block_path"])
    candidates = candidates[~candidates["block_path"].astype(str).isin(used_paths)]
    return candidates.sort_values(["inventory_index", "block_path"])


def _row_from_candidate(line_id: str, candidate: dict) -> dict:
    from_bus = str(candidate.get("bus_from_candidate", "") or "")
    to_bus = str(candidate.get("bus_to_candidate", "") or "")
    block_path = str(candidate.get("block_path", "") or "")
    if not block_path or block_path == "nan":
        return _unmapped_row(line_id)
    return {
        "line_id": line_id,
        "from_bus": from_bus,
        "to_bus": to_bus,
        "line_block_path": block_path,
        "breaker_block_path": "",
        "current_measurement_block_path": "",
        "voltage_measurement_block_path": "",
        "fault_injection_bus_or_line": from_bus,
        "mapping_status": "pilot_line_block_disable",
        "note": (
            "Extended from real IEEE39 wrapper Grid inventory; no explicit breaker found; "
            "pilot trip disables the line block before simulation."
        ),
    }


def _unmapped_row(line_id: str) -> dict:
    return {
        "line_id": line_id,
        "from_bus": "",
        "to_bus": "",
        "line_block_path": "not_in_current_line_map",
        "breaker_block_path": "",
        "current_measurement_block_path": "",
        "voltage_measurement_block_path": "",
        "fault_injection_bus_or_line": "",
        "mapping_status": "not_mapped",
        "note": "No verified real Grid line block path in inventory; do not invent a block path.",
    }


def main() -> None:
    summary = update_line_map()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
