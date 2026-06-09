from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from export_simulink_dynamic_cases import SimulinkDynamicCaseExportConfig, export_simulink_dynamic_cases


SEARCH_DIRS = (
    "results/gcn_search/path_reranker_strict_heldout_eval",
    "results/gcn_search/path_reranker_extended_strict_eval",
    "results/gcn_search/path_reranker_fulltruth_eval",
    "results/gcn_search/path_reranker_renewable_eval",
    "results/gcn_search/simulink_dynamic_real_topk",
    "results/gcn_search",
)


@dataclass(frozen=True)
class RealTopKPreparationConfig:
    output_dir: str = "results/gcn_search/simulink_dynamic_real_topk"
    input_csv: str | None = None
    search_dirs: tuple[str, ...] = SEARCH_DIRS
    method: str = "learned_mlp_reranker_strict"
    top_k: tuple[int, ...] = (20, 50, 100, 200)
    use_demo_fallback: bool = False


def prepare_real_topk_for_simulink_dynamic(config: RealTopKPreparationConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    source_csv = Path(config.input_csv) if config.input_csv else _find_real_per_path_csv(config.search_dirs, config.method)
    used_demo_fallback = False
    if source_csv is None:
        if not config.use_demo_fallback:
            searched = ", ".join(config.search_dirs)
            raise RuntimeError(
                "Real per-path ranking CSV not found in tracked artifacts. "
                f"Searched: {searched}. Provide --input-csv for a local ignored per-path ranking CSV, "
                "or pass --use-demo-fallback for interface testing only."
            )
        used_demo_fallback = True
        source_table = _demo_paths()
        source_description = "demo_fallback"
    else:
        source_table = pd.read_csv(source_csv)
        source_description = str(source_csv)
    normalized = _normalize_real_topk(source_table, max(config.top_k))
    paths_csv = out / "real_topk_input_paths.csv"
    normalized.to_csv(paths_csv, index=False, encoding="utf-8-sig")
    export_result = export_simulink_dynamic_cases(
        SimulinkDynamicCaseExportConfig(
            input_csv=str(paths_csv),
            output_dir=str(out),
            top_k=config.top_k,
            make_demo_cases=False,
        )
    )
    run_config = {
        **asdict(config),
        "source_csv": source_description,
        "used_demo_fallback": used_demo_fallback,
        "num_paths": int(len(normalized)),
        "note": "Use demo fallback only for interface tests; real dynamic validation requires a real per-path ranking CSV.",
    }
    (out / "real_topk_input_config.json").write_text(json.dumps(run_config, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output_dir": str(out), "paths_csv": str(paths_csv), **export_result}


def _find_real_per_path_csv(search_dirs: tuple[str, ...], method: str = "learned_mlp_reranker_strict") -> Path | None:
    candidates: list[tuple[int, Path]] = []
    for root in search_dirs:
        path = Path(root)
        if not path.exists():
            continue
        for csv_path in _iter_candidate_csvs(path):
            lower_csv_path = str(csv_path).lower()
            if any(part in lower_csv_path for part in ["ieee14", "simulink_dynamic"]):
                continue
            try:
                table = pd.read_csv(csv_path, nrows=5)
            except Exception:
                continue
            cols = {col.lower() for col in table.columns}
            has_path = "path" in cols or {"first_line", "second_line"}.issubset(cols)
            has_rank_or_score = bool(cols & {"path_rank", "rank", "learned_rank", "rank_in_pio", "reranker_score", "learned_score", "score", "path_score"})
            if has_path and has_rank_or_score and len(table) > 0:
                priority = 10
                if any(token in lower_csv_path for token in ["path_reranker", "reranker", "per_path", "rank", "score", "diagnostics"]):
                    priority += 5
                if "reranker_score" in cols or "learned_score" in cols:
                    priority += 5
                if "path_rank" in cols or "rank" in cols:
                    priority += 3
                candidates.append((priority, csv_path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], str(item[1])))
    return candidates[0][1]


def _iter_candidate_csvs(path: Path) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".csv":
        return [path]
    patterns = ["**/per_path*.csv", "**/*rank*.csv", "**/*score*.csv", "**/diagnostics/*.csv", "**/*.csv"]
    seen: set[Path] = set()
    result: list[Path] = []
    for pattern in patterns:
        for item in path.glob(pattern):
            if item not in seen:
                seen.add(item)
                result.append(item)
    return result


def _normalize_real_topk(table: pd.DataFrame, max_k: int) -> pd.DataFrame:
    work = table.copy()
    if "path" not in work.columns:
        if not {"first_line", "second_line"}.issubset(work.columns):
            raise RuntimeError("Per-path ranking CSV must contain path or first_line/second_line.")
        work["path"] = work["first_line"].astype(str) + "->" + work["second_line"].astype(str)
    if "path_rank" not in work.columns:
        rank_col = _first_existing(work, ["rank", "learned_rank", "rank_in_pio"])
        if rank_col:
            work["path_rank"] = pd.to_numeric(work[rank_col], errors="coerce")
        else:
            score_col = _first_existing(work, ["reranker_score", "learned_score", "score", "path_score", "pio_score"])
            if score_col is None:
                raise RuntimeError("Per-path ranking CSV must contain a rank or score column.")
            work = work.sort_values(score_col, ascending=False).copy()
            work["path_rank"] = np.arange(1, len(work) + 1)
    for col in ["case_id", "source_seed", "pio_score", "paper_score", "lodf_score", "reranker_score", "opa_is_critical", "opa_total_load_shed_mw"]:
        if col not in work.columns:
            work[col] = np.nan
    work["case_id"] = work["case_id"].astype("object")
    if work["reranker_score"].isna().all():
        score_col = _first_existing(work, ["learned_score", "score", "path_score", "pio_score"])
        if score_col:
            work["reranker_score"] = pd.to_numeric(work[score_col], errors="coerce")
    work = work.sort_values(["path_rank", "path"]).head(max_k).reset_index(drop=True)
    parsed = work["path"].astype(str).str.extract(r"L?(\d+)\s*->\s*L?(\d+)", expand=True)
    work["first_line"] = ["L" + str(int(v)).zfill(2) if pd.notna(v) else "" for v in parsed[0]]
    work["second_line"] = ["L" + str(int(v)).zfill(2) if pd.notna(v) else "" for v in parsed[1]]
    work = work[(work["first_line"] != "") & (work["second_line"] != "") & (work["first_line"] != work["second_line"])].copy()
    case_missing = work["case_id"].isna() | (work["case_id"].astype(str).str.strip() == "")
    work.loc[case_missing, "case_id"] = [f"real_topk_{idx:04d}" for idx in range(1, int(case_missing.sum()) + 1)]
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


def _first_existing(table: pd.DataFrame, names: list[str]) -> str | None:
    lookup = {col.lower(): col for col in table.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def _demo_paths() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"path_rank": 1, "path": "L10->L05", "reranker_score": 0.93, "opa_is_critical": True, "opa_total_load_shed_mw": 120.0},
            {"path_rank": 2, "path": "L27->L02", "reranker_score": 0.88, "opa_is_critical": True, "opa_total_load_shed_mw": 85.0},
            {"path_rank": 3, "path": "L16->L17", "reranker_score": 0.81, "opa_is_critical": False, "opa_total_load_shed_mw": 0.0},
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare real learned-reranker Top-K paths for Simulink dynamic validation.")
    parser.add_argument("--output-dir", default=RealTopKPreparationConfig.output_dir)
    parser.add_argument("--input-csv", default=None)
    parser.add_argument("--method", default=RealTopKPreparationConfig.method)
    parser.add_argument("--search-dirs", nargs="*", default=list(SEARCH_DIRS))
    parser.add_argument("--top-k", nargs="+", type=int, default=[20, 50, 100, 200])
    parser.add_argument("--use-demo-fallback", action="store_true")
    parser.add_argument("--allow-demo-fallback", action="store_true", help="Alias for --use-demo-fallback.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_real_topk_for_simulink_dynamic(
        RealTopKPreparationConfig(
            output_dir=args.output_dir,
            input_csv=args.input_csv,
            search_dirs=tuple(args.search_dirs),
            method=args.method,
            top_k=tuple(args.top_k),
            use_demo_fallback=args.use_demo_fallback or args.allow_demo_fallback,
        )
    )


if __name__ == "__main__":
    main()
