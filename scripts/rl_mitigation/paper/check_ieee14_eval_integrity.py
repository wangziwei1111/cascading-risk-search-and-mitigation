from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ._common import ROOT, mode_suffix, normalize_mode, rel


REQUIRED_POLICIES = {"do_nothing", "paper_proposed_policy"}
REQUIRED_FIELDS = {
    "negative_return", "num_generations", "num_line_outages", "load_shed_MW",
    "pf_failed", "num_invalid_actions", "num_proactive_actions",
}
MATCH_FIELDS = {"initial_outages", "initial_outage_type", "chronic_index", "load_scale", "gen_scale"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-csv", default="results/rl_mitigation/paper/ieee14/eval/eval_100_before_after_smoke.csv")
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    parser.add_argument("--suffix", choices=["smoke", "medium", "formal"])
    args = parser.parse_args()
    inferred = "medium" if "_medium" in args.eval_csv else None
    mode = normalize_mode(args.suffix or args.mode or inferred, "_smoke" in args.eval_csv)
    path = Path(args.eval_csv)
    if not path.is_absolute():
        path = ROOT / path
    rows = _read(path)
    result = check_rows(rows)
    result["source_eval_csv"] = rel(path)
    out = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"ieee14_eval_integrity_check{mode_suffix(mode)}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "ieee14_eval_integrity_check.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if not result["passed"]:
        raise SystemExit(f"IEEE14 eval integrity failed: {result['errors'][:3]}")
    print(f"IEEE14 eval integrity check written to {out}")


def check_rows(rows: list[dict]) -> dict:
    errors = []
    missing_fields = sorted(field for field in REQUIRED_FIELDS if any(field not in row for row in rows))
    if missing_fields:
        errors.append({"type": "missing_fields", "fields": missing_fields})
    by_scenario: dict[str, list[dict]] = {}
    for row in rows:
        by_scenario.setdefault(str(row.get("scenario_id")), []).append(row)
    for scenario_id, cur in by_scenario.items():
        policies = {row.get("policy") for row in cur}
        missing = sorted(REQUIRED_POLICIES - policies)
        if missing:
            errors.append({"type": "missing_policy", "scenario_id": scenario_id, "missing": missing})
            continue
        ref = next(row for row in cur if row.get("policy") == "do_nothing")
        for row in cur:
            if row.get("policy") not in REQUIRED_POLICIES:
                continue
            mismatched = [field for field in MATCH_FIELDS if str(row.get(field)) != str(ref.get(field))]
            if mismatched:
                errors.append({"type": "scenario_mismatch", "scenario_id": scenario_id, "policy": row.get("policy"), "fields": mismatched})
    return {
        "passed": not errors,
        "num_rows": len(rows),
        "num_scenarios": len(by_scenario),
        "required_policies": sorted(REQUIRED_POLICIES),
        "errors": errors,
    }


def _read(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


if __name__ == "__main__":
    main()
