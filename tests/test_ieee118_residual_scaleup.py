from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
IEEE118 = ROOT / "src" / "gcn_search" / "ieee118"
sys.path.insert(0, str(IEEE118))

from generate_ieee118_residual_scaleup_shards import (
    builder_command,
    paper_8000_shard_plan,
    run_shard,
    validate_plan,
)
from compare_ieee118_residual_scaleup import compare
from merge_ieee118_paper_gcn_shards import merge


FEATURE_NAMES = np.asarray(
    ["branch_status_offline", "relay_loading_ratio", "abs_flow", "max_terminal_load"],
    dtype=str,
)


def test_paper_8000_plan_is_exact_and_seed_separated() -> None:
    plan = paper_8000_shard_plan()
    validate_plan(plan)
    assert sum(spec.target_state_samples for spec in plan) == 8000
    assert sum(len(spec.seeds) for spec in plan if spec.split == "train") == 71
    assert sum(len(spec.seeds) for spec in plan if spec.split == "validation") == 8
    assert [spec.seeds for spec in plan if spec.split == "test"] == [(20260708,)]
    all_seeds = [seed for spec in plan for seed in spec.seeds]
    assert len(all_seeds) == len(set(all_seeds))


def test_shard_builder_command_keeps_test_seed_out_of_train(tmp_path: Path) -> None:
    spec = next(value for value in paper_8000_shard_plan() if value.split == "train")
    args = argparse.Namespace(
        python_executable=Path(sys.executable),
        output_root=tmp_path,
        sample_seed=20260712,
        checkpoint_every=25,
        resume=True,
    )
    command = builder_command(args, spec)
    train_start = command.index("--train-seeds") + 1
    validation_start = command.index("--validation-seeds")
    train_values = {int(value) for value in command[train_start:validation_start]}
    assert train_values == set(spec.seeds)
    assert 20260708 not in train_values
    assert "--resume" in command


def test_shard_run_rejects_successful_process_with_incomplete_sample_count(
    tmp_path: Path, monkeypatch
) -> None:
    spec = paper_8000_shard_plan()[0]
    output_dir = tmp_path / spec.name
    output_dir.mkdir(parents=True)
    (output_dir / "ieee118_paper_gcn_dataset_metadata.json").write_text(
        json.dumps({"num_state_samples": spec.target_state_samples - 1}),
        encoding="utf-8",
    )

    class Completed:
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Completed())
    result = run_shard(
        argparse.Namespace(
            python_executable=Path(sys.executable),
            output_root=tmp_path,
            sample_seed=20260712,
            checkpoint_every=25,
            resume=True,
        ),
        spec,
    )

    assert result["status"] == "failed"
    assert result["num_generated_state_samples"] == spec.target_state_samples - 1


def write_fake_shard(root: Path, name: str, seed: int, split: str, base: float) -> None:
    output = root / name
    output.mkdir(parents=True)
    x_raw = np.asarray(
        [
            [[base, base + 1, base + 2, base + 3], [base + 4, base + 5, base + 6, base + 7]],
            [[base + 1, base + 2, base + 3, base + 4], [base + 5, base + 6, base + 7, base + 8]],
        ],
        dtype=np.float32,
    )
    y = np.asarray([[0, 1], [1, 0]], dtype=np.int64)
    mask = np.ones((2, 2), dtype=bool)
    np.savez(
        output / "ieee118_paper_gcn_dataset.npz",
        x_gcn=x_raw.copy(),
        physics_raw_features=x_raw,
        y_gcn=y,
        y_critical=y.copy(),
        loss_mask=mask,
        seed=np.asarray([seed, seed], dtype=np.int64),
        split=np.asarray([split, split], dtype=str),
        sample_type=np.asarray(["S0", "S1"], dtype=str),
        active_first_line=np.asarray(["", "L001"], dtype=str),
        current_outage_labels=np.asarray(["", "L001"], dtype=str),
        line_labels=np.asarray(["L001", "L002"], dtype=str),
        branch_from_bus=np.asarray([1, 2], dtype=np.int64),
        branch_to_bus=np.asarray([2, 3], dtype=np.int64),
        feature_names=FEATURE_NAMES,
    )


def test_merge_refits_normalizer_on_train_only_and_preserves_splits(tmp_path: Path) -> None:
    input_root = tmp_path / "shards"
    write_fake_shard(input_root, "train_01", 101, "train", 1.0)
    write_fake_shard(input_root, "validation_01", 102, "validation", 100.0)
    write_fake_shard(input_root, "test_01", 20260708, "test", 200.0)
    output = tmp_path / "merged"
    metadata = merge(
        argparse.Namespace(
            input_root=input_root,
            output_dir=output,
            expected_state_samples=6,
        )
    )
    assert metadata["num_state_samples"] == 6
    assert metadata["train_seeds"] == [101]
    assert metadata["validation_seeds"] == [102]
    assert metadata["test_seeds"] == [20260708]
    assert metadata["num_s1_active_first_line_unknown"] == 0
    normalizer = json.loads((output / "ieee118_paper_gcn_feature_normalizer.json").read_text(encoding="utf-8"))
    assert normalizer["branch_status_offline"]["mean"] < 10.0
    merged = np.load(output / "ieee118_paper_gcn_dataset.npz", allow_pickle=True)
    assert merged["x_gcn"].shape == (6, 2, 4)
    assert set(merged["split"].astype(str)) == {"train", "validation", "test"}


def test_scaleup_large_artifacts_are_not_tracked() -> None:
    tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
    forbidden = [
        path
        for path in tracked
        if "ieee118_n1_residual_scaleup" in path
        and path.endswith((".npz", ".pt", "full_predictions.csv"))
    ]
    assert not forbidden


def write_fake_run(root: Path, state_samples: int, k90: int) -> None:
    training = root / "training_k6"
    evaluation = root / "eval_k6"
    training.mkdir(parents=True)
    evaluation.mkdir(parents=True)
    metrics = {
        "num_state_samples": state_samples,
        "num_train_state_samples": state_samples - 20,
        "num_validation_state_samples": 10,
        "num_test_state_samples": 10,
        "train_config": {"k_gcn": 6},
        "best_epoch": 3,
        "best_validation_average_precision": 0.4,
        "classification_metrics": {
            "test": {"average_precision": 0.3},
            "S0": {"average_precision": 0.8},
            "S1": {"average_precision": 0.2},
        },
    }
    (training / "ieee118_residual_reachable_gcn_k6_metrics.json").write_text(
        json.dumps(metrics), encoding="utf-8"
    )
    threshold_rows = []
    for method, offset in (
        ("N1_gate_plus_RTS79_residual_reachable_GCN_path_prob", 0),
        ("N1_gate_plus_RTS79_residual_reachable_GCN_second_only", -1),
    ):
        threshold_rows.append(
            {
                "method": method,
                "universe": "full",
                "K90": k90 + offset,
                "K95": k90 + 10 + offset,
                "K99": k90 + 20 + offset,
                "K100": k90 + 30 + offset,
                "total_physical_K90": k90 + 186 + offset,
                "total_physical_K95": k90 + 196 + offset,
                "total_physical_K99": k90 + 206 + offset,
                "total_physical_K100": k90 + 216 + offset,
            }
        )
    (evaluation / "ieee118_n1_gated_thresholds.json").write_text(
        json.dumps(threshold_rows), encoding="utf-8"
    )
    import pandas as pd

    pd.DataFrame(
        [
            {
                "method": row["method"],
                "K": 2000,
                "critical_hit_count": 100,
                "recall_critical": 0.5,
            }
            for row in threshold_rows
        ]
    ).to_csv(evaluation / "ieee118_n1_gated_search_summary.csv", index=False)


def test_scaleup_comparison_writes_pilot_and_paper8000_rows(tmp_path: Path) -> None:
    pilot = tmp_path / "pilot"
    scaleup = tmp_path / "scaleup"
    write_fake_run(pilot, 2000, 2000)
    write_fake_run(scaleup, 8000, 1800)
    result = compare(
        argparse.Namespace(
            pilot_root=pilot,
            scaleup_root=scaleup,
            output_dir=tmp_path / "compact",
        )
    )
    assert result["pilot_state_samples"] == 2000
    assert result["paper8000_state_samples"] == 8000
    assert result["path_prob_delta"]["total_physical_K90"] == -200
    assert (tmp_path / "compact" / "ieee118_paper8000_vs_pilot2000_thresholds.csv").exists()
    readme = (tmp_path / "compact" / "ieee118_paper8000_vs_pilot2000_readme.md").read_text(encoding="utf-8")
    assert "2,186" in readme
    assert "1,986" in readme
    assert "path_prob" in readme
