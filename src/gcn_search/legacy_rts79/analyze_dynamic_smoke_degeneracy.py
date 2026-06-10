from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def analyze_dynamic_smoke_degeneracy(
    summary_csv: str | Path,
    relay_security_summary_csv: str | Path,
    dynamic_results_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_real_pipeline_summary",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(summary_csv)
    relay = _metric_table(pd.read_csv(relay_security_summary_csv))
    dynamic = pd.read_csv(dynamic_results_csv)
    row = summary.iloc[0].to_dict()
    num_cases = int(row.get("num_dynamic_cases", row.get("num_simulated", len(dynamic))))
    dynamic_precision = float(row.get("dynamic_precision_at_k", 0.0))
    passive_cases = int(relay.get("cases_with_passive_relay_trip", row.get("cases_with_passive_relay_trip", 0)))
    security_cases = int(relay.get("cases_with_security_redispatch_or_load_shed", row.get("cases_with_security_redispatch_or_load_shed", 0)))
    opa_agreement = int(row.get("opa_critical_and_dynamic_unstable_count", 0)) + int(row.get("opa_noncritical_and_dynamic_stable_count", 0))
    opa_noncritical_unstable = int(row.get("opa_noncritical_but_dynamic_unstable_count", 0))
    all_unstable = dynamic_precision >= 1.0
    all_stable = dynamic_precision <= 0.0
    all_passive = num_cases > 0 and passive_cases >= num_cases
    no_security = security_cases == 0
    degeneracy_warning = bool(all_unstable or all_stable or all_passive or (no_security and all_passive))
    result = {
        "dynamic_precision_at_k": dynamic_precision,
        "num_dynamic_cases": num_cases,
        "passive_relay_trip_case_fraction": float(passive_cases / max(num_cases, 1)),
        "security_redispatch_case_fraction": float(security_cases / max(num_cases, 1)),
        "opa_dynamic_agreement_count": opa_agreement,
        "opa_noncritical_dynamic_unstable_count": opa_noncritical_unstable,
        "all_cases_dynamic_unstable": bool(all_unstable),
        "all_cases_passive_relay_trip": bool(all_passive),
        "no_security_actions": bool(no_security),
        "degeneracy_warning": degeneracy_warning,
        "note": "Warning indicates possible scale sensitivity or non-degeneracy calibration need; it does not by itself prove the pipeline is wrong.",
    }
    table = pd.DataFrame([result])
    csv_path = out / "dynamic_smoke_degeneracy_check.csv"
    json_path = out / "dynamic_smoke_degeneracy_check.json"
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), **result}


def _metric_table(table: pd.DataFrame) -> dict[str, float]:
    if not {"metric", "value"}.issubset(table.columns):
        return {}
    return {str(row["metric"]): float(row["value"]) for _, row in table.iterrows()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether a Top-K dynamic smoke result is degenerate.")
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--relay-security-summary-csv", required=True)
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_real_pipeline_summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    analyze_dynamic_smoke_degeneracy(args.summary_csv, args.relay_security_summary_csv, args.dynamic_results_csv, args.output_dir)


if __name__ == "__main__":
    main()
