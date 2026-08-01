from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pypower.idx_brch import BR_STATUS, BR_X, F_BUS, PF, RATE_A, TAP, T_BUS


ROOT = Path(__file__).resolve().parents[3]
IEEE118_DIR = Path(__file__).resolve().parent
LEGACY_DIR = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(IEEE118_DIR))
sys.path.insert(0, str(LEGACY_DIR))

from build_ieee118_dc_lodf_low_fidelity_targets import portable_result_path
from build_ieee118_paper_gcn_training_dataset import (
    apply_load_scenario,
    final_outage_set,
    state_features,
)
from case_adapter import build_case_adapter, run_sequential_outages_for_case
from convert_ieee118_step2_to_rts79_gcn_format import (
    PAPER_FEATURE_NAMES,
    normalize_x,
)
from evaluate_ieee118_iterative_lodf_n1_proxy import (
    compute_label_free_iterative_proxy_scores,
)
from evaluate_ieee118_lazy_prefix_search import rank_normalize_line_scores
from generate_ieee118_ordered_n2_fulltruth import (
    apply_thermal_limit_mode,
    summarize_state,
)
from prospective_physical_oracle import (
    OnDemandCascadeOracle,
    ProspectiveSearchResult,
    run_frozen_adaptive_ordered_n2,
)
from pair_interaction_reranker import FrozenPairInteractionReranker
from tail_rank_fusion import (
    gcn_upper_confidence_scores,
    reciprocal_rank_fusion_scores,
)
from train_ieee118_with_original_rts79_gcn import (
    build_branch_graph_adjacency_from_endpoints,
    load_original_rts79_gcn_symbols,
    predict_probability,
)


DEFAULT_RUN_DIR = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase3_mf_all_candidates_perstate95_e1_w5_curve"
    / "pmf_hybrid_prior_corrected_seed_20260730"
)
DEFAULT_NORMALIZER = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_n1_residual_scaleup"
    / "paper_8000_residual"
    / "ieee118_residual_reachable_feature_normalizer.json"
)
DEFAULT_OUTPUT_ROOT = (
    ROOT
    / "results"
    / "gcn_search"
    / "ieee118_simulation_efficient_gcn"
    / "phase4_prospective_oracle"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the frozen IEEE118 Phase-3 policy against an on-demand "
            "physical cascade oracle without reading full-truth."
        )
    )
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--load-scale", type=float, default=1.0)
    parser.add_argument("--load-random-low", type=float, default=0.9)
    parser.add_argument("--load-random-high", type=float, default=1.1)
    parser.add_argument(
        "--limit-mode",
        choices=["original_rate_a", "flow_scaled"],
        default="flow_scaled",
    )
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--proxy-max-rounds", type=int, default=20)
    parser.add_argument("--gate-size", type=int, default=26)
    parser.add_argument("--probes-per-second-line", type=int, default=5)
    parser.add_argument("--promotion-min-positives", type=int, default=1)
    parser.add_argument("--max-n2-queries", type=int, default=200)
    parser.add_argument(
        "--fallback-reserve-queries",
        type=int,
        default=0,
        help="Reserve this many N-2 queries for the learned fallback ranking.",
    )
    parser.add_argument("--checkpoint-every", type=int, default=25)
    parser.add_argument(
        "--gcn-checkpoint",
        type=Path,
        default=None,
        help="Optional PaperStyleRts79Gcn ensemble checkpoint override.",
    )
    parser.add_argument(
        "--interaction-head-checkpoint",
        type=Path,
        default=None,
        help="Optional frozen first-line/candidate relation head over GCN scores.",
    )
    parser.add_argument(
        "--fallback-score-mode",
        choices=[
            "gcn",
            "gcn_ucb",
            "rrf_gcn_proxy",
            "rrf_gcn_proxy_uncertainty",
        ],
        default="gcn",
        help="Label-free ranking used only by the final fallback stage.",
    )
    parser.add_argument("--rrf-k", type=float, default=60.0)
    parser.add_argument("--rrf-uncertainty-weight", type=float, default=0.25)
    parser.add_argument("--gcn-uncertainty-weight", type=float, default=0.25)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument(
        "--feature-normalizer-json",
        type=Path,
        default=DEFAULT_NORMALIZER,
    )
    parser.add_argument("--k-gcn", type=int, default=6)
    parser.add_argument("--first-layer-channels", type=int, default=16)
    parser.add_argument("--second-layer-channels", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args(argv)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class OriginalRts79GcnProspectiveScorer:
    """Inference-only wrapper around saved `PaperStyleRts79Gcn` states."""

    def __init__(
        self,
        *,
        checkpoint_path: Path,
        input_channels: int,
        branch_from_bus: np.ndarray,
        branch_to_bus: np.ndarray,
        k_gcn: int,
        first_layer_channels: int,
        second_layer_channels: int,
    ) -> None:
        symbols = load_original_rts79_gcn_symbols()
        self.torch = symbols["torch"]
        try:
            checkpoint = self.torch.load(
                checkpoint_path,
                map_location="cpu",
                weights_only=False,
            )
        except TypeError:  # pragma: no cover - older torch compatibility.
            checkpoint = self.torch.load(checkpoint_path, map_location="cpu")
        member_states = checkpoint.get("member_states", [])
        if not member_states:
            raise ValueError(
                f"GCN checkpoint contains no ensemble states: {checkpoint_path}"
            )
        adjacency = build_branch_graph_adjacency_from_endpoints(
            branch_from_bus,
            branch_to_bus,
        )
        self.adjacency_powers = self.torch.tensor(
            symbols["_build_adjacency_powers"](adjacency, int(k_gcn)),
            dtype=self.torch.float32,
        )
        config_class = symbols["PaperGcnTrainConfig"]
        model_class = symbols["PaperStyleRts79Gcn"]
        self.models = []
        for member, state in enumerate(member_states):
            config = config_class(
                epochs=1,
                batch_size=128,
                learning_rate=0.005,
                k_gcn=int(k_gcn),
                first_layer_channels=int(first_layer_channels),
                second_layer_channels=int(second_layer_channels),
                positive_weight=1.0,
                validation_fraction=0.0,
                random_seed=int(member),
            )
            model = model_class(input_channels=int(input_channels), config=config)
            model.load_state_dict(state)
            self.models.append(model)

    def predict_members(self, x_state: np.ndarray) -> np.ndarray:
        batch = np.asarray(x_state, dtype=np.float32)[None, :, :]
        return np.stack(
            [
                predict_probability(
                    model,
                    batch,
                    self.adjacency_powers,
                    self.torch,
                )[0]
                for model in self.models
            ],
            axis=0,
        )

    def predict(self, x_state: np.ndarray) -> np.ndarray:
        return np.mean(self.predict_members(x_state), axis=0)


def _atomic_csv(rows: list[dict[str, Any]], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    pd.DataFrame(rows).to_csv(temporary, index=False, encoding="utf-8-sig")
    temporary.replace(path)


def _atomic_json(value: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def _bool_series(values: pd.Series) -> pd.Series:
    if values.dtype == bool:
        return values.fillna(False)
    return values.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def _as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes"}


def build_prospective_stage_summary(query_table: pd.DataFrame) -> pd.DataFrame:
    required = {
        "search_stage",
        "critical",
        "relay_cascade",
        "has_overload_cascade",
        "total_load_shed_mw",
        "error",
    }
    missing = sorted(required - set(query_table))
    if missing:
        raise ValueError(f"Prospective query log is missing fields: {missing}")
    rows = []
    for stage in dict.fromkeys(query_table["search_stage"].astype(str)):
        group = query_table.loc[
            query_table["search_stage"].astype(str).eq(stage)
        ]
        critical = _bool_series(group["critical"])
        relay = _bool_series(group["relay_cascade"])
        activity = _bool_series(group["has_overload_cascade"])
        error = group["error"].fillna("").astype(str).str.len().gt(0)
        load_shed = pd.to_numeric(
            group["total_load_shed_mw"], errors="coerce"
        ).fillna(0.0)
        rows.append(
            {
                "search_stage": stage,
                "num_queries": int(len(group)),
                "num_critical": int(critical.sum()),
                "critical_precision": float(
                    critical.mean() if len(group) else 0.0
                ),
                "num_relay_cascade": int(relay.sum()),
                "num_overload_relay_activity": int(activity.sum()),
                "num_errors": int(error.sum()),
                "captured_load_shed_mw": float(load_shed.sum()),
            }
        )
    return pd.DataFrame(rows)


def build_prospective_top_discoveries(
    query_table: pd.DataFrame,
    *,
    limit: int = 100,
) -> pd.DataFrame:
    if limit < 0:
        raise ValueError("Top-discovery limit must be non-negative.")
    table = query_table.copy()
    table["total_load_shed_mw"] = pd.to_numeric(
        table["total_load_shed_mw"], errors="coerce"
    ).fillna(0.0)
    return table.sort_values(
        ["total_load_shed_mw", "query_rank", "path"],
        ascending=[False, True, True],
        kind="stable",
    ).head(limit)


def _configuration(args: argparse.Namespace, checkpoint_path: Path) -> dict[str, Any]:
    return {
        "case_name": "ieee118",
        "seed": int(args.seed),
        "load_scale": float(args.load_scale),
        "load_random_low": float(args.load_random_low),
        "load_random_high": float(args.load_random_high),
        "limit_mode": str(args.limit_mode),
        "flow_limit_scale": float(args.flow_limit_scale),
        "min_rate_a": float(args.min_rate_a),
        "beta": float(args.beta),
        "security_limit": float(args.security_limit),
        "proxy_max_rounds": int(args.proxy_max_rounds),
        "gate_size": int(args.gate_size),
        "probes_per_second_line": int(args.probes_per_second_line),
        "promotion_min_positives": int(args.promotion_min_positives),
        "max_n2_queries": int(args.max_n2_queries),
        "fallback_reserve_queries": int(args.fallback_reserve_queries),
        "fallback_score_mode": str(args.fallback_score_mode),
        "rrf_k": float(args.rrf_k),
        "rrf_uncertainty_weight": float(args.rrf_uncertainty_weight),
        "gcn_uncertainty_weight": float(args.gcn_uncertainty_weight),
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "checkpoint": portable_result_path(checkpoint_path),
        "checkpoint_sha256": _file_sha256(checkpoint_path),
        "interaction_head_checkpoint": (
            portable_result_path(args.interaction_head_checkpoint)
            if args.interaction_head_checkpoint is not None
            else None
        ),
        "interaction_head_sha256": (
            _file_sha256(args.interaction_head_checkpoint)
            if args.interaction_head_checkpoint is not None
            else None
        ),
        "feature_normalizer": portable_result_path(
            args.feature_normalizer_json
        ),
        "feature_normalizer_sha256": _file_sha256(
            args.feature_normalizer_json
        ),
        "k_gcn": int(args.k_gcn),
        "first_layer_channels": int(args.first_layer_channels),
        "second_layer_channels": int(args.second_layer_channels),
        "fulltruth_input": None,
    }


def _configuration_fingerprint(config: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(config, sort_keys=True).encode("utf-8")
    ).hexdigest()


def run_prospective_oracle(args: argparse.Namespace) -> dict[str, Any]:
    if args.max_n2_queries <= 0:
        raise ValueError("--max-n2-queries must be positive.")
    if args.checkpoint_every < 0:
        raise ValueError("--checkpoint-every must be non-negative.")
    if args.gate_size <= 0 or args.gate_size > 186:
        raise ValueError("--gate-size must be between 1 and 186.")
    if args.rrf_k <= 0:
        raise ValueError("--rrf-k must be positive.")
    if args.rrf_uncertainty_weight < 0:
        raise ValueError("--rrf-uncertainty-weight must be non-negative.")
    if args.gcn_uncertainty_weight < 0:
        raise ValueError("--gcn-uncertainty-weight must be non-negative.")
    checkpoint_path = (
        args.gcn_checkpoint
        if args.gcn_checkpoint is not None
        else args.run_dir / "active_label_replay_checkpoint.pt"
    )
    for path, label in (
        (checkpoint_path, "active-replay GCN checkpoint"),
        (args.feature_normalizer_json, "paper-feature normalizer"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"Missing local {label}: {path}")
    if (
        args.interaction_head_checkpoint is not None
        and not args.interaction_head_checkpoint.exists()
    ):
        raise FileNotFoundError(
            "Missing local pair interaction head: "
            f"{args.interaction_head_checkpoint}"
        )

    output_dir = args.output_dir or (
        DEFAULT_OUTPUT_ROOT / f"seed_{int(args.seed)}"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    query_path = output_dir / "ieee118_prospective_oracle_queries.csv"
    first_step_path = output_dir / "ieee118_prospective_oracle_first_steps.csv"
    config_path = output_dir / "ieee118_prospective_oracle_config.json"
    summary_path = output_dir / "ieee118_prospective_oracle_summary.json"
    config = _configuration(args, checkpoint_path)
    fingerprint = _configuration_fingerprint(config)
    resume_rows: list[dict[str, Any]] = []
    resume_first_step_rows: list[dict[str, Any]] = []
    previous_cumulative_n1_calls = 0
    previous_summary: dict[str, Any] = {}
    if args.resume and config_path.exists():
        existing_config = json.loads(config_path.read_text(encoding="utf-8"))
        if existing_config.get("fingerprint") != fingerprint:
            raise ValueError(
                "Prospective checkpoint configuration changed; use the original "
                "arguments or a new output directory."
            )
        if query_path.exists():
            resume_rows = pd.read_csv(query_path).to_dict("records")
        if first_step_path.exists():
            resume_first_step_rows = pd.read_csv(first_step_path).to_dict(
                "records"
            )
        if summary_path.exists():
            previous_summary = json.loads(
                summary_path.read_text(encoding="utf-8")
            )
            previous_cumulative_n1_calls = int(
                previous_summary.get(
                    "cumulative_n1_state_constructions",
                    previous_summary.get(
                        "num_n1_state_constructions_this_run",
                        0,
                    ),
                )
            )
    elif args.resume and query_path.exists():
        raise ValueError("Prospective query log exists without its config fingerprint.")
    elif not args.resume and query_path.exists():
        raise FileExistsError(
            f"Prospective output already exists: {query_path}. Use --resume or a new directory."
        )
    _atomic_json({**config, "fingerprint": fingerprint}, config_path)

    adapter = build_case_adapter("ieee118")
    scenario_case = apply_load_scenario(
        adapter.case,
        seed=int(args.seed),
        load_scale=float(args.load_scale),
        low=float(args.load_random_low),
        high=float(args.load_random_high),
    )
    scenario_case = apply_thermal_limit_mode(
        scenario_case,
        limit_mode=str(args.limit_mode),
        flow_limit_scale=float(args.flow_limit_scale),
        min_rate_a=float(args.min_rate_a),
    )
    branch = scenario_case["branch"]
    line_labels = np.asarray(adapter.line_labels, dtype=str)
    proxy = compute_label_free_iterative_proxy_scores(
        signed_flow=branch[:, PF],
        rate_a=branch[:, RATE_A],
        line_labels=line_labels,
        branch_from_bus=branch[:, F_BUS],
        branch_to_bus=branch[:, T_BUS],
        branch_x=branch[:, BR_X],
        branch_tap_ratio=branch[:, TAP],
        beta=float(args.beta),
        max_rounds=int(args.proxy_max_rounds),
    )
    proxy_score = proxy["iterative_composite_score"].to_numpy(dtype=float)
    normalized_first = rank_normalize_line_scores(proxy_score, line_labels)
    first_scores = dict(zip(line_labels.tolist(), normalized_first.tolist()))
    gate_lines = tuple(
        proxy.sort_values(
            ["iterative_composite_score", "line_label"],
            ascending=[False, True],
            kind="stable",
        )["line_label"]
        .head(int(args.gate_size))
        .astype(str)
    )

    normalizer = json.loads(
        args.feature_normalizer_json.read_text(encoding="utf-8")
    )
    missing_features = sorted(set(PAPER_FEATURE_NAMES) - set(normalizer))
    if missing_features:
        raise ValueError(f"Feature normalizer is missing: {missing_features}")
    scorer = OriginalRts79GcnProspectiveScorer(
        checkpoint_path=checkpoint_path,
        input_channels=len(PAPER_FEATURE_NAMES),
        branch_from_bus=branch[:, F_BUS],
        branch_to_bus=branch[:, T_BUS],
        k_gcn=int(args.k_gcn),
        first_layer_channels=int(args.first_layer_channels),
        second_layer_channels=int(args.second_layer_channels),
    )
    interaction_reranker = None
    if args.interaction_head_checkpoint is not None:
        interaction_reranker = FrozenPairInteractionReranker(
            args.interaction_head_checkpoint,
            adjacency=build_branch_graph_adjacency_from_endpoints(
                branch[:, F_BUS], branch[:, T_BUS]
            ),
            line_labels=line_labels,
        )

    def build_first(first_line: str) -> dict[str, Any]:
        try:
            return run_sequential_outages_for_case(
                scenario_case,
                adapter,
                [first_line],
                beta=float(args.beta),
                security_limit=float(args.security_limit),
            )
        except Exception as exc:  # pragma: no cover - physical solver failure.
            return {"prospective_error": str(exc)}

    def describe_first(state: dict[str, Any], first_line: str) -> dict[str, Any]:
        if "prospective_error" in state:
            return {
                "converged": False,
                "critical": False,
                "total_load_shed_mw": 0.0,
                "error": state["prospective_error"],
                "valid_second_lines": (),
            }
        summary = summarize_state(state, {first_line})
        status = state["case"]["branch"][:, BR_STATUS].astype(int) == 1
        valid = tuple(
            label
            for index, label in enumerate(line_labels)
            if status[index] and label != first_line
        )
        return {**summary, "valid_second_lines": valid}

    def build_second(first_state: dict[str, Any], second_line: str) -> dict[str, Any]:
        try:
            return run_sequential_outages_for_case(
                first_state["case"],
                adapter,
                [second_line],
                beta=float(args.beta),
                security_limit=float(args.security_limit),
            )
        except Exception as exc:  # pragma: no cover - physical solver failure.
            return {"prospective_error": str(exc)}

    def describe_second(
        state: dict[str, Any],
        first_line: str,
        second_line: str,
    ) -> dict[str, Any]:
        if "prospective_error" in state:
            return {
                "converged": False,
                "critical": False,
                "relay_cascade": False,
                "total_load_shed_mw": 0.0,
                "error": state["prospective_error"],
            }
        summary = summarize_state(state, {first_line, second_line})
        return {
            **summary,
            "relay_cascade": bool(
                summary["critical_mechanism"] == "relay_cascade"
            ),
            "error": "",
        }

    last_checkpoint_new_calls = -1

    def checkpoint_callback(oracle: OnDemandCascadeOracle) -> None:
        nonlocal last_checkpoint_new_calls
        if args.checkpoint_every <= 0:
            return
        current = oracle.num_new_n2_simulations
        if current == 0 or current % int(args.checkpoint_every) != 0:
            return
        if current == last_checkpoint_new_calls:
            return
        _atomic_csv(oracle.query_rows, query_path)
        _atomic_csv(oracle.first_step_rows, first_step_path)
        last_checkpoint_new_calls = current

    oracle = OnDemandCascadeOracle(
        line_labels=line_labels,
        first_state_builder=build_first,
        first_state_describer=describe_first,
        second_state_builder=build_second,
        second_state_describer=describe_second,
        resume_rows=resume_rows,
        resume_first_step_rows=resume_first_step_rows,
        checkpoint_callback=checkpoint_callback,
    )
    second_score_cache: dict[str, dict[str, float]] = {}

    def second_score_provider(first_line: str) -> dict[str, float]:
        if first_line in second_score_cache:
            return second_score_cache[first_line]
        first_state, description = oracle.get_first_state(first_line)
        if not description.get("converged", True) or description.get(
            "critical", False
        ):
            scores = {
                label: 0.0 for label in line_labels if label != first_line
            }
            second_score_cache[first_line] = scores
            return scores
        outages = final_outage_set(first_state) | {first_line}
        x_raw, feature_labels, _, _ = state_features(
            first_state["case"],
            adapter,
            outages,
            "paper",
            float(args.beta),
            float(args.security_limit),
        )
        if feature_labels != line_labels.tolist():
            raise ValueError("Prospective GCN line-label order changed.")
        x = normalize_x(
            x_raw[None, :, :],
            normalizer,
            PAPER_FEATURE_NAMES,
        )[0]
        member_probability = scorer.predict_members(x)
        probability = np.mean(member_probability, axis=0)
        valid = set(description["valid_second_lines"])
        valid_mask = np.asarray(
            [label in valid for label in line_labels],
            dtype=bool,
        )
        selected_score = probability
        if interaction_reranker is not None:
            if args.fallback_score_mode != "gcn":
                raise ValueError(
                    "Pair interaction reranking currently requires --fallback-score-mode gcn."
                )
            selected_score = interaction_reranker.predict(
                probability, x, first_line
            )
        elif args.fallback_score_mode == "gcn_ucb":
            selected_score = gcn_upper_confidence_scores(
                member_probability,
                uncertainty_weight=float(args.gcn_uncertainty_weight),
            )
        elif args.fallback_score_mode != "gcn":
            first_branch = first_state["case"]["branch"]
            physical_proxy = compute_label_free_iterative_proxy_scores(
                signed_flow=first_branch[:, PF],
                rate_a=first_branch[:, RATE_A],
                line_labels=line_labels,
                branch_from_bus=first_branch[:, F_BUS],
                branch_to_bus=first_branch[:, T_BUS],
                branch_x=first_branch[:, BR_X],
                branch_tap_ratio=first_branch[:, TAP],
                beta=float(args.beta),
                max_rounds=int(args.proxy_max_rounds),
                initial_branch_status=first_branch[:, BR_STATUS] > 0,
            )["iterative_composite_score"].to_numpy(dtype=float)
            uncertainty = (
                np.std(member_probability, axis=0)
                if args.fallback_score_mode
                == "rrf_gcn_proxy_uncertainty"
                else None
            )
            selected_score = reciprocal_rank_fusion_scores(
                probability,
                physical_proxy,
                line_labels,
                valid_mask,
                uncertainty=uncertainty,
                rrf_k=float(args.rrf_k),
                uncertainty_weight=float(args.rrf_uncertainty_weight),
            )
        scores = {
            label: float(selected_score[index]) if label in valid else 0.0
            for index, label in enumerate(line_labels)
            if label != first_line
        }
        second_score_cache[first_line] = scores
        return scores

    if len(resume_rows) > int(args.max_n2_queries):
        raise ValueError("Resume rows already exceed --max-n2-queries.")
    if len(resume_rows) == int(args.max_n2_queries):
        resume_table = pd.DataFrame(resume_rows)
        probe_paths = tuple(
            resume_table.loc[
                resume_table["search_stage"].astype(str).eq("probe"),
                "path",
            ].astype(str)
        )
        promoted = tuple(
            str(value)
            for value in previous_summary.get("promoted_second_lines", [])
        )
        if not promoted:
            promoted = tuple(
                dict.fromkeys(
                    resume_table.loc[
                        resume_table["search_stage"]
                        .astype(str)
                        .eq("promoted_line_expansion"),
                        "second_line",
                    ].astype(str)
                )
            )
        result = ProspectiveSearchResult(
            query_rows=tuple(oracle.query_rows),
            first_step_rows=tuple(oracle.first_step_rows),
            probe_paths=probe_paths,
            promoted_second_lines=promoted,
            num_n1_state_constructions=0,
            num_unique_n2_queries=len(oracle.query_rows),
            num_new_n2_simulations=0,
            budget_exhausted=True,
        )
    else:
        result = run_frozen_adaptive_ordered_n2(
            first_line_scores=first_scores,
            line_labels=line_labels,
            gate_second_lines=gate_lines,
            second_score_provider=second_score_provider,
            oracle=oracle,
            probes_per_second_line=int(args.probes_per_second_line),
            promotion_min_positives=int(args.promotion_min_positives),
            max_n2_queries=int(args.max_n2_queries),
            fallback_reserve_queries=int(args.fallback_reserve_queries),
            fallback_stage_name=(
                "gcn_pair_interaction_fallback"
                if args.interaction_head_checkpoint is not None
                else "unchanged_gcn_fallback"
                if args.fallback_score_mode == "gcn"
                else f"{args.fallback_score_mode}_fallback"
            ),
        )
    _atomic_csv(oracle.query_rows, query_path)
    _atomic_csv(oracle.first_step_rows, first_step_path)
    query_table = pd.DataFrame(oracle.query_rows)
    stage_summary = build_prospective_stage_summary(query_table)
    stage_summary_path = output_dir / "ieee118_prospective_stage_summary.csv"
    stage_summary.to_csv(stage_summary_path, index=False, encoding="utf-8-sig")
    top_path = output_dir / "ieee118_prospective_top_discoveries.csv"
    build_prospective_top_discoveries(query_table).to_csv(
        top_path,
        index=False,
        encoding="utf-8-sig",
    )
    critical = (
        _bool_series(query_table["critical"])
        if not query_table.empty
        else pd.Series(dtype=bool)
    )
    relay = (
        _bool_series(query_table["relay_cascade"])
        if "relay_cascade" in query_table
        else pd.Series(False, index=query_table.index, dtype=bool)
    )
    relay_activity = (
        _bool_series(query_table["has_overload_cascade"])
        if "has_overload_cascade" in query_table
        else pd.Series(False, index=query_table.index, dtype=bool)
    )
    errors = (
        query_table["error"].fillna("").astype(str).str.len().gt(0)
        if "error" in query_table
        else pd.Series(False, index=query_table.index, dtype=bool)
    )
    stage_counts = (
        query_table["search_stage"].value_counts().sort_index().to_dict()
        if not query_table.empty
        else {}
    )
    summary = {
        "status": "complete",
        "research_stage": "Phase 4 prospective on-demand physical-oracle smoke",
        "prospective_policy": True,
        "fulltruth_read_during_search": False,
        "fulltruth_audit_performed": False,
        "recall_metrics_available": False,
        "model_class": "PaperStyleRts79Gcn",
        "model_core_modified": False,
        "configuration_fingerprint": fingerprint,
        "seed": int(args.seed),
        "max_n2_queries": int(args.max_n2_queries),
        "num_unique_n2_queries": int(result.num_unique_n2_queries),
        "num_new_n2_simulations_this_run": int(result.num_new_n2_simulations),
        "num_resumed_n2_queries": int(
            result.num_unique_n2_queries - result.num_new_n2_simulations
        ),
        "num_n1_state_constructions_this_run": int(
            result.num_n1_state_constructions
        ),
        "cumulative_n1_state_constructions": int(
            previous_cumulative_n1_calls
            + result.num_n1_state_constructions
        ),
        "cumulative_n2_simulations": int(result.num_unique_n2_queries),
        "total_physical_operations_this_run": int(
            result.num_n1_state_constructions + result.num_new_n2_simulations
        ),
        "cumulative_total_physical_operations": int(
            previous_cumulative_n1_calls
            + result.num_n1_state_constructions
            + result.num_unique_n2_queries
        ),
        "num_critical_discoveries": int(critical.sum()),
        "observed_query_precision": float(
            critical.mean() if len(critical) else 0.0
        ),
        "num_relay_cascade_discoveries": int(relay.sum()),
        "num_overload_relay_activity_paths": int(relay_activity.sum()),
        "num_error_queries": int(errors.sum()),
        "captured_load_shed_mw": float(
            pd.to_numeric(
                query_table.get("total_load_shed_mw", pd.Series(dtype=float)),
                errors="coerce",
            ).fillna(0.0).sum()
        ),
        "search_stage_counts": {
            str(name): int(value) for name, value in stage_counts.items()
        },
        "search_stage_metrics": stage_summary.to_dict(orient="records"),
        "gate_second_lines": list(gate_lines),
        "probe_paths": list(result.probe_paths),
        "promoted_second_lines": list(result.promoted_second_lines),
        "budget_exhausted": bool(result.budget_exhausted),
        "first_step_critical_lines_observed": [
            str(row["first_line"])
            for row in oracle.first_step_rows
            if _as_bool(row["first_step_critical"])
        ],
        "metric_boundary": (
            "Only discovered positives and physical-call counts are available. "
            "Recall/K90 require a separate post-search audit that was not read "
            "by this policy."
        ),
        "outputs": {
            "query_log": query_path.name,
            "first_step_log": first_step_path.name,
            "config": config_path.name,
            "stage_summary": stage_summary_path.name,
            "top_discoveries": top_path.name,
        },
    }
    _atomic_json(summary, summary_path)
    (output_dir / "ieee118_prospective_oracle_readme.md").write_text(
        "# IEEE118 prospective physical-oracle run\n\n"
        "The frozen gate/probe/GCN policy queried the physical cascade simulator "
        "on demand. It did not read an IEEE118 full-truth CSV. Consequently, "
        "this directory reports discoveries and physical-call counts, not "
        "Recall@K or K90. A later audit may compare the frozen query log with "
        "independently generated truth without changing the ranking.\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    summary = run_prospective_oracle(parse_args(argv))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
