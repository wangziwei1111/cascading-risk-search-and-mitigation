from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
IEEE118_DIR = ROOT / "src" / "gcn_search" / "ieee118"
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
for path in (IEEE118_DIR, LEGACY_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


torch = pytest.importorskip("torch")

from build_ieee118_mechanism_targets import (  # noqa: E402
    mechanism_arrays_from_records,
)
from mechanism_aware_gcn import (  # noqa: E402
    MechanismAwareTrainingWrapper,
    auxiliary_positive_weight,
    masked_binary_loss,
    masked_positive_severity_loss,
    primary_protected_pcgrad,
)
from train_ieee118_mechanism_aware_gcn import (  # noqa: E402
    FORMAL_MODEL_CLASS,
)
from train_rts79_paper_gcn import (  # noqa: E402
    PaperGcnTrainConfig,
    PaperStyleRts79Gcn,
)
from summarize_ieee118_mechanism_experiments import (  # noqa: E402
    aggregate_prospective,
)


def _model() -> PaperStyleRts79Gcn:
    config = PaperGcnTrainConfig(
        epochs=1,
        batch_size=2,
        k_gcn=1,
        first_layer_channels=3,
        second_layer_channels=4,
        random_seed=7,
    )
    return PaperStyleRts79Gcn(input_channels=2, config=config)


def test_training_wrapper_preserves_original_primary_logits() -> None:
    model = _model()
    wrapper = MechanismAwareTrainingWrapper(model, hidden_channels=4)
    x = torch.randn(2, 3, 2)
    adjacency = torch.stack((torch.eye(3), torch.eye(3)))

    expected = model(x, adjacency)
    actual = wrapper(x, adjacency)["critical_logits"]

    assert torch.allclose(actual, expected)
    assert FORMAL_MODEL_CLASS is PaperStyleRts79Gcn
    assert wrapper.primary_model is model


def test_unqueried_mechanism_labels_do_not_change_binary_loss() -> None:
    logits = torch.tensor([[0.2, -0.4, 1.0]], requires_grad=True)
    mask = torch.tensor([[True, False, False]])
    first = masked_binary_loss(
        logits,
        torch.tensor([[1.0, 0.0, 0.0]]),
        mask,
        positive_weight=2.0,
    )
    second = masked_binary_loss(
        logits,
        torch.tensor([[1.0, 1.0, 1.0]]),
        mask,
        positive_weight=2.0,
    )

    assert float(first.detach()) == pytest.approx(float(second.detach()))


def test_severity_loss_uses_only_known_positive_shed() -> None:
    prediction = torch.tensor([[1.0, 9.0, 3.0]])
    known = torch.tensor([[True, True, False]])
    first = masked_positive_severity_loss(
        prediction, torch.tensor([[2.0, 0.0, 100.0]]), known
    )
    second = masked_positive_severity_loss(
        prediction, torch.tensor([[2.0, 0.0, 1.0]]), known
    )

    assert first == pytest.approx(second)


def test_mechanism_records_require_queried_positive_positions() -> None:
    known = np.asarray([[True, True, False]])
    critical = np.asarray([[1, 0, 1]])
    records = [
        {
            "state_index": 0,
            "line_index": 0,
            "relay_cascade": True,
            "island_load_shed_mw": 4.0,
            "total_load_shed_mw": 5.0,
        }
    ]
    arrays = mechanism_arrays_from_records((1, 3), known, critical, records)

    assert bool(arrays["complete"])
    assert arrays["relay_cascade_target"].tolist() == [[1, 0, 0]]
    assert arrays["island_shed_target"].tolist() == [[1, 0, 0]]
    assert arrays["log1p_load_shed_target"][0, 0] == pytest.approx(np.log1p(5.0))

    with pytest.raises(ValueError, match="unknown mechanism"):
        mechanism_arrays_from_records(
            (1, 3),
            known,
            critical,
            [{**records[0], "line_index": 2}],
        )


def test_auxiliary_positive_weight_is_capped() -> None:
    target = np.asarray([1, 0, 0, 0, 0])
    mask = np.ones(5, dtype=bool)
    assert auxiliary_positive_weight(target, mask) == pytest.approx(4.0)
    assert auxiliary_positive_weight(target, mask, cap=2.0) == pytest.approx(2.0)


def test_primary_protected_pcgrad_removes_opposing_auxiliary_component() -> None:
    primary = torch.tensor([1.0, 0.0])
    auxiliary = torch.tensor([-1.0, 1.0])

    combined, audit = primary_protected_pcgrad(
        [primary], [auxiliary], [True]
    )

    assert audit["gradient_conflict"] is True
    assert torch.allclose(combined[0], torch.tensor([1.0, 1.0]))
    assert torch.dot(combined[0], primary) > 0


def test_prospective_aggregate_separates_informative_fallback_seeds() -> None:
    import pandas as pd

    table = pd.DataFrame(
        {
            "fallback_queries": [0, 100, 80],
            "critical_delta": [0, 2, -1],
            "relay_delta": [0, 1, -2],
            "load_shed_delta_mw": [0.0, 10.0, -3.0],
        }
    )

    summary = aggregate_prospective(table)

    assert summary["num_seeds"] == 3
    assert summary["num_informative_fallback_seeds"] == 2
    assert summary["critical_delta"] == 1
    assert summary["informative_critical_wins"] == 1
    assert summary["informative_critical_losses"] == 1
