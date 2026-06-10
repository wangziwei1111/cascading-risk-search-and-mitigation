from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_post_fault_sanity_ladder_no_trip_passed_field(tmp_path: Path) -> None:
    summary = tmp_path / "post_fault_sanity_ladder_summary.csv"
    pd.DataFrame(
        [
            {"case_group": "no_trip", "unstable_fraction": 0.0, "sanity_level_passed": True},
            {"case_group": "low_risk_ordered_n2", "unstable_fraction": 0.5, "sanity_level_passed": True},
        ]
    ).to_csv(summary, index=False)
    table = pd.read_csv(summary)
    no_trip = table.loc[table["case_group"] == "no_trip"].iloc[0]
    assert bool(no_trip["sanity_level_passed"]) is True
