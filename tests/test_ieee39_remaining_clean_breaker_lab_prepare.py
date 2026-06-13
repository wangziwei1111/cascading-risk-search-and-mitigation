from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd


def test_remaining_clean_breaker_lab_prepare_summary_is_unwired_and_local_only() -> None:
    root = Path(__file__).resolve().parents[1]
    path = (
        root
        / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/"
        / "ieee39_clean_breaker_lab_remaining_prepare_summary.csv"
    )
    assert path.exists()
    table = pd.read_csv(path)
    expected_lines = {f"L{i:02d}" for i in range(11, 35)}
    assert set(table["line_id"].astype(str)) == expected_lines
    assert (table["status"].astype(str) == "prepared").all()
    for column in ["source_found", "target_created", "target_loadable"]:
        assert table[column].astype(str).str.lower().isin({"1", "true"}).all()
    for column in ["existing_handwired_breaker_found", "clean_lab_committed"]:
        assert table[column].astype(str).str.lower().isin({"0", "false"}).all()
    assert table["note"].astype(str).str.contains("no breaker was inserted", case=False).all()

    tracked = subprocess.run(
        ["git", "ls-files", "results/gcn_search/ieee39_graphical_dynamic_model/generated_models"],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.lower()
    for line_id in expected_lines:
        assert f"clean_breaker_lab_{line_id.lower()}.slx" not in tracked
