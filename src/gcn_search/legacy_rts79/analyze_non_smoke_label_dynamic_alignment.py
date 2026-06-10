from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


GROUPS = ["learned_mlp_top50", "learned_mlp_top100", "pio_gcn_top50", "pio_gcn_top100", "lodf_top50", "lodf_top100"]


def analyze_non_smoke_label_dynamic_alignment(
    ranking_csv: str | Path,
    summary_csv: str | Path,
    rank_depth_csv: str | Path,
    output_dir: str | Path,
    cases_root: str | Path | None = None,
    stress_ranks_csv: str | Path | None = None,
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ranking = pd.read_csv(ranking_csv)
    summary = pd.read_csv(summary_csv) if Path(summary_csv).exists() else pd.DataFrame()
    rank_depth = pd.read_csv(rank_depth_csv) if Path(rank_depth_csv).exists() else pd.DataFrame()
    stress = _load_stress_ranks(stress_ranks_csv, Path(summary_csv).parent)
    cases_root_path = Path(cases_root) if cases_root else _infer_cases_root(Path(summary_csv).parent)

    rows: list[dict] = []
    for group in GROUPS:
        method, top_k = _parse_group(group)
        paths = _load_group_paths(cases_root_path, group, ranking, method, top_k)
        if paths.empty:
            continue
        group_stress = stress[stress.get("group", pd.Series(dtype=str)).astype(str) == group] if not stress.empty and "group" in stress.columns else pd.DataFrame()
        merged = paths.merge(group_stress[["case_id", "dynamic_unstable", "dynamic_stress_score"]] if not group_stress.empty else pd.DataFrame(columns=["case_id", "dynamic_unstable", "dynamic_stress_score"]), on="case_id", how="left")
        merged["dynamic_unstable"] = merged["dynamic_unstable"].fillna(False).astype(bool)
        summary_row = summary[(summary.get("method", pd.Series(dtype=str)) == method) & (summary.get("top_k", pd.Series(dtype=int)) == top_k)]
        rows.append(
            {
                "method": method,
                "top_k": int(top_k),
                "num_paths": int(len(merged)),
                "opa_is_critical_positive_count": int(pd.to_numeric(merged.get("opa_is_critical", 0), errors="coerce").fillna(0).sum()),
                "mean_opa_total_load_shed_mw": _mean(merged.get("opa_total_load_shed_mw", pd.Series(dtype=float))),
                "dynamic_unstable_count": int(merged["dynamic_unstable"].sum()),
                "mean_dynamic_stress_score": _mean(merged.get("dynamic_stress_score", pd.Series(dtype=float))),
                "stress_corr_with_opa_total_load_shed_mw": _corr(merged, "dynamic_stress_score", "opa_total_load_shed_mw"),
                "stress_corr_with_reranker_score": _corr(merged, "dynamic_stress_score", "reranker_score"),
                "stress_corr_with_pio_score": _corr(merged, "dynamic_stress_score", "pio_score"),
                "stress_corr_with_lodf_score": _corr(merged, "dynamic_stress_score", "lodf_score"),
                "summary_dynamic_precision_at_k": _first(summary_row, "dynamic_precision_at_k", 0.0),
                "rank_depth_mean_stress_at_k": _rank_depth_value(rank_depth, method, top_k),
            }
        )
    table = pd.DataFrame(rows)
    csv_path = out / "non_smoke_label_dynamic_alignment.csv"
    json_path = out / "non_smoke_label_dynamic_alignment.json"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    payload = {
        "ranking_csv": str(ranking_csv),
        "summary_csv": str(summary_csv),
        "rank_depth_csv": str(rank_depth_csv),
        "cases_root": str(cases_root_path),
        "num_rows": int(len(table)),
        "note": "preliminary diagnostic alignment only; no dynamic recall is reported",
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), **payload}


def _load_stress_ranks(stress_ranks_csv: str | Path | None, summary_dir: Path) -> pd.DataFrame:
    candidates = []
    if stress_ranks_csv:
        candidates.append(Path(stress_ranks_csv))
    candidates.extend(summary_dir.glob("*stress_ranks.csv"))
    for candidate in candidates:
        if candidate.exists():
            return pd.read_csv(candidate)
    return pd.DataFrame()


def _infer_cases_root(summary_dir: Path) -> Path:
    name = summary_dir.name
    if "non_smoke" in name:
        return summary_dir.parent / "simulink_dynamic_method_comparison_cases_non_smoke"
    return summary_dir.parent / "simulink_dynamic_method_comparison_cases"


def _load_group_paths(cases_root: Path, group: str, ranking: pd.DataFrame, method: str, top_k: int) -> pd.DataFrame:
    topk_csv = cases_root / group / "simulink_topk_paths.csv"
    if topk_csv.exists():
        return pd.read_csv(topk_csv)
    score_col = {"learned_mlp": "reranker_score", "pio_gcn": "pio_score", "lodf": "lodf_score"}.get(method, "reranker_score")
    work = ranking.copy()
    if score_col in work.columns:
        work[score_col] = pd.to_numeric(work[score_col], errors="coerce")
        work = work.sort_values([score_col, "path"], ascending=[False, True]).head(top_k).copy()
    else:
        work = work.sort_values(["path_rank", "path"], ascending=[True, True]).head(top_k).copy()
    if "case_id" not in work.columns:
        work["case_id"] = [f"dyn_case_{idx:04d}" for idx in range(1, len(work) + 1)]
    return work


def _parse_group(group: str) -> tuple[str, int]:
    if group.endswith("_top50"):
        return group.removesuffix("_top50"), 50
    if group.endswith("_top100"):
        return group.removesuffix("_top100"), 100
    return group, 0


def _mean(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return float(values.mean()) if len(values) else 0.0


def _corr(table: pd.DataFrame, left: str, right: str) -> float:
    if left not in table.columns or right not in table.columns:
        return 0.0
    pair = table[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(pair) < 2 or pair[left].nunique() < 2 or pair[right].nunique() < 2:
        return 0.0
    return float(pair[left].corr(pair[right]))


def _first(table: pd.DataFrame, column: str, default: float) -> float:
    if table.empty or column not in table.columns:
        return default
    return float(pd.to_numeric(table[column], errors="coerce").fillna(default).iloc[0])


def _rank_depth_value(table: pd.DataFrame, method: str, k: int) -> float:
    if table.empty:
        return 0.0
    row = table[(table.get("method", pd.Series(dtype=str)) == method) & (table.get("k", pd.Series(dtype=int)) == k)]
    return _first(row, "mean_dynamic_stress_score_at_k", 0.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze OPA label and dynamic stress alignment for non-smoke dynamic comparison.")
    parser.add_argument("--ranking-csv", required=True)
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--rank-depth-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--cases-root")
    parser.add_argument("--stress-ranks-csv")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_non_smoke_label_dynamic_alignment(
        args.ranking_csv,
        args.summary_csv,
        args.rank_depth_csv,
        args.output_dir,
        args.cases_root,
        args.stress_ranks_csv,
    )


if __name__ == "__main__":
    main()
