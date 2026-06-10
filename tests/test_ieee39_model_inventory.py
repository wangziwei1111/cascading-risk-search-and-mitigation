from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
legacy_dir = repo_root / "src" / "gcn_search" / "legacy_rts79"
if str(legacy_dir) not in sys.path:
    sys.path.insert(0, str(legacy_dir))

from inventory_ieee39_simulink_models import inventory_ieee39_simulink_models


def test_ieee39_model_inventory_schema(tmp_path: Path) -> None:
    root = tmp_path / "IEEE39BusSystemExample"
    root.mkdir()
    model = root / "IEEE39BusSystem.slx"
    model.write_text("placeholder", encoding="utf-8")
    result = inventory_ieee39_simulink_models([root], tmp_path / "out", [model])
    table = pd.read_csv(result["csv"])
    required = {
        "model_path",
        "model_name",
        "is_slx_or_mdl",
        "can_open_in_matlab",
        "requires_toolboxes",
        "contains_generators",
        "contains_exciters",
        "contains_governors",
        "contains_breakers",
        "contains_lines",
        "contains_loads",
        "contains_measurements",
        "contains_protection",
        "likely_model_type",
        "license_or_source_note",
    }
    assert required.issubset(table.columns)
    assert len(table) == 1
    assert bool(table.loc[0, "can_open_in_matlab"])
    assert table.loc[0, "likely_model_type"] == "phasor_RMS"
