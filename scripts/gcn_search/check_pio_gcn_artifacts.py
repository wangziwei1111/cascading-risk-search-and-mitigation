"""Check review-ready PIO-GCN artifacts.

This script is intentionally lightweight. It checks that the review documents
and compact result summaries exist, and that Git is not tracking heavy or
misleading result details.
"""

from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_FILES = [
    "docs/pio_gcn_stage_summary.md",
    "docs/pio_gcn_advisor_brief.md",
    "docs/pio_gcn_pr_description.md",
    "docs/pio_gcn_reproduction_commands.md",
    "docs/gcn_pio_validation_log.md",
    "results/gcn_search/pio_formal_preliminary_3seed/config.json",
    "results/gcn_search/pio_formal_preliminary_3seed/aggregate_method_comparison.csv",
    "results/gcn_search/pio_formal_ablation_3seed/config.json",
    "results/gcn_search/pio_formal_ablation_3seed/ablation_method_comparison.csv",
    "results/gcn_search/pio_formal_ablation_3seed/diagnostics/per_method_score_distribution_summary.csv",
    "results/gcn_search/pio_rank_loss_preliminary_3seed/config.json",
    "results/gcn_search/pio_rank_loss_preliminary_3seed/aggregate_method_comparison.csv",
    "results/gcn_search/pio_rank_loss_preliminary_3seed/diagnostics/rank_loss_vs_ce_summary.csv",
    "results/gcn_search/tracked_large_files_removed_round8.txt",
]


DISALLOWED_TRACKED_SUBSTRINGS = [
    ".pt",
    ".npz",
    "full_truth",
    "smoke_truth",
    "simulation_results",
    "scenario_checkpoints",
    "per_method_score_distribution.csv",
]


DISALLOWED_TRACKED_SUFFIXES = [
    "order.csv",
]


def _git_ls_files(path: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", path],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _read_csv_methods(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return {row.get("method", "") for row in reader}


def main() -> int:
    failures: list[str] = []

    for rel_path in REQUIRED_FILES:
        if not (ROOT / rel_path).exists():
            failures.append(f"Missing required artifact: {rel_path}")

    comparison_path = ROOT / "results/gcn_search/pio_formal_preliminary_3seed/aggregate_method_comparison.csv"
    if comparison_path.exists():
        methods = _read_csv_methods(comparison_path)
        required_methods = {"PIO_GCN_Top100", "LODF_yP", "original_GCN_path_prob", "oracle"}
        missing = required_methods - methods
        if missing:
            failures.append(
                "Preliminary method comparison is missing methods: "
                + ", ".join(sorted(missing))
            )

    validation_log = ROOT / "docs/gcn_pio_validation_log.md"
    if validation_log.exists():
        text = validation_log.read_text(encoding="utf-8", errors="ignore")
        if "Round 7" not in text and "Seventh" not in text and "第七轮" not in text:
            failures.append("Validation log does not contain the seventh-round record.")
        if "Round 8" not in text and "Eighth" not in text and "第八轮" not in text:
            failures.append("Validation log does not contain the eighth-round record.")

    tracked = _git_ls_files("results/gcn_search")
    bad_files: list[str] = []
    for rel_path in tracked:
        lower = rel_path.lower()
        if any(token in lower for token in DISALLOWED_TRACKED_SUBSTRINGS):
            bad_files.append(rel_path)
            continue
        if any(lower.endswith(suffix) for suffix in DISALLOWED_TRACKED_SUFFIXES):
            bad_files.append(rel_path)

    if bad_files:
        failures.append(
            "Disallowed tracked result artifacts:\n" + "\n".join(f"  - {p}" for p in bad_files)
        )

    if failures:
        print("FAIL: PIO-GCN artifact check failed.")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("PASS: PIO-GCN artifacts are review-ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
