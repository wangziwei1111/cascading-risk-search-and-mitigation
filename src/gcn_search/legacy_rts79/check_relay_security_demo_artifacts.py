from __future__ import annotations

import argparse
import json
from pathlib import Path


def check_relay_security_demo_artifacts(
    mild_summary: str | Path,
    severe_summary: str | Path,
    allow_missing_matlab_results: bool = False,
) -> dict:
    mild_path = Path(mild_summary)
    severe_path = Path(severe_summary)
    if allow_missing_matlab_results and (not mild_path.exists() or not severe_path.exists()):
        result = {"status": "skipped", "reason": "MATLAB demo summaries are missing."}
        print(json.dumps(result, indent=2))
        return result
    if not mild_path.exists():
        raise FileNotFoundError(f"Missing mild overload summary: {mild_path}")
    if not severe_path.exists():
        raise FileNotFoundError(f"Missing severe overload summary: {severe_path}")
    mild = json.loads(mild_path.read_text(encoding="utf-8-sig"))
    severe = json.loads(severe_path.read_text(encoding="utf-8-sig"))
    failures: list[str] = []
    if not mild.get("has_security_redispatch_or_load_shed", False):
        failures.append("Mild demo did not report security redispatch/load shedding.")
    if mild.get("has_passive_relay_trip", False):
        failures.append("Mild demo unexpectedly reported passive relay trip.")
    if not (float(mild.get("max_loading_ratio", 0.0)) > 1.0 and float(mild.get("max_loading_ratio", 0.0)) <= float(mild.get("relay_beta", 1.2))):
        failures.append("Mild demo max loading is not in (1.0, beta].")
    if float(mild.get("dynamic_load_shed_mw", 0.0)) <= 0.0:
        failures.append("Mild demo did not shed load.")
    if not severe.get("has_passive_relay_trip", False):
        failures.append("Severe demo did not report passive relay trip.")
    if not (float(severe.get("max_relay_violation_loading_ratio", 0.0)) > float(severe.get("relay_beta", 1.2))):
        failures.append("Severe demo relay violation is not above beta.")
    result = {"status": "passed" if not failures else "failed", "failures": failures}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check mild/severe relay-security MATLAB demo summaries.")
    parser.add_argument("--mild-summary", required=True)
    parser.add_argument("--severe-summary", required=True)
    parser.add_argument("--allow-missing-matlab-results", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    check_relay_security_demo_artifacts(args.mild_summary, args.severe_summary, args.allow_missing_matlab_results)


if __name__ == "__main__":
    main()
