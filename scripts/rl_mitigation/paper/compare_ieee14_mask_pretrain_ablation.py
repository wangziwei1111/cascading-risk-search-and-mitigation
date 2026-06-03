from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from ._common import ROOT


VARIANTS = [
    ("A_no_pretrain_no_mask", False, False),
    ("B_no_pretrain_mask", False, True),
    ("C_pretrain_no_mask", True, False),
    ("D_pretrain_mask_proposed", True, True),
]


def main() -> None:
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    eval_rows = _read_latest_eval(base / "eval")
    out_dir = base / "ablation"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for variant, use_pretrain, use_mask in VARIANTS:
        rows.append(_summary(variant, use_pretrain, use_mask, eval_rows))
    fields = list(rows[0])
    with open(out_dir / "mask_pretrain_ablation.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# IEEE14 Mask/Pretrain Ablation", "", "This table is a paper-method ablation scaffold. It excludes oracle BC and safe gate.", ""]
    lines.extend(f"- {row['variant']}: mean negative return `{row['mean_negative_return']:.4f}`" for row in rows)
    (out_dir / "mask_pretrain_ablation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"IEEE14 mask/pretrain ablation summary written to {out_dir}")


def _read_latest_eval(eval_dir: Path) -> list[dict]:
    files = sorted(eval_dir.glob("eval_*_before_after*.csv"))
    if not files:
        return []
    with open(files[-1], newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _summary(variant: str, use_pretrain: bool, use_mask: bool, rows: list[dict]) -> dict:
    proposed = [row for row in rows if row.get("policy") == "paper_proposed_policy"]
    use = proposed or rows
    def mean(key):
        return float(np.mean([float(row.get(key, 0.0)) for row in use])) if use else 0.0
    return {
        "variant": variant,
        "use_pretrain": use_pretrain,
        "use_mask": use_mask,
        "mean_episode_return": mean("episode_return"),
        "mean_negative_return": mean("negative_return"),
        "mean_num_invalid_actions": mean("num_invalid_actions"),
        "mean_num_proactive_actions": mean("num_proactive_actions"),
        "mean_num_generations": mean("num_generations"),
        "mean_num_line_outages": mean("num_line_outages"),
        "mean_load_shed_MW": mean("load_shed_MW"),
        "pf_failed_ratio": float(np.mean([str(row.get("pf_failed")).lower() == "true" for row in use])) if use else 0.0,
    }


if __name__ == "__main__":
    main()

