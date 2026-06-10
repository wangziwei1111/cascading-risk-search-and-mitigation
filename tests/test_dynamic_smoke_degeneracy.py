from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from analyze_dynamic_smoke_degeneracy import analyze_dynamic_smoke_degeneracy


def _write_inputs(tmp_path: Path, precision: float, passive_cases: int, security_cases: int, num_cases: int = 20) -> tuple[Path, Path, Path]:
    summary = tmp_path / "summary.csv"
    relay = tmp_path / "relay.csv"
    dynamic = tmp_path / "dynamic.csv"
    pd.DataFrame(
        [
            {
                "top_k": 20,
                "num_dynamic_cases": num_cases,
                "num_simulated": num_cases,
                "dynamic_precision_at_k": precision,
                "opa_critical_and_dynamic_unstable_count": 1,
                "opa_noncritical_but_dynamic_unstable_count": int(precision * num_cases) - 1 if precision > 0 else 0,
            }
        ]
    ).to_csv(summary, index=False)
    pd.DataFrame(
        [
            {"metric": "cases_with_passive_relay_trip", "value": passive_cases},
            {"metric": "cases_with_security_redispatch_or_load_shed", "value": security_cases},
        ]
    ).to_csv(relay, index=False)
    pd.DataFrame([{"case_id": f"case_{idx}", "dynamic_unstable": idx <= int(precision * num_cases)} for idx in range(1, num_cases + 1)]).to_csv(dynamic, index=False)
    return summary, relay, dynamic


def test_all_unstable_and_all_passive_warns(tmp_path: Path) -> None:
    summary, relay, dynamic = _write_inputs(tmp_path, precision=1.0, passive_cases=20, security_cases=0)
    result = analyze_dynamic_smoke_degeneracy(summary, relay, dynamic, tmp_path / "out")
    assert result["degeneracy_warning"] is True
    assert result["all_cases_dynamic_unstable"] is True
    assert result["all_cases_passive_relay_trip"] is True


def test_zero_precision_warns(tmp_path: Path) -> None:
    summary, relay, dynamic = _write_inputs(tmp_path, precision=0.0, passive_cases=0, security_cases=0)
    result = analyze_dynamic_smoke_degeneracy(summary, relay, dynamic, tmp_path / "out")
    assert result["degeneracy_warning"] is True
    assert result["dynamic_precision_at_k"] == 0.0
