from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from prepare_real_topk_for_simulink_dynamic import _normalize_real_topk


METHOD_SCORES = {
    "learned_mlp": ["reranker_score", "learned_score", "score", "path_score"],
    "pio_gcn": ["pio_score"],
    "lodf": ["lodf_score"],
}


def prepare_dynamic_method_comparison_topk(
    input_csv: str | Path,
    output_dir: str | Path,
    top_k: int = 100,
    ensure_unique_paths: bool = False,
    fill_to_k: bool = False,
    max_search_multiplier: int = 5,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    table = pd.read_csv(input_csv)
    outputs: dict[str, str] = {}
    warnings: list[str] = []
    coverage: dict[str, dict] = {}
    for method, score_names in METHOD_SCORES.items():
        score_col = _first_existing(table, score_names)
        if score_col is None:
            warnings.append(f"Skipped {method}: missing score column from {score_names}.")
            continue
        ranked = table.copy()
        ranked[score_col] = pd.to_numeric(ranked[score_col], errors="coerce")
        if method == "learned_mlp" and "path_rank" in ranked.columns:
            ranked = ranked.sort_values(["reranker_score", "path_rank", "path"], ascending=[False, True, True]).copy()
        else:
            ranked = ranked.sort_values([score_col, "path"], ascending=[False, True]).copy()
        ranked["path_rank"] = np.arange(1, len(ranked) + 1)
        if ensure_unique_paths or fill_to_k:
            normalized, method_coverage = _normalize_unique_valid_topk(ranked, top_k, max_search_multiplier)
        else:
            normalized = _normalize_real_topk(ranked, top_k)
            method_coverage = _coverage_payload(ranked, normalized, top_k, duplicate_dropped=0, invalid_dropped=0, same_line_dropped=0, filled_from_rank_depth=0)
        method_outputs: dict[str, str] = {}
        for k in sorted({50, int(top_k)}):
            if k > top_k:
                continue
            output_path = out / f"{method}_top{k}_input_paths.csv"
            normalized.head(k).to_csv(output_path, index=False, encoding="utf-8-sig")
            method_outputs[f"top{k}"] = str(output_path)
        legacy_path = out / f"{method}_topk_input_paths.csv"
        normalized.head(top_k).to_csv(legacy_path, index=False, encoding="utf-8-sig")
        method_outputs["topk"] = str(legacy_path)
        outputs[method] = method_outputs
        coverage[method] = method_coverage
        if len(normalized) < top_k:
            warnings.append(f"{method} produced only {len(normalized)} unique valid paths for requested top_k={top_k}.")
    config = {
        "input_csv": str(input_csv),
        "output_dir": str(out),
        "top_k": top_k,
        "ensure_unique_paths": bool(ensure_unique_paths),
        "fill_to_k": bool(fill_to_k),
        "max_search_multiplier": int(max_search_multiplier),
        "outputs": outputs,
        "coverage": coverage,
        "warnings": warnings,
        "label_columns_used_for_sorting": [],
        "forbidden_label_columns": ["opa_is_critical", "opa_total_load_shed_mw"],
    }
    (out / "dynamic_method_comparison_input_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    return config


def _normalize_unique_valid_topk(table: pd.DataFrame, top_k: int, max_search_multiplier: int) -> tuple[pd.DataFrame, dict]:
    search_limit = min(len(table), max(top_k, top_k * max(1, int(max_search_multiplier))))
    selected: list[pd.Series] = []
    seen: set[str] = set()
    duplicate_dropped = 0
    invalid_dropped = 0
    same_line_dropped = 0
    missing_line_label_count = 0
    for _, row in table.head(search_limit).iterrows():
        first, second, path = _extract_path(row)
        if not first or not second:
            invalid_dropped += 1
            missing_line_label_count += 1
            continue
        if first == second:
            same_line_dropped += 1
            continue
        if path in seen:
            duplicate_dropped += 1
            continue
        seen.add(path)
        item = row.copy()
        item["first_line"] = first
        item["second_line"] = second
        item["path"] = path
        selected.append(item)
        if len(selected) >= top_k:
            break
    normalized = pd.DataFrame(selected)
    if normalized.empty:
        normalized = pd.DataFrame(columns=["case_id", "source_seed", "path_rank", "path", "first_line", "second_line", "pio_score", "paper_score", "lodf_score", "reranker_score", "opa_is_critical", "opa_total_load_shed_mw"])
    else:
        normalized = _normalize_real_topk(normalized, len(normalized))
    filled = max(0, len(normalized) - min(top_k, len(table.head(top_k).drop_duplicates("path")) if "path" in table.columns else 0))
    coverage = _coverage_payload(
        table,
        normalized,
        top_k,
        duplicate_dropped=duplicate_dropped,
        invalid_dropped=invalid_dropped,
        same_line_dropped=same_line_dropped,
        filled_from_rank_depth=filled,
    )
    coverage["missing_line_label_count"] = int(missing_line_label_count)
    coverage["ranking_rows_searched"] = int(search_limit)
    return normalized, coverage


def _extract_path(row: pd.Series) -> tuple[str, str, str]:
    if "path" in row and pd.notna(row["path"]):
        parsed = _parse_path(str(row["path"]))
        if parsed[0] and parsed[1]:
            return parsed[0], parsed[1], f"{parsed[0]}->{parsed[1]}"
    first = _normalize_line(row.get("first_line", ""))
    second = _normalize_line(row.get("second_line", ""))
    return first, second, f"{first}->{second}" if first and second else ""


def _parse_path(value: str) -> tuple[str, str]:
    parts = re.split(r"\s*->\s*", value.strip().upper())
    if len(parts) != 2:
        return "", ""
    return _normalize_line(parts[0]), _normalize_line(parts[1])


def _normalize_line(value: object) -> str:
    match = re.search(r"L?(\d+)", str(value).upper())
    if not match:
        return ""
    idx = int(match.group(1))
    if idx < 1 or idx > 38:
        return ""
    return f"L{idx:02d}"


def _coverage_payload(
    ranked: pd.DataFrame,
    normalized: pd.DataFrame,
    top_k: int,
    duplicate_dropped: int,
    invalid_dropped: int,
    same_line_dropped: int,
    filled_from_rank_depth: int,
) -> dict:
    return {
        "requested_top_k": int(top_k),
        "ranking_rows_available": int(len(ranked)),
        "unique_paths_available": int(ranked["path"].nunique()) if "path" in ranked.columns else int(len(ranked)),
        "produced_rows": int(len(normalized)),
        "duplicate_dropped": int(duplicate_dropped),
        "invalid_dropped": int(invalid_dropped),
        "same_line_dropped": int(same_line_dropped),
        "filled_from_rank_depth": int(filled_from_rank_depth),
        "coverage_ratio": float(len(normalized) / max(top_k, 1)),
    }


def _first_existing(table: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {col.lower(): col for col in table.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare learned/Pio/LODF Top-K inputs for dynamic method comparison.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_method_comparison_inputs")
    parser.add_argument("--top-k", type=int, default=100)
    parser.add_argument("--ensure-unique-paths", action="store_true")
    parser.add_argument("--fill-to-k", action="store_true")
    parser.add_argument("--max-search-multiplier", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_dynamic_method_comparison_topk(
        args.input_csv,
        args.output_dir,
        args.top_k,
        args.ensure_unique_paths,
        args.fill_to_k,
        args.max_search_multiplier,
    )


if __name__ == "__main__":
    main()
