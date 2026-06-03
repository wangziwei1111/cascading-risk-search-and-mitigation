import json
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import torch

LEGACY = Path(__file__).resolve().parents[1] / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from evaluate_rts79_pio_gcn_topk import PioTopkConfig, evaluate_pio_gcn_topk
from rts79_cascade import run_initial_dcopf
from train_rts79_paper_gcn import PaperGcnTrainConfig, PaperStyleRts79Gcn, _build_adjacency_powers, _build_branch_graph_adjacency


def test_measured_state_example_is_used_consistently_in_topk_outputs(tmp_path):
    state = run_initial_dcopf()
    model = PaperStyleRts79Gcn(9, PaperGcnTrainConfig())
    adjacency = _build_branch_graph_adjacency(state.case)
    checkpoint = {
        "train_config": asdict(PaperGcnTrainConfig()),
        "model_state_dict": model.state_dict(),
        "adjacency_powers": _build_adjacency_powers(adjacency, 3),
    }
    model_path = tmp_path / "model.pt"
    torch.save(checkpoint, model_path)

    normalizer = {
        name: {"mean": 0.0, "std": 1.0}
        for name in [
            "branch_status_offline",
            "relay_loading_ratio",
            "abs_flow",
            "max_terminal_load",
            "loading_ratio",
            "security_margin",
            "relay_margin",
            "is_online",
            "is_candidate",
        ]
    }
    normalizer_path = tmp_path / "normalizer.json"
    normalizer_path.write_text(json.dumps(normalizer), encoding="utf-8")
    output_dir = tmp_path / "measured_eval"

    evaluate_pio_gcn_topk(
        PioTopkConfig(
            model=str(model_path),
            normalizer=str(normalizer_path),
            output_dir=str(output_dir),
            measured_state_json=str(Path(__file__).resolve().parents[1] / "examples" / "rts79_measured_state_example.json"),
            top_k=(20,),
            max_paths_for_smoke_test=20,
        )
    )

    order = pd.read_csv(output_dir / "pio_gcn_topk_order.csv")
    assert not order.empty
    assert all("L03" not in str(path).split("->") for path in order["path"])
    assert all("L03" in str(value) for value in order["initial_offline_lines"])
    assert all(value == "measured_state_updated_case" for value in order["simulation_initial_source"])

    simulation = pd.read_csv(output_dir / "pio_gcn_topk_simulation_results.csv")
    assert not simulation.empty
    assert all("L03" in str(value).split(",") for value in simulation["final_outage_labels"])
    assert all(value == "measured_state_updated_case" for value in simulation["simulation_initial_source"])

    online_summary = json.loads((output_dir / "online_state_summary.json").read_text(encoding="utf-8"))
    assert online_summary["used_measured_state"] is True
    assert online_summary["initial_offline_lines"] == ["L03"]
    assert online_summary["num_offline_lines"] == 1
