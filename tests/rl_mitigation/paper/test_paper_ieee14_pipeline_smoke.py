from pathlib import Path


def test_ieee14_paper_smoke_outputs_exist():
    base = Path("results/rl_mitigation/paper/ieee14")
    assert (base / "train_logs" / "proposed_pretrain_mask_smoke.csv").exists()
    assert (base / "eval" / "eval_100_before_after_smoke.csv").exists()
    assert (base / "reports" / "ieee14_claim_check.json").exists()

