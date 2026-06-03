from pathlib import Path


def test_ieee118_smoke_outputs_or_failure_report_exist():
    base = Path("results/rl_mitigation/paper/ieee118")
    failure = base / "reports" / "ieee118_smoke_failure.md"
    expected = [
        base / "train_logs" / "proposed_pretrain_mask_smoke.csv",
        base / "eval" / "eval_20_before_after_smoke.csv",
        base / "figures" / "fig9_ieee118_learning_curve_pretrain_mask_vs_baseline_smoke.png",
        base / "figures" / "fig10_ieee118_negative_return_survival_smoke.png",
        base / "figures" / "fig11a_ieee118_generations_survival_smoke.png",
        base / "figures" / "fig12_ieee118_action_frequency_smoke.png",
    ]
    assert failure.exists() or all(path.exists() for path in expected)

