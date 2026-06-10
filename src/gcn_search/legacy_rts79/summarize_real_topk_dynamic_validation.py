from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


VALID_SCOPES = {
    "default_top20_preliminary_dynamic_smoke",
    "calibrated_top20_preliminary_dynamic_smoke",
    "top20_preliminary_dynamic_smoke",
    "top20_preliminary_smoke",
    "top50_preliminary_dynamic_validation",
    "top100_preliminary_dynamic_validation",
    "top50_preliminary",
    "top100_preliminary",
    "full_dynamic_truth",
}


def summarize_real_topk_dynamic_validation(
    precision_csv: str | Path,
    overlap_csv: str | Path,
    relay_security_summary_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_real_pipeline_summary",
    method: str = "learned_mlp_reranker_strict",
    result_scope: str = "top20_preliminary_smoke",
    run_status: str = "completed",
    smoke_mode: bool = True,
    matlab_executed: bool = True,
    num_train_seeds: int = 3,
    num_test_seeds: int = 1,
    calibrated: bool = False,
    calibration_options_json: str | None = None,
    degeneracy_check_json: str | None = None,
) -> dict:
    if result_scope not in VALID_SCOPES:
        raise ValueError(f"result_scope must be one of {sorted(VALID_SCOPES)}")
    if result_scope == "full_dynamic_truth":
        scope_note = "Full dynamic truth scope was declared by the caller; verify that a complete dynamic truth table exists."
    else:
        scope_note = "Top-K preliminary dynamic validation only; no dynamic recall is reported."

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    precision = pd.read_csv(precision_csv)
    if result_scope in {"top20_preliminary_dynamic_smoke", "default_top20_preliminary_dynamic_smoke", "calibrated_top20_preliminary_dynamic_smoke"} and "top_k" in precision.columns:
        precision = precision[pd.to_numeric(precision["top_k"], errors="coerce") == 20].copy()
    overlap = _metric_table(pd.read_csv(overlap_csv))
    relay = _metric_table(pd.read_csv(relay_security_summary_csv))
    degeneracy_warning = _load_degeneracy_warning(degeneracy_check_json)

    rows = []
    for _, item in precision.iterrows():
        row = {
            "run_status": run_status,
            "method": method,
            "top_k": int(item["top_k"]),
            "num_simulated": int(item["num_simulated"]),
            "num_dynamic_cases": int(item["num_simulated"]),
            "dynamic_precision_at_k": float(item["dynamic_precision_at_k"]),
            "opa_critical_and_dynamic_unstable_count": int(overlap.get("opa_critical_and_dynamic_unstable_count", 0)),
            "opa_critical_but_dynamic_stable_count": int(overlap.get("opa_critical_but_dynamic_stable_count", 0)),
            "opa_noncritical_but_dynamic_unstable_count": int(overlap.get("opa_noncritical_but_dynamic_unstable_count", 0)),
            "cases_with_security_redispatch_or_load_shed": int(relay.get("cases_with_security_redispatch_or_load_shed", 0)),
            "cases_with_passive_relay_trip": int(relay.get("cases_with_passive_relay_trip", 0)),
            "total_dynamic_load_shed_mw": float(relay.get("total_dynamic_load_shed_mw", 0.0)),
            "passive_relay_trip_count": int(relay.get("passive_relay_trip_count", relay.get("cases_with_passive_relay_trip", 0))),
            "security_redispatch_count": int(relay.get("security_redispatch_count", relay.get("cases_with_security_redispatch_or_load_shed", 0))),
            "result_scope": result_scope,
            "smoke_mode": bool(smoke_mode),
            "num_train_seeds": int(num_train_seeds),
            "num_test_seeds": int(num_test_seeds),
            "matlab_executed": bool(matlab_executed),
            "calibrated": bool(calibrated),
            "calibration_options_json": calibration_options_json or "",
            "degeneracy_warning": bool(degeneracy_warning),
            "passive_relay_trip_case_fraction": float(int(relay.get("cases_with_passive_relay_trip", 0)) / max(int(item["num_simulated"]), 1)),
            "security_redispatch_case_fraction": float(int(relay.get("cases_with_security_redispatch_or_load_shed", 0)) / max(int(item["num_simulated"]), 1)),
            "note": scope_note,
        }
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary_csv = out / "real_topk_dynamic_validation_summary.csv"
    summary_json = out / "real_topk_dynamic_validation_summary.json"
    smoke_summary_csv = out / "real_topk_dynamic_smoke_summary.csv"
    smoke_summary_json = out / "real_topk_dynamic_smoke_summary.json"
    scoped_csv = out / _scoped_summary_name(result_scope, "csv")
    scoped_json = out / _scoped_summary_name(result_scope, "json")
    brief_md = out / "real_topk_dynamic_validation_brief.md"
    summary.to_csv(summary_csv, index=False, encoding="utf-8-sig")
    summary.to_csv(smoke_summary_csv, index=False, encoding="utf-8-sig")
    summary.to_csv(scoped_csv, index=False, encoding="utf-8-sig")
    payload = {
        "method": method,
        "result_scope": result_scope,
        "scope_note": scope_note,
        "num_rows": int(len(summary)),
        "summary_csv": str(summary_csv),
    }
    summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    smoke_summary_json.write_text(json.dumps({**payload, "summary_csv": str(smoke_summary_csv)}, ensure_ascii=False, indent=2), encoding="utf-8")
    scoped_json.write_text(json.dumps({**payload, "summary_csv": str(scoped_csv)}, ensure_ascii=False, indent=2), encoding="utf-8")
    brief_md.write_text(_make_brief(summary, scope_note), encoding="utf-8")
    return {"summary_csv": str(summary_csv), "summary_json": str(summary_json), "smoke_summary_csv": str(smoke_summary_csv), "smoke_summary_json": str(smoke_summary_json), "scoped_summary_csv": str(scoped_csv), "scoped_summary_json": str(scoped_json), "brief_md": str(brief_md)}


def _metric_table(table: pd.DataFrame) -> dict[str, float]:
    if not {"metric", "value"}.issubset(table.columns):
        return {}
    result: dict[str, float] = {}
    for _, row in table.iterrows():
        result[str(row["metric"])] = float(row["value"])
    return result


def _make_brief(summary: pd.DataFrame, scope_note: str) -> str:
    lines = [
        "# Real Top-K Dynamic Validation Brief",
        "",
        scope_note,
        "",
        "| top_k | num_simulated | dynamic_precision_at_k | security_cases | relay_cases | load_shed_mw |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {int(row['top_k'])} | {int(row['num_simulated'])} | {float(row['dynamic_precision_at_k']):.4f} | "
            f"{int(row['cases_with_security_redispatch_or_load_shed'])} | {int(row['cases_with_passive_relay_trip'])} | "
            f"{float(row['total_dynamic_load_shed_mw']):.4f} |"
        )
    lines.extend(["", "No dynamic recall is reported unless full dynamic truth is available.", ""])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize real Top-K dynamic validation into compact review artifacts.")
    parser.add_argument("--precision-csv", required=True)
    parser.add_argument("--overlap-csv", required=True)
    parser.add_argument("--relay-security-summary-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_real_pipeline_summary")
    parser.add_argument("--method", default="learned_mlp_reranker_strict")
    parser.add_argument("--result-scope", default="top20_preliminary_dynamic_smoke", choices=sorted(VALID_SCOPES))
    parser.add_argument("--run-status", default="completed")
    parser.add_argument("--smoke-mode", action="store_true")
    parser.add_argument("--matlab-executed", action="store_true")
    parser.add_argument("--num-train-seeds", type=int, default=3)
    parser.add_argument("--num-test-seeds", type=int, default=1)
    parser.add_argument("--calibrated", action="store_true")
    parser.add_argument("--calibration-options-json", default=None)
    parser.add_argument("--degeneracy-check-json", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summarize_real_topk_dynamic_validation(
        args.precision_csv,
        args.overlap_csv,
        args.relay_security_summary_csv,
        args.output_dir,
        args.method,
        args.result_scope,
        args.run_status,
        args.smoke_mode,
        args.matlab_executed,
        args.num_train_seeds,
        args.num_test_seeds,
        args.calibrated,
        args.calibration_options_json,
        args.degeneracy_check_json,
    )


def _load_degeneracy_warning(path_text: str | None) -> bool:
    if not path_text:
        return False
    path = Path(path_text)
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(payload.get("degeneracy_warning", False))


def _scoped_summary_name(result_scope: str, suffix: str) -> str:
    if result_scope == "default_top20_preliminary_dynamic_smoke":
        return f"default_top20_dynamic_smoke_summary.{suffix}"
    if result_scope == "calibrated_top20_preliminary_dynamic_smoke":
        return f"calibrated_top20_dynamic_smoke_summary.{suffix}"
    return f"{result_scope}_summary.{suffix}"


if __name__ == "__main__":
    main()
