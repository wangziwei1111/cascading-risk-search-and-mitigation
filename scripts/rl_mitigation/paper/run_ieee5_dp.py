from __future__ import annotations

import argparse
import json
import pickle

import matplotlib.pyplot as plt

from ._common import ROOT, load_config
from rl_mitigation.cases import make_ieee5_case
from rl_mitigation.dp.dfs_transition_builder import build_transition_counts
from rl_mitigation.dp.policy_iteration import policy_iteration, transition_probabilities


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl_mitigation/paper/ieee5_dp.yaml")
    args = parser.parse_args()
    cfg = load_config(args.config)
    case = make_ieee5_case()
    case["initial_outages"] = [int(x) for x in cfg.get("initial_outages", [0, 3])]
    out = ROOT / "results" / "rl_mitigation" / "paper" / "ieee5"
    out.mkdir(parents=True, exist_ok=True)
    counts = build_transition_counts(case, max_depth=cfg.get("max_depth", 4))
    with open(out / "transition_counts.pkl", "wb") as f:
        pickle.dump(counts, f)
    probs = transition_probabilities(counts)
    probs_json = {f"{state}|{action}": [{"next_state": sp, "reward": r, "probability": p} for sp, r, p in rows] for (state, action), rows in probs.items()}
    (out / "transition_probabilities.json").write_text(json.dumps(probs_json, indent=2), encoding="utf-8")
    result = policy_iteration(counts)
    (out / "dp_policy.json").write_text(json.dumps(result["policy"], indent=2), encoding="utf-8")
    (out / "dp_value_function.json").write_text(json.dumps(result["values"], indent=2), encoding="utf-8")
    _draw_case(case, out / "fig2_ieee5_without_mitigation.png", "Figure 2 IEEE5 without mitigation", [0, 3, 4, 6])
    _draw_case(case, out / "fig3_ieee5_with_mitigation.png", "Figure 3 IEEE5 with mitigation", [0, 3])
    report = [
        "# IEEE5 DP Paper Example",
        "",
        "This is a mechanism reproduction of the paper IEEE5 DP example.",
        "The repository does not claim numerical identity with the paper because the exact IEEE5 parameters are not available.",
        "",
        f"States enumerated: {len(result['values'])}",
        f"State-action pairs: {len(counts)}",
        "Initial outages use paper-style line 1 and line 4 under zero-based indices `[0, 3]`.",
    ]
    (out / "ieee5_dp_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"IEEE5 DP paper artifacts written to {out}")


def _draw_case(case: dict, out_png, title: str, highlighted: list[int]) -> None:
    pts = {0: (0, 1), 1: (1, 1), 2: (0.2, 0), 3: (1.1, 0.05), 4: (0.6, -0.8)}
    plt.figure(figsize=(5, 4), facecolor="white")
    for i, (a, b) in enumerate(case["lines"]):
        xs = [pts[a][0], pts[b][0]]
        ys = [pts[a][1], pts[b][1]]
        plt.plot(xs, ys, lw=3 if i in highlighted else 1.4, color="#c73e1d" if i in highlighted else "#555555")
        plt.text(sum(xs) / 2, sum(ys) / 2, str(i + 1), fontsize=8)
    for bus, (x, y) in pts.items():
        plt.scatter([x], [y], s=180, color="white", edgecolor="black", zorder=3)
        plt.text(x, y, str(bus + 1), ha="center", va="center", zorder=4)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.savefig(out_png.with_suffix(".pdf"))
    plt.close()


if __name__ == "__main__":
    main()

