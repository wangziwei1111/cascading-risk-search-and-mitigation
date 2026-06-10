from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


FORBIDDEN_LABEL_COLUMNS = {"is_critical", "critical", "opa_is_critical", "total_load_shed_mw", "opa_total_load_shed_mw", "y_critical", "y_load_shed"}
SCORE_CANDIDATES = ["reranker_score", "learned_score", "score", "path_score", "pio_score", "paper_score", "lodf_score"]


@dataclass(frozen=True)
class SimulinkDynamicCaseExportConfig:
    input_csv: str | None = None
    input_dir: str = "results/gcn_search/path_reranker_strict_heldout_eval"
    output_dir: str = "results/gcn_search/simulink_dynamic_cases"
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    event_1_time: float = 1.0
    event_2_time: float = 5.0
    simulation_end_time: float = 20.0
    method: str = "learned_mlp_reranker_strict"
    make_demo_cases: bool = False


def export_simulink_dynamic_cases(config: SimulinkDynamicCaseExportConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "simulink_dynamic_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    if config.make_demo_cases:
        paths = _make_demo_paths(config)
    elif config.input_csv:
        paths = _load_input_csv(Path(config.input_csv))
    else:
        paths = _load_ranked_paths(Path(config.input_dir), config)
    if paths.empty:
        raise RuntimeError("No valid ordered N-2 paths were found for Simulink export.")
    paths = _normalize_path_table(paths, config).head(max(config.top_k)).reset_index(drop=True)
    event_table = _make_event_table(paths, config)
    manifest = _make_manifest(paths, config)
    coverage = _make_coverage_summary(paths, config)
    matlab_input = event_table[["case_id", "event_time", "event_type", "event_line", "simulation_end_time"]].copy()
    paths.to_csv(out / "simulink_topk_paths.csv", index=False, encoding="utf-8-sig")
    event_table.to_csv(out / "simulink_dynamic_event_table.csv", index=False, encoding="utf-8-sig")
    manifest.to_csv(out / "simulink_dynamic_case_manifest.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(out / "case_export_coverage_summary.csv", index=False, encoding="utf-8-sig")
    matlab_input.to_csv(out / "matlab_batch_input.csv", index=False, encoding="utf-8-sig")
    return {
        "output_dir": str(out),
        "num_cases": int(len(paths)),
        "coverage_summary": str(out / "case_export_coverage_summary.csv"),
        "event_table": str(out / "simulink_dynamic_event_table.csv"),
        "matlab_batch_input": str(out / "matlab_batch_input.csv"),
    }


def _make_demo_paths(config: SimulinkDynamicCaseExportConfig) -> pd.DataFrame:
    rows = [
        {"source_seed": 20260722, "path": "L10->L05", "reranker_score": 0.93, "pio_score": 0.72, "opa_is_critical": True, "opa_total_load_shed_mw": 120.0},
        {"source_seed": 20260722, "path": "L27->L02", "reranker_score": 0.88, "pio_score": 0.69, "opa_is_critical": True, "opa_total_load_shed_mw": 85.0},
        {"source_seed": 20260723, "path": "L16->L17", "reranker_score": 0.81, "pio_score": 0.55, "opa_is_critical": False, "opa_total_load_shed_mw": 0.0},
    ]
    return pd.DataFrame(rows)


def _load_input_csv(input_csv: Path) -> pd.DataFrame:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input path-level CSV does not exist: {input_csv}. Use --make-demo-cases to test the interface.")
    try:
        table = pd.read_csv(input_csv)
    except Exception as exc:
        raise RuntimeError(f"Failed to read input path-level CSV: {input_csv}") from exc
    normalized = {col.lower(): col for col in table.columns}
    has_path = "path" in normalized or {"first_line", "second_line"}.issubset(normalized)
    if not has_path:
        raise RuntimeError(f"Input CSV must contain either path or first_line/second_line columns: {input_csv}")
    return table


def _load_ranked_paths(input_dir: Path, config: SimulinkDynamicCaseExportConfig) -> pd.DataFrame:
    candidates: list[tuple[int, Path, pd.DataFrame]] = []
    for csv_path in input_dir.rglob("*.csv"):
        try:
            table = pd.read_csv(csv_path)
        except Exception:
            continue
        normalized = {col.lower(): col for col in table.columns}
        has_path = "path" in normalized or {"first_line", "second_line"}.issubset(normalized)
        if not has_path:
            continue
        score = _table_priority(table, config)
        if score >= 0:
            candidates.append((score, csv_path, table))
    if not candidates:
        raise RuntimeError(f"No path-level CSV found under {input_dir}. Use --make-demo-cases to test the interface.")
    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    return candidates[0][2]


def _table_priority(table: pd.DataFrame, config: SimulinkDynamicCaseExportConfig) -> int:
    cols = {col.lower() for col in table.columns}
    priority = 0
    if "path" in cols:
        priority += 10
    if any(col in cols for col in ["learned_score", "reranker_score", "score", "path_score"]):
        priority += 5
    if "method" in cols and config.method in set(table["method"].astype(str)):
        priority += 3
    if any(col in cols for col in ["rank", "learned_rank", "path_rank", "rank_in_pio"]):
        priority += 2
    return priority if priority > 0 else -1


def _normalize_path_table(table: pd.DataFrame, config: SimulinkDynamicCaseExportConfig) -> pd.DataFrame:
    work = table.copy()
    if "method" in work.columns and config.method in set(work["method"].astype(str)):
        work = work[work["method"].astype(str) == config.method].copy()
    if "path" not in work.columns:
        work["path"] = work["first_line"].astype(str) + "->" + work["second_line"].astype(str)
    elif {"first_line", "second_line"}.issubset(work.columns):
        fallback_path = work["first_line"].astype(str) + "->" + work["second_line"].astype(str)
        path_missing = work["path"].isna() | (work["path"].astype(str).str.strip() == "")
        work.loc[path_missing, "path"] = fallback_path.loc[path_missing]
    parsed = work["path"].astype(str).map(_parse_path)
    work["first_line"] = [item[0] for item in parsed]
    work["second_line"] = [item[1] for item in parsed]
    work = work[(work["first_line"] != "") & (work["second_line"] != "") & (work["first_line"] != work["second_line"])].copy()
    if "status" in work.columns:
        work = work[work["status"].astype(str).str.lower().isin(["1", "true", "online", "nan", ""])]
    rank_col = _first_existing(work, ["path_rank", "rank", "learned_rank", "rank_in_pio", "rank_in_lodf", "rank_in_paper"])
    if rank_col:
        work["path_rank"] = pd.to_numeric(work[rank_col], errors="coerce")
    else:
        score_col = _score_column(work)
        if score_col:
            work = work.sort_values([score_col, "path"], ascending=[False, True]).copy()
        work["path_rank"] = np.arange(1, len(work) + 1)
    score_col = _score_column(work)
    if score_col:
        work["reranker_score"] = pd.to_numeric(work[score_col], errors="coerce")
    for optional in ["pio_score", "paper_score", "lodf_score", "opa_is_critical", "opa_total_load_shed_mw", "source_seed"]:
        if optional not in work.columns:
            work[optional] = np.nan
    work = work.sort_values(["path_rank", "path"], ascending=[True, True]).drop_duplicates("path").reset_index(drop=True)
    work["case_id"] = [f"dyn_case_{idx:04d}" for idx in range(1, len(work) + 1)]
    return work[
        [
            "case_id",
            "source_seed",
            "path_rank",
            "path",
            "first_line",
            "second_line",
            "pio_score",
            "paper_score",
            "lodf_score",
            "reranker_score",
            "opa_is_critical",
            "opa_total_load_shed_mw",
        ]
    ]


def _parse_path(value: str) -> tuple[str, str]:
    parts = re.split(r"\s*->\s*", value.strip().upper())
    if len(parts) != 2:
        return "", ""
    return _normalize_line(parts[0]), _normalize_line(parts[1])


def _normalize_line(value: str) -> str:
    match = re.search(r"L?(\d+)", str(value).upper())
    if not match:
        return ""
    return f"L{int(match.group(1)):02d}"


def _first_existing(table: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {col.lower(): col for col in table.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def _score_column(table: pd.DataFrame) -> str | None:
    lookup = {col.lower(): col for col in table.columns}
    for name in SCORE_CANDIDATES:
        if name in lookup and name not in FORBIDDEN_LABEL_COLUMNS:
            return lookup[name]
    return None


def _make_event_table(paths: pd.DataFrame, config: SimulinkDynamicCaseExportConfig) -> pd.DataFrame:
    rows: list[dict] = []
    for _, item in paths.iterrows():
        for event_time, event_type, event_line in [
            (config.event_1_time, "trip_first_line", item["first_line"]),
            (config.event_2_time, "trip_second_line", item["second_line"]),
        ]:
            rows.append(
                {
                    "case_id": item["case_id"],
                    "source_seed": item["source_seed"],
                    "path_rank": int(item["path_rank"]),
                    "first_line": item["first_line"],
                    "second_line": item["second_line"],
                    "event_time": float(event_time),
                    "event_type": event_type,
                    "event_line": event_line,
                    "simulation_end_time": float(config.simulation_end_time),
                    "method": config.method,
                    "pio_score": item["pio_score"],
                    "paper_score": item["paper_score"],
                    "lodf_score": item["lodf_score"],
                    "reranker_score": item["reranker_score"],
                    "opa_is_critical": item["opa_is_critical"],
                    "opa_total_load_shed_mw": item["opa_total_load_shed_mw"],
                }
            )
    return pd.DataFrame(rows)


def _make_manifest(paths: pd.DataFrame, config: SimulinkDynamicCaseExportConfig) -> pd.DataFrame:
    manifest = paths.copy()
    requested = int(max(config.top_k))
    manifest["event_1_time"] = float(config.event_1_time)
    manifest["event_2_time"] = float(config.event_2_time)
    manifest["simulation_end_time"] = float(config.simulation_end_time)
    manifest["method"] = config.method
    manifest["full_dynamic_truth"] = False
    manifest["requested_top_k"] = requested
    manifest["exported_case_count"] = int(len(paths))
    manifest["dropped_case_count"] = int(max(0, requested - len(paths)))
    manifest["coverage_ratio"] = float(len(paths) / max(requested, 1))
    manifest["dropped_reason"] = ""
    return manifest


def _make_coverage_summary(paths: pd.DataFrame, config: SimulinkDynamicCaseExportConfig) -> pd.DataFrame:
    requested = int(max(config.top_k))
    exported = int(len(paths))
    return pd.DataFrame(
        [
            {
                "method": config.method,
                "requested_top_k": requested,
                "exported_case_count": exported,
                "dropped_case_count": int(max(0, requested - exported)),
                "coverage_ratio": float(exported / max(requested, 1)),
                "dropped_reason_summary": "none" if exported >= requested else "insufficient_unique_valid_paths_after_export",
            }
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export learned-reranker / PIO-GCN Top-K ordered N-2 paths as Simulink dynamic trip events.")
    parser.add_argument("--input-csv", default=None, help="Explicit path-level ranking CSV. Takes priority over --input-dir.")
    parser.add_argument("--input-dir", default=SimulinkDynamicCaseExportConfig.input_dir)
    parser.add_argument("--output-dir", default=SimulinkDynamicCaseExportConfig.output_dir)
    parser.add_argument("--top-k", type=int, nargs="+", default=list(SimulinkDynamicCaseExportConfig.top_k))
    parser.add_argument("--event-1-time", type=float, default=1.0)
    parser.add_argument("--event-2-time", type=float, default=5.0)
    parser.add_argument("--simulation-end-time", type=float, default=20.0)
    parser.add_argument("--method", default=SimulinkDynamicCaseExportConfig.method)
    parser.add_argument("--make-demo-cases", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_simulink_dynamic_cases(
        SimulinkDynamicCaseExportConfig(
            input_dir=args.input_dir,
            input_csv=args.input_csv,
            output_dir=args.output_dir,
            top_k=tuple(args.top_k),
            event_1_time=args.event_1_time,
            event_2_time=args.event_2_time,
            simulation_end_time=args.simulation_end_time,
            method=args.method,
            make_demo_cases=args.make_demo_cases,
        )
    )


if __name__ == "__main__":
    main()
