from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BUILDER = Path(__file__).resolve().with_name("build_ieee118_paper_gcn_training_dataset.py")
DEFAULT_OUTPUT = ROOT / "results" / "gcn_search" / "ieee118_n1_residual_scaleup" / "paper_8000_shards"


@dataclass(frozen=True)
class ShardSpec:
    name: str
    split: str
    seeds: tuple[int, ...]
    target_state_samples: int
    samples_per_scenario: int


def paper_8000_shard_plan() -> list[ShardSpec]:
    train_seeds = (
        [20260800 + day for day in range(1, 32)]
        + [20260900 + day for day in range(1, 31)]
        + [20261000 + day for day in range(1, 11)]
    )
    plan = [
        ShardSpec(
            name=f"train_{idx + 1:02d}",
            split="train",
            seeds=tuple(train_seeds[idx * 10 : (idx + 1) * 10]),
            target_state_samples=1010,
            samples_per_scenario=100,
        )
        for idx in range(7)
    ]
    plan.extend(
        [
            ShardSpec(
                name="train_08_partial",
                split="train",
                seeds=(train_seeds[70],),
                target_state_samples=21,
                samples_per_scenario=20,
            ),
            ShardSpec(
                name="validation_01",
                split="validation",
                seeds=tuple(20261100 + day for day in range(1, 9)),
                target_state_samples=808,
                samples_per_scenario=100,
            ),
            ShardSpec(
                name="test_01",
                split="test",
                seeds=(20260708,),
                target_state_samples=101,
                samples_per_scenario=100,
            ),
        ]
    )
    return plan


def validate_plan(plan: list[ShardSpec]) -> None:
    if sum(spec.target_state_samples for spec in plan) != 8000:
        raise ValueError("Paper-8000 shard plan must contain exactly 8,000 state samples.")
    seen: set[int] = set()
    for spec in plan:
        overlap = seen & set(spec.seeds)
        if overlap:
            raise ValueError(f"Seeds appear in multiple shards: {sorted(overlap)}")
        seen.update(spec.seeds)
    if 20260708 not in {seed for spec in plan if spec.split == "test" for seed in spec.seeds}:
        raise ValueError("Held-out seed 20260708 must be assigned to the test shard.")
    if any(20260708 in spec.seeds for spec in plan if spec.split != "test"):
        raise ValueError("Held-out seed 20260708 leaked outside the test shard.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the formal IEEE118 paper-8000 dataset in resumable seed shards.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--python-executable", type=Path, default=Path(sys.executable))
    parser.add_argument("--num-workers", type=int, default=min(8, max(1, (os.cpu_count() or 2) // 2)))
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument("--sample-seed", type=int, default=20260712)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-shards", type=int, default=None)
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def builder_command(args: argparse.Namespace, spec: ShardSpec) -> list[str]:
    command = [
        str(args.python_executable),
        str(BUILDER),
        "--seeds",
        *[str(value) for value in spec.seeds],
        "--samples-per-scenario",
        str(spec.samples_per_scenario),
        "--target-state-samples",
        str(spec.target_state_samples),
        "--load-scale",
        "1.1",
        "--load-random-low",
        "0.9",
        "--load-random-high",
        "1.1",
        "--limit-mode",
        "flow_scaled",
        "--flow-limit-scale",
        "8.0",
        "--min-rate-a",
        "1.0",
        "--beta",
        "1.2",
        "--security-limit",
        "1.0",
        "--first-step-critical-policy",
        "skip",
        "--feature-mode",
        "paper",
        "--sample-seed",
        str(args.sample_seed),
        "--checkpoint-every",
        str(args.checkpoint_every),
        "--train-seeds",
        *([str(value) for value in spec.seeds] if spec.split == "train" else []),
        "--validation-seeds",
        *([str(value) for value in spec.seeds] if spec.split == "validation" else []),
        "--test-seeds",
        *([str(value) for value in spec.seeds] if spec.split == "test" else ["20260708"]),
        "--output-dir",
        str(args.output_root / spec.name),
    ]
    if args.resume:
        command.append("--resume")
    return command


def run_shard(args: argparse.Namespace, spec: ShardSpec) -> dict[str, Any]:
    output_dir = args.output_root / spec.name
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "generation_stdout.log"
    stderr_path = output_dir / "generation_stderr.log"
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONUNBUFFERED": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
        }
    )
    command = builder_command(args, spec)
    with stdout_path.open("a", encoding="utf-8") as stdout, stderr_path.open("a", encoding="utf-8") as stderr:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=stdout,
            stderr=stderr,
            text=True,
            check=False,
            env=environment,
        )
    metadata_path = output_dir / "ieee118_paper_gcn_dataset_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    num_generated = int(metadata.get("num_state_samples", 0))
    complete = completed.returncode == 0 and num_generated == spec.target_state_samples
    return {
        **asdict(spec),
        "seeds": list(spec.seeds),
        "returncode": int(completed.returncode),
        "status": "complete" if complete else "failed",
        "num_generated_state_samples": num_generated,
        "stdout_log": str(stdout_path),
        "stderr_log": str(stderr_path),
        "command": command,
    }


def write_summary(output_root: Path, rows: list[dict[str, Any]], expected_num_shards: int) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    all_reported = len(rows) == expected_num_shards
    summary = {
        "status": (
            "complete"
            if all_reported and all(row["status"] == "complete" for row in rows)
            else "partial_or_failed"
        ),
        "target_state_samples": 8000,
        "num_shards_planned": int(expected_num_shards),
        "num_shards_reported": len(rows),
        "num_complete_shards": sum(row["status"] == "complete" for row in rows),
        "num_generated_state_samples": sum(int(row["num_generated_state_samples"]) for row in rows),
        "shards": sorted(rows, key=lambda row: row["name"]),
    }
    (output_root / "paper_8000_shard_generation_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def generate(args: argparse.Namespace) -> dict[str, Any]:
    plan = paper_8000_shard_plan()
    validate_plan(plan)
    if args.max_shards is not None:
        plan = plan[: max(0, int(args.max_shards))]
    args.output_root.mkdir(parents=True, exist_ok=True)
    plan_payload = {
        "target_state_samples": 8000,
        "planned_state_samples": sum(spec.target_state_samples for spec in plan),
        "num_workers": int(args.num_workers),
        "resume": bool(args.resume),
        "shards": [{**asdict(spec), "seeds": list(spec.seeds)} for spec in plan],
    }
    (args.output_root / "paper_8000_shard_plan.json").write_text(json.dumps(plan_payload, indent=2), encoding="utf-8")
    if args.plan_only:
        return {"status": "plan_only", **plan_payload}
    if args.num_workers < 1:
        raise ValueError("--num-workers must be positive.")

    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(args.num_workers, max(len(plan), 1))) as executor:
        futures = {executor.submit(run_shard, args, spec): spec for spec in plan}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            write_summary(args.output_root, rows, len(plan))
            print(
                f"[paper-8000-shards] {row['name']} status={row['status']} "
                f"states={row['num_generated_state_samples']}/{row['target_state_samples']}",
                flush=True,
            )
    write_summary(args.output_root, rows, len(plan))
    failures = [row for row in rows if row["status"] != "complete"]
    if failures:
        raise RuntimeError(f"{len(failures)} paper-8000 shards failed; inspect per-shard stderr logs and rerun --resume.")
    return json.loads((args.output_root / "paper_8000_shard_generation_summary.json").read_text(encoding="utf-8"))


def main() -> None:
    args = parse_args()
    print(json.dumps(generate(args), indent=2))


if __name__ == "__main__":
    main()
