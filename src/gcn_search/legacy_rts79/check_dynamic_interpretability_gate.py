from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def check_dynamic_interpretability_gate(
    post_fault_sanity_csv: str | Path,
    negative_control_v3_csv: str | Path,
    output_dir: str | Path = "results/gcn_search/simulink_dynamic_interpretability_gate",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ladder = pd.read_csv(post_fault_sanity_csv)
    v3 = pd.read_csv(negative_control_v3_csv)
    no_trip_passed = _group_passed(ladder, "no_trip")
    single_mild_passed = _group_passed(ladder, "single_mild_trip")
    low_risk_not_all = _group_unstable(ladder, "low_risk_ordered_n2") < 1.0
    random_not_all = _group_unstable(ladder, "random_ordered_n2") < 1.0
    controls = v3[v3["group"].astype(str) != "learned_top20"]
    controls_have_variation = bool(not controls.empty and controls["unstable_fraction_post_fault_calibrated"].astype(float).nunique() > 1)
    if not controls.empty:
        controls_have_variation = controls_have_variation or bool((controls["unstable_fraction_post_fault_calibrated"].astype(float) < 1.0).any())
    default_interpretable = bool(no_trip_passed and controls_have_variation and low_risk_not_all and random_not_all)
    allowed_next_step = "expand_top50_top100" if default_interpretable else "continue_dynamic_calibration"
    summary = {
        "no_trip_passed": no_trip_passed,
        "single_mild_trip_passed": single_mild_passed,
        "low_risk_not_all_unstable": low_risk_not_all,
        "random_not_all_unstable": random_not_all,
        "controls_have_variation": controls_have_variation,
        "default_dynamic_precision_interpretable": default_interpretable,
        "allowed_next_step": allowed_next_step,
    }
    csv_path = out / "dynamic_interpretability_gate_summary.csv"
    json_path = out / "dynamic_interpretability_gate_summary.json"
    pd.DataFrame([summary]).to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def _group_passed(table: pd.DataFrame, group: str) -> bool:
    sub = table.loc[table["case_group"].astype(str) == group]
    if sub.empty:
        return False
    return str(sub["sanity_level_passed"].iloc[0]).lower() in {"true", "1", "yes"}


def _group_unstable(table: pd.DataFrame, group: str) -> float:
    sub = table.loc[table["case_group"].astype(str) == group]
    if sub.empty:
        return 1.0
    return float(sub["unstable_fraction"].iloc[0])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check whether dynamic Top-K precision is interpretable.")
    parser.add_argument("--post-fault-sanity-csv", required=True)
    parser.add_argument("--negative-control-v3-csv", required=True)
    parser.add_argument("--output-dir", default="results/gcn_search/simulink_dynamic_interpretability_gate")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_dynamic_interpretability_gate(args.post_fault_sanity_csv, args.negative_control_v3_csv, args.output_dir)


if __name__ == "__main__":
    main()
