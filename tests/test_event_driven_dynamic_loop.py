from __future__ import annotations

import json
from pathlib import Path
import sys

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from check_relay_security_demo_artifacts import check_relay_security_demo_artifacts


def test_mock_mild_and_severe_demo_summaries_pass(tmp_path: Path) -> None:
    mild = tmp_path / "mild_overload_summary.json"
    severe = tmp_path / "severe_overload_summary.json"
    mild.write_text(
        json.dumps(
            {
                "has_security_redispatch_or_load_shed": True,
                "has_passive_relay_trip": False,
                "max_loading_ratio": 1.05,
                "relay_beta": 1.2,
                "dynamic_load_shed_mw": 3.0,
            }
        ),
        encoding="utf-8",
    )
    severe.write_text(
        json.dumps(
            {
                "has_passive_relay_trip": True,
                "max_relay_violation_loading_ratio": 1.25,
                "relay_beta": 1.2,
                "passive_relay_trip_count": 1,
            }
        ),
        encoding="utf-8",
    )
    result = check_relay_security_demo_artifacts(mild, severe)
    assert result["status"] == "passed"


def test_demo_checker_can_skip_missing_matlab_outputs(tmp_path: Path) -> None:
    result = check_relay_security_demo_artifacts(
        tmp_path / "missing_mild.json",
        tmp_path / "missing_severe.json",
        allow_missing_matlab_results=True,
    )
    assert result["status"] == "skipped"
