import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.rl_mitigation import tune_safe_policy_thresholds


def test_safe_policy_threshold_tuning_uses_val_split_source():
    source = Path(tune_safe_policy_thresholds.__file__).read_text(encoding="utf-8")
    assert '"val"' in source
    assert 'SPLIT_SEEDS["val"]' in source
    assert 'SPLIT_SEEDS["test"]' not in source
