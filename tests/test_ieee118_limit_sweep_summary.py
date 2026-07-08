import subprocess
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "gcn_search" / "ieee118" / "summarize_ieee118_limit_sweep.py"


def test_ieee118_limit_sweep_summary_outputs_required_fields(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--scales",
            "2.00",
            "2.50",
            "--output-dir",
            str(tmp_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr

    summary_path = tmp_path / "ieee118_flow_scaled_wide_scale_sweep.csv"
    json_path = tmp_path / "ieee118_flow_scaled_wide_scale_sweep.json"
    assert summary_path.exists()
    assert json_path.exists()

    table = pd.read_csv(summary_path)
    required = {
        "scale",
        "total_rows",
        "converged_rows",
        "error_rows",
        "critical_rows",
        "critical_ratio",
        "relay_cascade_rows",
        "relay_cascade_ratio",
        "island_only_rows",
        "redispatch_shed_rows",
        "mixed_rows",
        "max_event_loading_ratio",
        "max_pre_redispatch_loading_ratio",
        "total_relay_trips",
        "max_relay_trips_per_path",
        "mean_total_load_shed_mw",
        "p95_total_load_shed_mw",
        "max_total_load_shed_mw",
    }
    assert required.issubset(table.columns)
    assert set(pd.to_numeric(table["scale"]).round(2)) == {2.00, 2.50}
    assert (table["total_rows"] == 500).all()
    assert (table["converged_rows"] == 500).all()
    assert (table["error_rows"] == 0).all()
    assert (table["relay_cascade_rows"] > 0).all()
    assert table["critical_ratio"].between(0.0, 1.0).all()
    assert table["relay_cascade_ratio"].between(0.0, 1.0).all()
