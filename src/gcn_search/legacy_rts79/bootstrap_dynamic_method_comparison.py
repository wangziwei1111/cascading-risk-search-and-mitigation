from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from compute_dynamic_stress_score import compute_dynamic_stress_score


GROUPS = ["learned_mlp_top50", "learned_mlp_top100", "pio_gcn_top50", "pio_gcn_top100", "lodf_top50", "lodf_top100"]


def bootstrap_dynamic_method_comparison(
    results_root: str | Path,
    cases_root: str | Path,
    summary_csv: str | Path,
    output_dir: str | Path,
    bootstrap_n: int = 1000,
    seed: int = 20260824,
) -> dict:
    del cases_root
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    samples: dict[tuple[str, int], pd.DataFrame] = {}
    for group in GROUPS:
        method, top_k = _parse_group(group)
        dynamic_csv = Path(results_root) / group / "simulink_dynamic_simulation_results.csv"
        if not dynamic_csv.exists():
            continue
        dynamic = pd.read_csv(dynamic_csv)
        stress = compute_dynamic_stress_score(dynamic_csv, Path(results_root) / group / "dynamic_stress_score_for_bootstrap.csv")
        data = dynamic.merge(stress[["case_id", "dynamic_stress_score"]], on="case_id", how="left")
        samples[(method, top_k)] = data
        for metric, column, reducer in [
            ("dynamic_precision_at_k", "dynamic_unstable", lambda x: np.mean(x.astype(float))),
            ("mean_dynamic_stress_score", "dynamic_stress_score", lambda x: np.mean(x.astype(float))),
            ("mean_frequency_nadir_hz", "frequency_nadir_hz", lambda x: np.mean(x.astype(float))),
            ("mean_rotor_angle_coi_deg", "max_rotor_angle_separation_coi_deg", lambda x: np.mean(x.astype(float))),
        ]:
            estimate, low, high = _bootstrap_metric(data[column], reducer, bootstrap_n, rng)
            rows.append(_row(method, top_k, metric, estimate, low, high, bootstrap_n, seed))
    rows.extend(_comparison_rows(samples, bootstrap_n, seed, rng))
    table = pd.DataFrame(rows)
    csv_path = out / "dynamic_method_bootstrap_ci.csv"
    json_path = out / "dynamic_method_bootstrap_ci.json"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    payload = {
        "summary_csv": str(summary_csv),
        "bootstrap_n": int(bootstrap_n),
        "random_seed": int(seed),
        "num_rows": int(len(table)),
        "conclusion": _conclusion(table),
        "note": "preliminary diagnostic bootstrap; no dynamic recall is reported",
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), **payload}


def _bootstrap_metric(series: pd.Series, reducer, bootstrap_n: int, rng: np.random.Generator) -> tuple[float, float, float]:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return 0.0, 0.0, 0.0
    estimate = float(reducer(values))
    boots = np.empty(bootstrap_n, dtype=float)
    for idx in range(bootstrap_n):
        sample = rng.choice(values, size=len(values), replace=True)
        boots[idx] = reducer(sample)
    return estimate, float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))


def _comparison_rows(samples: dict[tuple[str, int], pd.DataFrame], bootstrap_n: int, seed: int, rng: np.random.Generator) -> list[dict]:
    rows: list[dict] = []
    for top_k in [50, 100]:
        learned = samples.get(("learned_mlp", top_k))
        for control in ["pio_gcn", "lodf"]:
            other = samples.get((control, top_k))
            if learned is None or other is None:
                continue
            for metric, column in [
                (f"learned_precision_minus_{control}", "dynamic_unstable"),
                (f"learned_stress_minus_{control}", "dynamic_stress_score"),
            ]:
                l_values = pd.to_numeric(learned[column], errors="coerce").dropna().to_numpy(dtype=float)
                o_values = pd.to_numeric(other[column], errors="coerce").dropna().to_numpy(dtype=float)
                if len(l_values) == 0 or len(o_values) == 0:
                    estimate = low = high = 0.0
                else:
                    estimate = float(np.mean(l_values) - np.mean(o_values))
                    boots = np.empty(bootstrap_n, dtype=float)
                    for idx in range(bootstrap_n):
                        boots[idx] = float(np.mean(rng.choice(l_values, size=len(l_values), replace=True)) - np.mean(rng.choice(o_values, size=len(o_values), replace=True)))
                    low = float(np.quantile(boots, 0.025))
                    high = float(np.quantile(boots, 0.975))
                rows.append(_row("learned_mlp", top_k, metric, estimate, low, high, bootstrap_n, seed))
    return rows


def _row(method: str, top_k: int, metric: str, estimate: float, low: float, high: float, bootstrap_n: int, seed: int) -> dict:
    return {
        "method": method,
        "top_k": int(top_k),
        "metric": metric,
        "estimate": float(estimate),
        "ci_low": float(low),
        "ci_high": float(high),
        "bootstrap_n": int(bootstrap_n),
        "random_seed": int(seed),
    }


def _parse_group(group: str) -> tuple[str, int]:
    if group.endswith("_top50"):
        return group.removesuffix("_top50"), 50
    if group.endswith("_top100"):
        return group.removesuffix("_top100"), 100
    return group, 0


def _conclusion(table: pd.DataFrame) -> str:
    comparisons = table[table["metric"].astype(str).str.startswith("learned_precision_minus")]
    if comparisons.empty:
        return "inconclusive"
    if (comparisons["ci_low"].astype(float) > 0.0).any():
        return "learned_advantage_observed_preliminary"
    return "no robust learned dynamic advantage observed"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap dynamic method comparison uncertainty.")
    parser.add_argument("--results-root", required=True)
    parser.add_argument("--cases-root", required=True)
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--bootstrap-n", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=20260824)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bootstrap_dynamic_method_comparison(args.results_root, args.cases_root, args.summary_csv, args.output_dir, args.bootstrap_n, args.seed)


if __name__ == "__main__":
    main()
