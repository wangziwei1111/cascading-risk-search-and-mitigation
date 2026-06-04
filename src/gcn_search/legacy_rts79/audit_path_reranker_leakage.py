from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from train_path_reranker import FEATURE_COLUMNS


FORBIDDEN_FEATURES = {
    "is_critical",
    "y_critical",
    "y_load_shed",
    "total_load_shed_mw",
    "oracle_rank",
    "rank_in_oracle",
    "critical_rank",
    "truth_rank",
}


@dataclass(frozen=True)
class LeakageAuditConfig:
    dataset_dir: str = "results/gcn_search/path_reranker_dataset"
    model_dir: str = "results/gcn_search/path_reranker_models"
    eval_dir: str = "results/gcn_search/path_reranker_fulltruth_eval"
    output_dir: str = "results/gcn_search/path_reranker_leakage_audit"
    suspicious_recall_threshold: float = 0.90


def audit_path_reranker_leakage(config: LeakageAuditConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(Path(config.dataset_dir) / "path_reranker_train.csv")
    val = pd.read_csv(Path(config.dataset_dir) / "path_reranker_val.csv")
    test = pd.read_csv(Path(config.dataset_dir) / "path_reranker_test.csv")
    all_data = pd.concat([train.assign(split="train"), val.assign(split="val"), test.assign(split="test")], ignore_index=True)
    split_rows = _seed_split_audit(train, val, test)
    feature_rows = _forbidden_feature_check(all_data)
    leakage_rows = _feature_leakage_report(all_data)
    summary_rows = _summary(config, split_rows, feature_rows, leakage_rows)
    pd.DataFrame(split_rows).to_csv(out / "seed_split_audit.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(feature_rows).to_csv(out / "forbidden_feature_check.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(leakage_rows).to_csv(out / "feature_leakage_report.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(summary_rows).to_csv(out / "leakage_audit_summary.csv", index=False, encoding="utf-8-sig")
    _write_recommendations(out, summary_rows, leakage_rows)
    return {"output_dir": str(out)}


def _seed_split_audit(train: pd.DataFrame, val: pd.DataFrame, test: pd.DataFrame) -> list[dict]:
    splits = {"train": train, "val": val, "test": test}
    seed_sets = {name: set(table["seed"].astype(int).unique().tolist()) for name, table in splits.items()}
    rows = []
    for name, seeds in seed_sets.items():
        rows.append({"check": f"{name}_seeds", "value": ",".join(map(str, sorted(seeds))), "passed": True})
    for a, b in [("train", "val"), ("train", "test"), ("val", "test")]:
        overlap = sorted(seed_sets[a] & seed_sets[b])
        rows.append({"check": f"{a}_{b}_seed_overlap", "value": ",".join(map(str, overlap)), "passed": len(overlap) == 0})
    for a, b in [("train", "test"), ("val", "test")]:
        overlap_paths = set(splits[a]["path"]) & set(splits[b]["path"])
        rows.append(
            {
                "check": f"{a}_{b}_path_label_overlap",
                "value": len(overlap_paths),
                "passed": True,
                "notes": "Same topology path labels repeat across operating-condition seeds; seed split remains the leakage boundary.",
            }
        )
    return rows


def _forbidden_feature_check(dataset: pd.DataFrame) -> list[dict]:
    rows = []
    for name in FEATURE_COLUMNS:
        forbidden = name in FORBIDDEN_FEATURES or "truth" in name.lower() or "oracle" in name.lower()
        rows.append({"feature": name, "is_forbidden": forbidden, "passed": not forbidden})
    for name in sorted(FORBIDDEN_FEATURES & set(dataset.columns)):
        rows.append({"feature": name, "is_forbidden": True, "passed": name not in FEATURE_COLUMNS, "notes": "Present as label/evaluation field only."})
    return rows


def _feature_leakage_report(dataset: pd.DataFrame) -> list[dict]:
    rows = []
    y = dataset["y_critical"].to_numpy(dtype=float)
    for feature in FEATURE_COLUMNS:
        x = dataset[feature].replace([np.inf, -np.inf], np.nan).fillna(0.0).to_numpy(dtype=float)
        corr = _safe_corr(x, y)
        rows.append(
            {
                "feature": feature,
                "pearson_abs_corr_with_y_critical": abs(corr),
                "suspicious_near_perfect_corr": abs(corr) > 0.98,
                "unique_values": int(pd.Series(x).nunique()),
            }
        )
    return rows


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    if np.std(x) < 1e-12 or np.std(y) < 1e-12:
        return 0.0
    return float(np.corrcoef(x, y)[0, 1])


def _summary(config: LeakageAuditConfig, split_rows: list[dict], feature_rows: list[dict], leakage_rows: list[dict]) -> list[dict]:
    eval_path = Path(config.eval_dir) / "path_reranker_method_comparison.csv"
    suspicious_perf = False
    if eval_path.exists():
        table = pd.read_csv(eval_path)
        subset = table[(table["method"] == "learned_mlp_reranker") & (table["top_k"] == 100)]
        suspicious_perf = bool(not subset.empty and float(subset.iloc[0]["mean_recall"]) >= config.suspicious_recall_threshold)
    return [
        {"check": "seed_split_disjoint", "passed": all(bool(row.get("passed", False)) for row in split_rows if "seed_overlap" in row["check"])},
        {"check": "no_forbidden_input_features", "passed": all(bool(row["passed"]) for row in feature_rows if row["feature"] in FEATURE_COLUMNS)},
        {"check": "no_near_perfect_feature_label_corr", "passed": not any(bool(row["suspicious_near_perfect_corr"]) for row in leakage_rows)},
        {"check": "suspiciously_high_performance_warning", "passed": not suspicious_perf, "notes": "High recall requires strict held-out confirmation."},
    ]


def _write_recommendations(out: Path, summary_rows: list[dict], leakage_rows: list[dict]) -> None:
    failed = [row for row in summary_rows if not bool(row.get("passed", False)) and row["check"] != "suspiciously_high_performance_warning"]
    suspicious = [row for row in summary_rows if row["check"] == "suspiciously_high_performance_warning" and not bool(row.get("passed", False))]
    high_corr = sorted(leakage_rows, key=lambda row: row["pearson_abs_corr_with_y_critical"], reverse=True)[:5]
    text = "# Path Reranker Leakage Audit\n\n"
    text += "## Leakage Finding\n\n"
    text += "No direct forbidden input feature was found.\n\n" if not failed else "Potential leakage checks failed and should be fixed before reporting.\n\n"
    text += "The high learned-reranker recall is flagged as suspiciously high, so strict held-out evaluation is required.\n\n" if suspicious else "No suspicious performance warning was triggered.\n\n"
    text += "## Highest Feature Correlations\n\n"
    for row in high_corr:
        text += f"- {row['feature']}: abs(correlation) = {row['pearson_abs_corr_with_y_critical']:.4f}\n"
    text += "\n## Recommendation\n\n"
    text += "Report the learned reranker only together with strict held-out seed results. Current evidence can be shown to an advisor as preliminary, but not as final evidence.\n"
    (out / "recommendations.md").write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit path reranker dataset and metrics for leakage.")
    parser.add_argument("--dataset-dir", default=LeakageAuditConfig.dataset_dir)
    parser.add_argument("--model-dir", default=LeakageAuditConfig.model_dir)
    parser.add_argument("--eval-dir", default=LeakageAuditConfig.eval_dir)
    parser.add_argument("--output-dir", default=LeakageAuditConfig.output_dir)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit_path_reranker_leakage(LeakageAuditConfig(dataset_dir=args.dataset_dir, model_dir=args.model_dir, eval_dir=args.eval_dir, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
