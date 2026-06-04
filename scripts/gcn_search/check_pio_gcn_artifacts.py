"""Check review-ready PIO-GCN PathRank artifacts."""

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
    "docs/pio_gcn_extended_experiment.md",
    "docs/pio_gcn_renewable_preliminary.md",
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
    "results/gcn_search/pio_extended_fulltruth_5seed/config.json",
    "results/gcn_search/pio_extended_fulltruth_5seed/per_seed_fulltruth_summary.csv",
    "results/gcn_search/pio_extended_fulltruth_5seed/aggregate_method_comparison.csv",
    "results/gcn_search/pio_extended_fulltruth_5seed/diagnostics/per_seed_variability.csv",
    "results/gcn_search/paper_baseline_strong/paper_baseline_eval_summary.csv",
    "results/gcn_search/pio_loss_diagnostics/recommendations.md",
]


SUMMARY_FILES = [
    "results/gcn_search/pio_formal_preliminary_3seed/aggregate_method_comparison.csv",
    "results/gcn_search/pio_formal_preliminary_3seed/aggregate_topk_summary.csv",
    "results/gcn_search/pio_formal_ablation_3seed/ablation_method_comparison.csv",
    "results/gcn_search/pio_rank_loss_preliminary_3seed/aggregate_method_comparison.csv",
    "results/gcn_search/pio_rank_loss_preliminary_3seed/diagnostics/rank_loss_vs_ce_summary.csv",
    "results/gcn_search/pio_extended_fulltruth_5seed/aggregate_method_comparison.csv",
    "results/gcn_search/paper_baseline_strong/paper_baseline_eval_summary.csv",
    "results/gcn_search/pio_loss_diagnostics/loss_contribution_summary.csv",
]


DISALLOWED_TRACKED_SUBSTRINGS = [
    ".pt",
    ".npz",
    "full_truth",
    "smoke_truth",
    "simulation_results",
    "scenario_checkpoints",
    "per_method_score_distribution.csv",
    "topk_score_distribution.csv",
    "found_critical_paths.csv",
    "missed_critical_paths.csv",
]


DISALLOWED_TRACKED_SUFFIXES = ["order.csv"]


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


def _read_text(rel_path: str) -> str:
    return (ROOT / rel_path).read_text(encoding="utf-8", errors="ignore")


def main() -> int:
    failures: list[str] = []

    for rel_path in REQUIRED_FILES:
        if not (ROOT / rel_path).exists():
            failures.append(f"Missing required artifact: {rel_path}")

    for rel_path in SUMMARY_FILES:
        path = ROOT / rel_path
        if path.exists() and path.stat().st_size == 0:
            failures.append(f"Summary file is empty: {rel_path}")

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

    validation_log_path = ROOT / "docs/gcn_pio_validation_log.md"
    if validation_log_path.exists():
        text = _read_text("docs/gcn_pio_validation_log.md")
        if "Round 7" not in text and "Seventh" not in text:
            failures.append("Validation log does not contain the seventh-round record.")
        if "Round 8" not in text and "Eighth" not in text:
            failures.append("Validation log does not contain the eighth-round record.")
        if "Round 9" not in text and "Ninth" not in text:
            failures.append("Validation log does not contain the ninth-round record.")

    pr_text = _read_text("docs/pio_gcn_pr_description.md") if (ROOT / "docs/pio_gcn_pr_description.md").exists() else ""
    if "RL Untouched" not in pr_text and "RL untouched" not in pr_text:
        failures.append("PR description does not contain an RL untouched statement.")

    advisor_text = _read_text("docs/pio_gcn_advisor_brief.md") if (ROOT / "docs/pio_gcn_advisor_brief.md").exists() else ""
    if not any(term in advisor_text for term in ["不是最终论文结论", "not a final", "not final"]):
        failures.append("Advisor brief does not clearly state this is not a final paper conclusion.")

    stage_text = _read_text("docs/pio_gcn_stage_summary.md") if (ROOT / "docs/pio_gcn_stage_summary.md").exists() else ""
    if "run_pio_gcn_formal_experiment.py" in stage_text:
        failures.append("Stage summary contains nonexistent script: run_pio_gcn_formal_experiment.py")
    if "real SCADA/PMU integration" in stage_text:
        failures.append("Stage summary contains an overstated SCADA/PMU integration claim.")

    renewable_text = _read_text("docs/pio_gcn_renewable_preliminary.md") if (ROOT / "docs/pio_gcn_renewable_preliminary.md").exists() else ""
    if "synthetic renewable" not in renewable_text.lower():
        failures.append("Renewable preliminary doc does not clearly state synthetic renewable scope.")

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
