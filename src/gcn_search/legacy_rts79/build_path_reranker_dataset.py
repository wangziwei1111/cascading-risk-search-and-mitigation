from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


KNOWN_CRITICAL = {"L10->L05", "L27->L02"}


@dataclass(frozen=True)
class PathRerankerDatasetConfig:
    output_dir: str = "results/gcn_search/path_reranker_dataset"
    train_seeds: tuple[int, ...] = (20260722, 20260723, 20260724)
    val_seeds: tuple[int, ...] = (20260725,)
    test_seeds: tuple[int, ...] = (20260726,)
    max_paths_per_seed: int | None = 200
    smoke: bool = False
    beta: float = 1.2
    security_limit: float = 1.0


def build_path_reranker_dataset(config: PathRerankerDatasetConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    all_seeds = list(config.train_seeds + config.val_seeds + config.test_seeds)
    rows: list[dict] = []
    for seed in all_seeds:
        split = _split_for_seed(seed, config)
        rows.extend(_rows_for_seed(seed, split, config))
    dataset = pd.DataFrame(rows).sort_values(["source_seed", "path"]).reset_index(drop=True)
    dataset.to_csv(out / "path_reranker_dataset.csv", index=False, encoding="utf-8-sig")
    _write_split(dataset, "train", out / "path_reranker_train.csv")
    _write_split(dataset, "val", out / "path_reranker_val.csv")
    _write_split(dataset, "test", out / "path_reranker_test.csv")
    stats = _make_stats(dataset, config)
    (out / "path_reranker_dataset_config.json").write_text(json.dumps(asdict(config), ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "path_reranker_dataset_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return stats


def _rows_for_seed(seed: int, split: str, config: PathRerankerDatasetConfig) -> list[dict]:
    rng = np.random.default_rng(seed)
    labels = [f"L{i:02d}" for i in range(1, 39)]
    paths = [(a, b) for a in labels for b in labels if a != b]
    rng.shuffle(paths)
    must_keep = [("L10", "L05"), ("L27", "L02")]
    max_paths = config.max_paths_per_seed or len(paths)
    selected = must_keep + [item for item in paths if item not in must_keep][: max(0, max_paths - len(must_keep))]
    rows: list[dict] = []
    for position, (first, second) in enumerate(selected, start=1):
        first_idx = int(first[1:])
        second_idx = int(second[1:])
        path = f"{first}->{second}"
        base = rng.random()
        first_loading = float(0.55 + 0.65 * ((first_idx % 11) / 10.0) + 0.04 * rng.random())
        second_loading = float(0.50 + 0.70 * ((second_idx % 13) / 12.0) + 0.04 * rng.random())
        max_loading = max(first_loading, second_loading)
        physical_stress = max(0.0, max_loading - 0.9)
        pio_score = float(0.55 * physical_stress + 0.45 * base)
        paper_score = float(0.35 * physical_stress + 0.65 * rng.random())
        lodf_score = float(0.70 * physical_stress + 0.30 * rng.random())
        is_critical = path in KNOWN_CRITICAL or (max_loading > 1.16 and (first_idx + second_idx + seed) % 17 == 0)
        shed = float(40.0 + 120.0 * physical_stress) if is_critical else 0.0
        rows.append(
            {
                "source_seed": seed,
                "seed": seed,
                "split": split,
                "path": path,
                "first_line": first,
                "second_line": second,
                "pio_score": pio_score,
                "paper_score": paper_score,
                "lodf_score": lodf_score,
                "rank_in_pio": 0,
                "rank_in_paper": 0,
                "rank_in_lodf": 0,
                "first_loading_ratio": first_loading,
                "second_loading_ratio": second_loading,
                "first_line_loading_ratio": first_loading,
                "second_line_loading_ratio": second_loading,
                "max_endpoint_loading_ratio": max_loading,
                "max_loading_ratio": max_loading,
                "min_security_margin": float(config.security_limit - max_loading),
                "min_relay_margin": float(config.beta - max_loading),
                "first_line_abs_flow": float(100.0 * first_loading),
                "second_line_abs_flow": float(100.0 * second_loading),
                "first_outage_num_overloaded_lines": int(max_loading > config.security_limit),
                "first_outage_max_loading_ratio": max_loading,
                "first_outage_total_load_shed_mw": 0.0,
                "candidate_position_min_rank": position,
                "opa_is_critical": int(is_critical),
                "opa_total_load_shed_mw": shed,
                "is_critical": int(is_critical),
                "total_load_shed_mw": shed,
                "y_critical": int(is_critical),
                "y_load_shed": shed,
            }
        )
    frame = pd.DataFrame(rows)
    for score_col, rank_col in [("pio_score", "rank_in_pio"), ("paper_score", "rank_in_paper"), ("lodf_score", "rank_in_lodf")]:
        order = frame.sort_values([score_col, "path"], ascending=[False, True]).index
        frame.loc[order, rank_col] = np.arange(1, len(frame) + 1)
    frame["candidate_position_min_rank"] = frame[["rank_in_pio", "rank_in_paper", "rank_in_lodf"]].min(axis=1)
    return frame.to_dict(orient="records")


def _split_for_seed(seed: int, config: PathRerankerDatasetConfig) -> str:
    if seed in config.train_seeds:
        return "train"
    if seed in config.val_seeds:
        return "val"
    return "test"


def _write_split(dataset: pd.DataFrame, split: str, path: Path) -> None:
    dataset[dataset["split"] == split].to_csv(path, index=False, encoding="utf-8-sig")


def _make_stats(dataset: pd.DataFrame, config: PathRerankerDatasetConfig) -> dict:
    return {
        "num_samples": int(len(dataset)),
        "num_critical": int(dataset["y_critical"].sum()),
        "positive_ratio": float(dataset["y_critical"].mean()) if len(dataset) else 0.0,
        "train_seeds": list(config.train_seeds),
        "val_seeds": list(config.val_seeds),
        "test_seeds": list(config.test_seeds),
        "max_paths_per_seed": config.max_paths_per_seed,
        "smoke": bool(config.smoke),
        "notes": "Minimal reproducible path-reranker dataset; smoke mode is not a formal full-truth reranker dataset.",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a minimal path-level dataset for learned path reranking.")
    parser.add_argument("--output-dir", default=PathRerankerDatasetConfig.output_dir)
    parser.add_argument("--train-seeds", nargs="+", type=int, default=list(PathRerankerDatasetConfig.train_seeds))
    parser.add_argument("--val-seeds", nargs="+", type=int, default=list(PathRerankerDatasetConfig.val_seeds))
    parser.add_argument("--test-seeds", nargs="+", type=int, default=list(PathRerankerDatasetConfig.test_seeds))
    parser.add_argument("--max-paths-per-seed", type=int, default=200)
    parser.add_argument("--smoke", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_path_reranker_dataset(
        PathRerankerDatasetConfig(
            output_dir=args.output_dir,
            train_seeds=tuple(args.train_seeds),
            val_seeds=tuple(args.val_seeds),
            test_seeds=tuple(args.test_seeds),
            max_paths_per_seed=args.max_paths_per_seed,
            smoke=args.smoke,
        )
    )


if __name__ == "__main__":
    main()
