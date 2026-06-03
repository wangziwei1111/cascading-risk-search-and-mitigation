import json
import sys
from pathlib import Path

import numpy as np
import torch

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, _make_path_order
from gcn_physics_constraints import make_candidate_mask
from online_state_update import apply_measured_state_to_case, load_measured_state_json
from pypower.idx_brch import BR_STATUS
from rts79_cascade import run_initial_dcopf
from rts79_cascade_from_case import simulate_cascade_path_from_case
from train_rts79_paper_gcn import PaperGcnTrainConfig, PaperStyleRts79Gcn, _build_adjacency_powers, _build_branch_graph_adjacency


def test_measured_offline_line_is_excluded_from_topk_order(tmp_path):
    state = run_initial_dcopf()
    measured_path = tmp_path / "measured.json"
    measured_path.write_text(json.dumps({"branch_status": {"L03": 0}}), encoding="utf-8")
    measured = load_measured_state_json(measured_path)
    root_case = apply_measured_state_to_case(state.case, measured)
    assert root_case["branch"][2, BR_STATUS] == 0
    assert not make_candidate_mask(root_case)[2]

    model = PaperStyleRts79Gcn(9, PaperGcnTrainConfig())
    adjacency = _build_branch_graph_adjacency(root_case)
    adjacency_powers = torch.tensor(_build_adjacency_powers(adjacency, 3), dtype=torch.float32)
    normalizer = {name: {"mean": 0.0, "std": 1.0} for name in [
        "branch_status_offline",
        "relay_loading_ratio",
        "abs_flow",
        "max_terminal_load",
        "loading_ratio",
        "security_margin",
        "relay_margin",
        "is_online",
        "is_candidate",
    ]}
    order = _make_path_order(model, adjacency_powers, normalizer, root_case, PioTopkConfig(model="", normalizer="", output_dir=""))
    assert order
    assert all("L03" not in row["path"].split("->") for row in order[:50])


def test_simulation_from_case_preserves_initial_offline_line():
    state = run_initial_dcopf()
    root_case = apply_measured_state_to_case(
        state.case,
        load_measured_state_json(Path(__file__).resolve().parents[1] / "examples" / "rts79_measured_state_example.json"),
    )
    result = simulate_cascade_path_from_case(root_case, ["L01", "L02"], beta=1.2, security_limit=1.0)
    assert "L03" in result.final_outage_labels
