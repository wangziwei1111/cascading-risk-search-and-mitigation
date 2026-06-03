from __future__ import annotations

import argparse

from ._common import load_config, resolve_path
from rl_mitigation.cases import make_ieee14_case
from gcn_search.ieee14.branch_graph import build_branch_graph
from gcn_search.ieee14.risk_dataset import SPLITS, build_split_dataset, save_dataset, write_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/gcn_search/ieee14/ieee14_gcn.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    case = make_ieee14_case()
    out_dir = resolve_path(cfg["dataset"]["output_dir"])
    scan_dir = resolve_path(cfg["dataset"]["action_scan_dir"])
    split_counts = {}
    for split in SPLITS:
        csv_path = scan_dir / f"{split}_action_value_scan.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing same-system IEEE14 action scan: {csv_path}")
        dataset, rows = build_split_dataset(case, split, csv_path)
        save_dataset(dataset, rows, out_dir)
        split_counts[split] = int(len(rows))
    write_manifest(out_dir, build_branch_graph(case), cfg, split_counts)
    print(f"IEEE14 branch-GCN risk dataset written to {out_dir}")


if __name__ == "__main__":
    main()

