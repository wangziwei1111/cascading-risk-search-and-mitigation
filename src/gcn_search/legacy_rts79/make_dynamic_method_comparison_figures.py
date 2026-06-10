from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


CAPTION = "Preliminary diagnostic; simplified swing-equation prototype; no dynamic recall; not EMT / not full OPF."


def make_dynamic_method_comparison_figures(
    summary_csv: str | Path,
    rank_depth_csv: str | Path,
    alignment_csv: str | Path,
    bootstrap_csv: str | Path,
    output_dir: str | Path,
) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = pd.read_csv(summary_csv)
    rank_depth = pd.read_csv(rank_depth_csv)
    alignment = pd.read_csv(alignment_csv)
    bootstrap = pd.read_csv(bootstrap_csv) if Path(bootstrap_csv).exists() else pd.DataFrame()
    files: dict[str, str] = {}
    files["precision"] = str(out / "fig_dynamic_precision_top50_top100.png")
    files["stress"] = str(out / "fig_mean_dynamic_stress_top50_top100.png")
    files["rank_depth"] = str(out / "fig_rank_depth_stress_curve.png")
    files["alignment"] = str(out / "fig_opa_dynamic_alignment.png")
    _bar(summary, "dynamic_precision_at_k", "Dynamic Precision Top50/Top100 (preliminary diagnostic)", files["precision"], plt)
    _bar(summary, "mean_dynamic_stress_score", "Mean Dynamic Stress Top50/Top100 (preliminary diagnostic)", files["stress"], plt)
    _rank_depth(rank_depth, files["rank_depth"], plt)
    _alignment(alignment, files["alignment"], plt)
    tables_csv = out / "dynamic_method_comparison_tables.csv"
    _write_tables(summary, alignment, bootstrap, tables_csv)
    manifest = {
        "summary_csv": str(summary_csv),
        "rank_depth_csv": str(rank_depth_csv),
        "alignment_csv": str(alignment_csv),
        "bootstrap_csv": str(bootstrap_csv),
        "figures": files,
        "tables_csv": str(tables_csv),
        "caption": CAPTION,
        "note": "report-ready preliminary diagnostic figures only; no dynamic recall is reported",
    }
    manifest_path = out / "figure_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"manifest": str(manifest_path), **manifest}


def _bar(summary: pd.DataFrame, column: str, title: str, output: str, plt) -> None:
    pivot = summary.pivot(index="method", columns="top_k", values=column).reindex(["learned_mlp", "pio_gcn", "lodf"])
    ax = pivot.plot(kind="bar", figsize=(7, 4), color=["#4C78A8", "#F58518"])
    ax.set_title(title)
    ax.set_ylabel(column)
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.3)
    ax.text(0.0, -0.28, CAPTION, transform=ax.transAxes, fontsize=8)
    plt.tight_layout()
    plt.savefig(output, dpi=180)
    plt.close()


def _rank_depth(rank_depth: pd.DataFrame, output: str, plt) -> None:
    fig, ax = plt.subplots(figsize=(7, 4))
    for method, sub in rank_depth.groupby("method"):
        sub = sub.sort_values("k")
        ax.plot(sub["k"], sub["mean_dynamic_stress_score_at_k"], marker="o", label=method)
    ax.set_title("Rank-Depth Mean Dynamic Stress (preliminary diagnostic)")
    ax.set_xlabel("K")
    ax.set_ylabel("mean_dynamic_stress_score_at_k")
    ax.grid(alpha=0.3)
    ax.legend()
    ax.text(0.0, -0.28, CAPTION, transform=ax.transAxes, fontsize=8)
    plt.tight_layout()
    plt.savefig(output, dpi=180)
    plt.close(fig)


def _alignment(alignment: pd.DataFrame, output: str, plt) -> None:
    top100 = alignment[alignment["top_k"].astype(int) == 100].copy()
    ax = top100.set_index("method")["stress_corr_with_opa_total_load_shed_mw"].reindex(["learned_mlp", "pio_gcn", "lodf"]).plot(kind="bar", figsize=(7, 4), color="#54A24B")
    ax.set_title("OPA/Dynamic Alignment Top100 (preliminary diagnostic)")
    ax.set_ylabel("corr(stress, OPA shed)")
    ax.set_xlabel("")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.grid(axis="y", alpha=0.3)
    ax.text(0.0, -0.28, CAPTION, transform=ax.transAxes, fontsize=8)
    plt.tight_layout()
    plt.savefig(output, dpi=180)
    plt.close()


def _write_tables(summary: pd.DataFrame, alignment: pd.DataFrame, bootstrap: pd.DataFrame, output: Path) -> None:
    parts = []
    summary_part = summary.copy()
    summary_part.insert(0, "table", "dynamic_summary")
    parts.append(summary_part)
    alignment_part = alignment.copy()
    alignment_part.insert(0, "table", "alignment")
    parts.append(alignment_part)
    if not bootstrap.empty:
        boot_part = bootstrap.copy()
        boot_part.insert(0, "table", "bootstrap")
        parts.append(boot_part)
    pd.concat(parts, ignore_index=True, sort=False).to_csv(output, index=False, encoding="utf-8-sig")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Make report-ready dynamic method comparison figures.")
    parser.add_argument("--summary-csv", required=True)
    parser.add_argument("--rank-depth-csv", required=True)
    parser.add_argument("--alignment-csv", required=True)
    parser.add_argument("--bootstrap-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    make_dynamic_method_comparison_figures(args.summary_csv, args.rank_depth_csv, args.alignment_csv, args.bootstrap_csv, args.output_dir)


if __name__ == "__main__":
    main()
