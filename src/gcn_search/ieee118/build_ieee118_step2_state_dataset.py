from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from pypower.idx_brch import BR_B, BR_STATUS, BR_X, F_BUS, PF, RATE_A, T_BUS
from pypower.idx_bus import BUS_I, BUS_TYPE, PD, VA
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG

ROOT = Path(__file__).resolve().parents[3]
LEGACY = ROOT / "src" / "gcn_search" / "legacy_rts79"
sys.path.insert(0, str(LEGACY))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from case_adapter import build_branch_table, build_case_adapter, run_sequential_outages_for_case
from generate_ieee118_ordered_n2_fulltruth import apply_ieee118_load_scenario, apply_thermal_limit_mode


REQUIRED_FULLTRUTH_COLUMNS = {
    "scenario_id",
    "seed",
    "path",
    "first_line",
    "second_line",
    "critical",
    "critical_mechanism",
    "has_overload_cascade",
    "total_load_shed_mw",
    "num_relay_trips",
    "max_event_loading_ratio",
}

SAMPLE_COLUMNS = [
    "sample_id",
    "scenario_id",
    "seed",
    "path",
    "first_line",
    "second_line",
    "critical",
    "critical_mechanism",
    "has_overload_cascade",
    "relay_cascade",
    "total_load_shed_mw",
    "num_relay_trips",
    "max_event_loading_ratio",
    "label_critical",
    "label_relay_cascade",
    "label_load_shed_positive",
    "first_line_loading_ratio",
    "candidate_second_line_loading_ratio",
    "candidate_second_line_rate_a",
    "candidate_second_line_pf",
    "lodf_or_dc_sensitivity_if_available",
    "node_features_json",
    "edge_features_json",
    "path_features_json",
]

NODE_FEATURE_COLUMNS = [
    "bus_id",
    "bus_type",
    "Pd",
    "Pg",
    "net_injection",
    "voltage_angle_or_dc_theta",
    "is_islanded_component",
    "component_id",
]

EDGE_FEATURE_COLUMNS = [
    "line_label",
    "from_bus",
    "to_bus",
    "x",
    "b",
    "rate_a",
    "pf_after_first_outage",
    "abs_pf_after_first_outage",
    "loading_ratio_after_first_outage",
    "is_first_outage",
    "is_candidate_second_outage",
]

PATH_FEATURE_COLUMNS = [
    "first_line_loading_ratio",
    "candidate_second_line_loading_ratio",
    "candidate_second_line_rate_a",
    "candidate_second_line_pf",
    "lodf_or_dc_sensitivity_if_available",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build IEEE118 Step2-State samples from flow-scaled full truth.")
    parser.add_argument(
        "--fulltruth-csv",
        type=Path,
        default=ROOT
        / "results"
        / "gcn_search"
        / "ieee118_flow_scaled_800_fulltruth_seed20260708"
        / "ieee118_fulltruth_summary.csv",
    )
    parser.add_argument("--limit-mode", choices=["original_rate_a", "flow_scaled"], default="flow_scaled")
    parser.add_argument("--flow-limit-scale", type=float, default=8.0)
    parser.add_argument("--min-rate-a", type=float, default=1.0)
    parser.add_argument("--load-scale", type=float, default=1.0)
    parser.add_argument("--beta", type=float, default=1.2)
    parser.add_argument("--security-limit", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=20260708)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "gcn_search" / "ieee118_flow_scaled_800_step2_state",
    )
    parser.add_argument("--max-first-lines", type=int, default=None, help="Optional smoke cap on unique first_line values.")
    parser.add_argument("--max-samples", type=int, default=None, help="Optional smoke cap on total output samples.")
    return parser.parse_args()


def load_fulltruth(path: Path, *, seed: int, max_first_lines: int | None, max_samples: int | None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing IEEE118 full-truth CSV: {path}. Generate it locally first; the raw 34,410-row CSV is intentionally not tracked in git."
        )
    table = pd.read_csv(path)
    missing = sorted(REQUIRED_FULLTRUTH_COLUMNS - set(table.columns))
    if missing:
        raise ValueError(f"Full-truth CSV is missing required columns: {missing}")
    table = table.loc[table["seed"].astype(int) == int(seed)].copy()
    if table.empty:
        raise ValueError(f"Full-truth CSV contains no rows for seed={seed}")
    if max_first_lines is not None:
        first_lines = list(dict.fromkeys(table["first_line"].astype(str).tolist()))[:max_first_lines]
        table = table.loc[table["first_line"].astype(str).isin(first_lines)].copy()
    if max_samples is not None:
        table = table.head(max_samples).copy()
    return table.reset_index(drop=True)


def make_scenario_case(*, seed: int, load_scale: float, limit_mode: str, flow_limit_scale: float, min_rate_a: float) -> tuple[Any, dict]:
    adapter = build_case_adapter("ieee118")
    scenario_case = apply_ieee118_load_scenario(adapter.case, seed=seed, load_scale=load_scale)
    scenario_case = apply_thermal_limit_mode(
        scenario_case,
        limit_mode=limit_mode,
        flow_limit_scale=flow_limit_scale,
        min_rate_a=min_rate_a,
    )
    return adapter, scenario_case


def component_map(case: dict) -> dict[int, tuple[int, bool]]:
    graph = nx.Graph()
    bus_ids = [int(row[BUS_I]) for row in case["bus"]]
    graph.add_nodes_from(bus_ids)
    for row in case["branch"]:
        if int(row[BR_STATUS]) == 1:
            graph.add_edge(int(row[F_BUS]), int(row[T_BUS]))
    components = [sorted(component) for component in nx.connected_components(graph)]
    is_split = len(components) > 1
    mapping: dict[int, tuple[int, bool]] = {}
    for component_id, buses in enumerate(components, start=1):
        for bus_id in buses:
            mapping[bus_id] = (component_id, is_split)
    return mapping


def build_node_features(case: dict) -> list[dict]:
    gen_by_bus: dict[int, float] = {}
    for row in case["gen"]:
        if int(row[GEN_STATUS]) > 0:
            bus_id = int(row[GEN_BUS])
            gen_by_bus[bus_id] = gen_by_bus.get(bus_id, 0.0) + float(row[PG])
    components = component_map(case)
    records = []
    for row in case["bus"]:
        bus_id = int(row[BUS_I])
        pd_mw = float(row[PD])
        pg_mw = float(gen_by_bus.get(bus_id, 0.0))
        component_id, is_islanded = components.get(bus_id, (0, False))
        records.append(
            {
                "bus_id": bus_id,
                "bus_type": int(row[BUS_TYPE]),
                "Pd": pd_mw,
                "Pg": pg_mw,
                "net_injection": pg_mw - pd_mw,
                "voltage_angle_or_dc_theta": float(row[VA]),
                "is_islanded_component": bool(is_islanded),
                "component_id": int(component_id),
            }
        )
    return records


def build_edge_features(case: dict, adapter: Any, first_line: str, second_line: str) -> list[dict]:
    branch_table = build_branch_table(case, adapter)
    branch = case["branch"]
    records = []
    for idx, row in branch_table.iterrows():
        records.append(
            {
                "line_label": str(row["line_label"]),
                "from_bus": int(row["from_bus"]),
                "to_bus": int(row["to_bus"]),
                "x": float(branch[idx, BR_X]),
                "b": float(branch[idx, BR_B]),
                "rate_a": float(row["F_max_MW"]),
                "pf_after_first_outage": float(row["F_MW"]),
                "abs_pf_after_first_outage": float(row["abs_F_MW"]),
                "loading_ratio_after_first_outage": float(row["loading_ratio"]),
                "is_first_outage": str(row["line_label"]) == first_line,
                "is_candidate_second_outage": str(row["line_label"]) == second_line,
            }
        )
    return records


def find_line_feature(edge_features: list[dict], line_label: str, key: str) -> float:
    for edge in edge_features:
        if edge["line_label"] == line_label:
            return float(edge[key])
    return 0.0


def json_dumps(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def bool_from_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def build_step2_state_dataset(args: argparse.Namespace) -> pd.DataFrame:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    fulltruth = load_fulltruth(
        args.fulltruth_csv,
        seed=args.seed,
        max_first_lines=args.max_first_lines,
        max_samples=args.max_samples,
    )
    adapter, scenario_case = make_scenario_case(
        seed=args.seed,
        load_scale=args.load_scale,
        limit_mode=args.limit_mode,
        flow_limit_scale=args.flow_limit_scale,
        min_rate_a=args.min_rate_a,
    )

    first_state_cache: dict[str, dict] = {}
    graph_feature_cache: dict[str, tuple[str, str, list[dict]]] = {}
    rows: list[dict] = []
    cache_hits = 0
    cache_misses = 0
    for sample_id, truth in enumerate(fulltruth.to_dict("records"), start=1):
        first_line = adapter.normalize_line_label(str(truth["first_line"]))
        second_line = adapter.normalize_line_label(str(truth["second_line"]))
        if first_line not in first_state_cache:
            first_state_cache[first_line] = run_sequential_outages_for_case(
                scenario_case,
                adapter,
                [first_line],
                beta=args.beta,
                security_limit=args.security_limit,
            )
            cache_misses += 1
        else:
            cache_hits += 1

        first_state = first_state_cache[first_line]
        if first_line not in graph_feature_cache:
            node_features = build_node_features(first_state["case"])
            edge_features = build_edge_features(first_state["case"], adapter, first_line, second_line="")
            graph_feature_cache[first_line] = (json_dumps(node_features), json_dumps(edge_features), edge_features)
        node_json, _, base_edge_features = graph_feature_cache[first_line]
        edge_features = [
            {**edge, "is_candidate_second_outage": edge["line_label"] == second_line} for edge in base_edge_features
        ]

        first_loading = find_line_feature(edge_features, first_line, "loading_ratio_after_first_outage")
        candidate_loading = find_line_feature(edge_features, second_line, "loading_ratio_after_first_outage")
        candidate_rate = find_line_feature(edge_features, second_line, "rate_a")
        candidate_pf = find_line_feature(edge_features, second_line, "pf_after_first_outage")
        relay_cascade = str(truth["critical_mechanism"]) == "relay_cascade"
        critical = bool_from_value(truth["critical"])
        load_shed = float(truth["total_load_shed_mw"])
        path_features = {
            "first_line_loading_ratio": first_loading,
            "candidate_second_line_loading_ratio": candidate_loading,
            "candidate_second_line_rate_a": candidate_rate,
            "candidate_second_line_pf": candidate_pf,
            "lodf_or_dc_sensitivity_if_available": None,
        }
        rows.append(
            {
                "sample_id": sample_id,
                "scenario_id": int(truth["scenario_id"]),
                "seed": int(truth["seed"]),
                "path": str(truth["path"]),
                "first_line": first_line,
                "second_line": second_line,
                "critical": critical,
                "critical_mechanism": str(truth["critical_mechanism"]),
                "has_overload_cascade": bool_from_value(truth["has_overload_cascade"]),
                "relay_cascade": relay_cascade,
                "total_load_shed_mw": load_shed,
                "num_relay_trips": int(truth["num_relay_trips"]),
                "max_event_loading_ratio": float(truth["max_event_loading_ratio"]),
                "label_critical": int(critical),
                "label_relay_cascade": int(relay_cascade),
                "label_load_shed_positive": int(load_shed > 1e-7),
                "first_line_loading_ratio": first_loading,
                "candidate_second_line_loading_ratio": candidate_loading,
                "candidate_second_line_rate_a": candidate_rate,
                "candidate_second_line_pf": candidate_pf,
                "lodf_or_dc_sensitivity_if_available": np.nan,
                "node_features_json": node_json,
                "edge_features_json": json_dumps(edge_features),
                "path_features_json": json_dumps(path_features),
            }
        )

    sample_table = pd.DataFrame(rows, columns=SAMPLE_COLUMNS)
    sample_table.to_csv(output_dir / "ieee118_step2_state_samples.csv", index=False, encoding="utf-8-sig")
    write_schema(output_dir)
    write_metadata(output_dir, args, sample_table, len(adapter.line_labels), cache_hits, cache_misses)
    write_readme(output_dir, sample_table, cache_hits, cache_misses)
    return sample_table


def write_schema(output_dir: Path) -> None:
    schema = {
        "sample_columns": SAMPLE_COLUMNS,
        "node_features": NODE_FEATURE_COLUMNS,
        "edge_features": EDGE_FEATURE_COLUMNS,
        "path_features": PATH_FEATURE_COLUMNS,
        "json_columns": {
            "node_features_json": "List[Dict[node feature name, value]] with one record per bus.",
            "edge_features_json": "List[Dict[edge feature name, value]] with one record per branch.",
            "path_features_json": "Dict of scalar first/candidate path features.",
        },
    }
    (output_dir / "ieee118_step2_state_feature_schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")


def write_metadata(
    output_dir: Path,
    args: argparse.Namespace,
    sample_table: pd.DataFrame,
    num_lines: int,
    cache_hits: int,
    cache_misses: int,
) -> None:
    metadata = {
        "case_name": "ieee118",
        "source_fulltruth_csv": str(args.fulltruth_csv),
        "limit_mode": args.limit_mode,
        "flow_limit_scale": args.flow_limit_scale,
        "min_rate_a": args.min_rate_a,
        "seed": args.seed,
        "num_lines": num_lines,
        "expected_full_samples": num_lines * (num_lines - 1),
        "num_samples": int(len(sample_table)),
        "num_unique_first_lines": int(sample_table["first_line"].nunique()) if not sample_table.empty else 0,
        "critical_samples": int(sample_table["label_critical"].sum()) if not sample_table.empty else 0,
        "critical_ratio": float(sample_table["label_critical"].mean()) if not sample_table.empty else 0.0,
        "relay_cascade_samples": int(sample_table["label_relay_cascade"].sum()) if not sample_table.empty else 0,
        "relay_cascade_ratio": float(sample_table["label_relay_cascade"].mean()) if not sample_table.empty else 0.0,
        "first_state_cache_hits": int(cache_hits),
        "first_state_cache_misses": int(cache_misses),
        "max_first_lines": args.max_first_lines,
        "max_samples": args.max_samples,
        "full_dataset_csv_tracked_in_git": False,
        "notes": "Labels come directly from the supplied full-truth CSV; critical is not recomputed here.",
    }
    (output_dir / "ieee118_step2_state_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def write_readme(output_dir: Path, sample_table: pd.DataFrame, cache_hits: int, cache_misses: int) -> None:
    lines = [
        "# IEEE118 Flow-Scaled 8.00 Step2-State Dataset",
        "",
        "This dataset builds second-step candidate graph samples from the IEEE118 `flow_scaled=8.00`, `min-rate-a=1.0` full-truth table.",
        "",
        f"- Samples: {len(sample_table)}",
        f"- Critical samples: {int(sample_table['label_critical'].sum()) if not sample_table.empty else 0}",
        f"- Relay-cascade samples: {int(sample_table['label_relay_cascade'].sum()) if not sample_table.empty else 0}",
        f"- First-state cache misses: {cache_misses}",
        f"- First-state cache hits: {cache_hits}",
        "",
        "The full dataset CSV can be large and should remain local unless explicitly approved. This stage does not train a GCN or evaluate search efficiency.",
    ]
    (output_dir / "ieee118_step2_state_readme.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    table = build_step2_state_dataset(args)
    print(f"IEEE118 Step2-State samples written to {args.output_dir / 'ieee118_step2_state_samples.csv'}")
    print(f"num_samples={len(table)}")
    print(f"num_critical={int(table['label_critical'].sum()) if not table.empty else 0}")
    print(f"num_relay_cascade={int(table['label_relay_cascade'].sum()) if not table.empty else 0}")


if __name__ == "__main__":
    main()
