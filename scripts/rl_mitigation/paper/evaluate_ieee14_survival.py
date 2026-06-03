from __future__ import annotations

import argparse
import csv

from ._common import ROOT, mode_suffix, normalize_mode
from rl_mitigation.plotting.plot_survival import plot_survival_by_policy


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-csv")
    parser.add_argument("--episodes", type=int, default=1000)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    args = parser.parse_args()
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    eval_csv = args.eval_csv or str(base / "eval" / f"eval_{args.episodes}_before_after.csv")
    rows = _read(eval_csv)
    figs = base / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    inferred = "medium" if "_medium" in str(eval_csv) else None
    mode = normalize_mode(args.mode or inferred, args.smoke or "_smoke" in str(eval_csv))
    suffix = mode_suffix(mode)
    paper_rows = [row for row in rows if row.get("policy") in {"do_nothing", "paper_proposed_policy"}]
    plot_survival_by_policy(
        paper_rows,
        str(figs / f"fig8_ieee14_negative_return_survival{suffix}.png"),
        str(figs / f"fig8_ieee14_negative_return_survival{suffix}.pdf"),
    )
    _write_survival_csv(paper_rows, figs / f"fig8_ieee14_negative_return_survival{suffix}.csv")
    print(f"Figure 8 written to {figs}")


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_survival_csv(rows, path):
    out = []
    for policy in sorted({row["policy"] for row in rows}):
        vals = sorted(float(row["negative_return"]) for row in rows if row["policy"] == policy)
        for idx, value in enumerate(vals):
            out.append({"policy": policy, "negative_return": value, "survival_probability": 1.0 - idx / len(vals)})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["policy", "negative_return", "survival_probability"])
        writer.writeheader()
        writer.writerows(out)


if __name__ == "__main__":
    main()
