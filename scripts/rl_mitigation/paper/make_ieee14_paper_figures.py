from __future__ import annotations

import argparse
from ._common import ROOT, normalize_mode


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--mode", choices=["smoke", "medium", "formal"])
    args = parser.parse_args()
    mode = normalize_mode(args.mode, args.smoke)
    base = ROOT / "results" / "rl_mitigation" / "paper" / "ieee14"
    figs = base / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    # Figure 7 is produced by train_ieee14_gridsearch; Figure 8 by evaluate_ieee14_survival.
    caption = [
        "# IEEE14 Paper Figures",
        "",
        f"- Current requested mode: `{mode}`.",
        "- Figure 7: grid-search learning curves. Smoke/medium files include explicit suffixes.",
        "- Figure 8: before/after negative-return survival function. Smoke/medium/formal files are separate.",
        "- No oracle, safe gate, or GCN-RL result is included in these paper figures.",
    ]
    (figs / "ieee14_paper_figures_readme.md").write_text("\n".join(caption) + "\n", encoding="utf-8")
    print(f"IEEE14 paper figure index written to {figs}")


if __name__ == "__main__":
    main()
