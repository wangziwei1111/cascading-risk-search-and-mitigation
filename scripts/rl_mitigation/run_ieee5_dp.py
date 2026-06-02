from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt

from ._bootstrap import add_src_to_path

ROOT = add_src_to_path()

from rl_mitigation.cases import make_ieee5_case
from rl_mitigation.dp.dfs_transition_builder import build_transition_counts, save_transition_counts
from rl_mitigation.dp.policy_iteration import policy_iteration


def draw_case(case: dict, out_path: Path, title: str, highlighted: list[int]):
    pts = {0: (0, 1), 1: (1, 1), 2: (0.2, 0), 3: (1.1, 0.05), 4: (0.6, -0.8)}
    plt.figure(figsize=(5, 4), facecolor="white")
    for i, (a, b) in enumerate(case["lines"]):
        x = [pts[a][0], pts[b][0]]
        y = [pts[a][1], pts[b][1]]
        plt.plot(x, y, lw=3 if i in highlighted else 1.5, color="#d62728" if i in highlighted else "#555555")
        plt.text(sum(x) / 2, sum(y) / 2, str(i), fontsize=8)
    for bus, (x, y) in pts.items():
        plt.scatter([x], [y], s=180, color="white", edgecolor="black", zorder=3)
        plt.text(x, y, str(bus), ha="center", va="center", zorder=4)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=200)
    plt.savefig(out_path.with_suffix(".pdf"))
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/ieee5_dp.yaml")
    args = parser.parse_args()
    case = make_ieee5_case()
    out = ROOT / "results" / "rl_mitigation" / "ieee5"
    out.mkdir(parents=True, exist_ok=True)
    counts = build_transition_counts(case)
    save_transition_counts(counts, str(out / "transition_counts.pkl"))
    result = policy_iteration(counts)
    with open(out / "dp_policy.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    draw_case(case, out / "fig_ieee5_cascade_without_mitigation.png", "IEEE5 cascade without mitigation", [0, 1, 3, 4, 6])
    draw_case(case, out / "fig_ieee5_cascade_with_mitigation.png", "IEEE5 cascade with mitigation", [0, 1, 5])
    draw_case(case, out / "fig_ieee5_transition_dfs.png", "IEEE5 DFS transition graph proxy", case["initial_outages"])
    print(f"IEEE5 DP artifacts written to {out}")


if __name__ == "__main__":
    main()
