from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))

from case_adapter import search_ordered_n2_paths_for_case


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an IEEE 118 ordered N-2 cascade smoke test.")
    parser.add_argument("--num-paths", type=int, default=100, help="Number of sampled ordered N-2 paths.")
    parser.add_argument("--seed", type=int, default=20260708, help="Random seed for path sampling.")
    parser.add_argument("--beta", type=float, default=1.2, help="Relay overload threshold multiplier.")
    parser.add_argument("--security-limit", type=float, default=1.0, help="Redispatch branch security limit multiplier.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_smoke",
        help="Directory for smoke-test outputs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    path_table = search_ordered_n2_paths_for_case(
        "ieee118",
        num_paths=args.num_paths,
        seed=args.seed,
        beta=args.beta,
        security_limit=args.security_limit,
    )
    output_csv = args.output_dir / "ieee118_ordered_n2_smoke_paths.csv"
    output_config = args.output_dir / "ieee118_ordered_n2_smoke_config.json"
    path_table.to_csv(output_csv, index=False, encoding="utf-8-sig")
    output_config.write_text(
        json.dumps(
            {
                "case_name": "ieee118",
                "num_paths": args.num_paths,
                "seed": args.seed,
                "beta": args.beta,
                "security_limit": args.security_limit,
                "output_csv": str(output_csv),
                "num_converged": int(path_table["converged"].sum()) if "converged" in path_table else 0,
                "num_critical": int(path_table["critical"].sum()) if "critical" in path_table else 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"IEEE 118 ordered N-2 smoke paths written to {output_csv}")
    print(f"num_paths={len(path_table)}")
    print(f"num_converged={int(path_table['converged'].sum())}")
    print(f"num_critical={int(path_table['critical'].sum())}")


if __name__ == "__main__":
    main()
