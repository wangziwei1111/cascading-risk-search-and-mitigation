from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/gcn_search/ieee39_dynamic_fault_type_expansion"


def test_prepare_script_regenerates_dry_run_commands() -> None:
    subprocess.run(
        ["python", "scripts/gcn_search/prepare_ieee39_non_line_trip_fault_expansion.py"],
        cwd=ROOT,
        check=True,
    )
    dry_run = OUT / "ieee39_non_line_trip_dry_run_commands.txt"
    assert dry_run.exists()
    text = dry_run.read_text(encoding="utf-8")
    assert "Dry-run command plan only" in text
    assert "NF01" in text
    assert "NF02" in text
    assert "NF06" in text
    assert "manual_required" in text


def test_dry_run_commands_do_not_batch_execute_or_touch_line_trip_labels() -> None:
    text = (OUT / "ieee39_non_line_trip_dry_run_commands.txt").read_text(encoding="utf-8").lower()
    assert "do not execute automatically" in text
    assert "l12" not in text
    assert "handwired_timed_breaker" not in text
    assert "single_line_trip" not in text
    assert "run_ieee39_multi_handwired" not in text
    assert "run_ieee39_clean_breaker_lab_line_trip" not in text
