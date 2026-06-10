from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def compute_dynamic_stress_score(
    dynamic_results_csv: str | Path,
    output_csv: str | Path,
    load_shed_normalizer_mw: float | None = None,
) -> pd.DataFrame:
    table = pd.read_csv(dynamic_results_csv)
    shed = pd.to_numeric(table.get("dynamic_load_shed_mw", 0.0), errors="coerce").fillna(0.0)
    normalizer = load_shed_normalizer_mw or max(float(shed.max()), 1.0)
    freq = pd.to_numeric(table.get("frequency_nadir_hz", 50.0), errors="coerce").fillna(50.0)
    angle = pd.to_numeric(table.get("max_rotor_angle_separation_deg", 0.0), errors="coerce").fillna(0.0)
    loading = pd.to_numeric(table.get("max_line_loading_ratio", 0.0), errors="coerce").fillna(0.0)
    relay = pd.to_numeric(table.get("passive_relay_trip_count", 0.0), errors="coerce").fillna(0.0)
    score = (
        (49.5 - freq).clip(lower=0.0)
        + (angle / 180.0 - 1.0).clip(lower=0.0)
        + (loading - 1.0).clip(lower=0.0)
        + shed / normalizer
        + relay
    )
    result = table.copy()
    result["dynamic_stress_score"] = score
    result["stress_rank"] = result["dynamic_stress_score"].rank(method="first", ascending=False).astype(int)
    result["stress_reason"] = [
        _stress_reason(f, a, l, s, r) for f, a, l, s, r in zip(freq, angle, loading, shed, relay)
    ]
    result = result.sort_values("stress_rank")
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result


def _stress_reason(freq: float, angle: float, loading: float, shed: float, relay: float) -> str:
    reasons = []
    if freq < 49.5:
        reasons.append("low_frequency")
    if angle > 180.0:
        reasons.append("large_rotor_angle")
    if loading > 1.0:
        reasons.append("line_loading")
    if shed > 0:
        reasons.append("load_shed")
    if relay > 0:
        reasons.append("passive_relay")
    return ";".join(reasons) if reasons else "low_stress"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute continuous dynamic stress score for simulated cases.")
    parser.add_argument("--dynamic-results-csv", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--load-shed-normalizer-mw", type=float, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    compute_dynamic_stress_score(args.dynamic_results_csv, args.output_csv, args.load_shed_normalizer_mw)


if __name__ == "__main__":
    main()
