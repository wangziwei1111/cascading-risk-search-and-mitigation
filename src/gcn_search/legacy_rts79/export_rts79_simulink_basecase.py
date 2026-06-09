from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
from pypower.idx_brch import BR_B, BR_R, BR_STATUS, BR_X, F_BUS, RATE_A, T_BUS
from pypower.idx_bus import BASE_KV, BUS_I, PD, QD
from pypower.idx_gen import GEN_BUS, MBASE, PG, QG

from rts79_cascade import Rts79InitialConfig, run_initial_dcopf


@dataclass(frozen=True)
class Rts79SimulinkBasecaseExportConfig:
    output_dir: str = "results/gcn_search/simulink_dynamic_basecase"
    seed: int = 20260722
    default_inertia_h_s: float = 5.0
    default_damping_pu: float = 1.0


def export_rts79_simulink_basecase(config: Rts79SimulinkBasecaseExportConfig) -> dict:
    out = Path(config.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    state = run_initial_dcopf(Rts79InitialConfig(random_seed=config.seed))
    case = state.case
    buses = _buses(case)
    branches = _branches(case)
    generators = _generators(case, config)
    loads = buses[["bus_id", "pd_mw", "qd_mvar"]].copy()
    line_map = branches[["line_label", "from_bus", "to_bus", "rate_mva", "status"]].copy()
    buses.to_csv(out / "rts79_simulink_buses.csv", index=False, encoding="utf-8-sig")
    branches.to_csv(out / "rts79_simulink_branches.csv", index=False, encoding="utf-8-sig")
    generators.to_csv(out / "rts79_simulink_generators.csv", index=False, encoding="utf-8-sig")
    loads.to_csv(out / "rts79_simulink_loads.csv", index=False, encoding="utf-8-sig")
    line_map.to_csv(out / "rts79_simulink_line_map.csv", index=False, encoding="utf-8-sig")
    metadata = {
        **asdict(config),
        "num_buses": int(len(buses)),
        "num_branches": int(len(branches)),
        "num_generators": int(len(generators)),
        "dynamic_parameter_source": "assumed_defaults",
        "dynamic_parameter_note": "H_s and D_pu are synthetic defaults for a Simulink dynamic validation prototype; they are not verified RTS-79 dynamic data.",
        "model_scope": "simplified swing-equation / DC-network prototype, not EMT and not a production dynamic model",
    }
    (out / "rts79_simulink_basecase.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"output_dir": str(out), "basecase_json": str(out / "rts79_simulink_basecase.json")}


def _buses(case: dict) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "bus_id": case["bus"][:, BUS_I].astype(int),
            "pd_mw": case["bus"][:, PD],
            "qd_mvar": case["bus"][:, QD],
            "base_kv": case["bus"][:, BASE_KV],
        }
    )


def _branches(case: dict) -> pd.DataFrame:
    rows = []
    for idx, row in enumerate(case["branch"], start=1):
        rows.append(
            {
                "line_label": f"L{idx:02d}",
                "from_bus": int(row[F_BUS]),
                "to_bus": int(row[T_BUS]),
                "r_pu": float(row[BR_R]),
                "x_pu": float(row[BR_X]),
                "b_pu": float(row[BR_B]),
                "rate_mva": float(row[RATE_A]),
                "status": int(row[BR_STATUS]),
            }
        )
    return pd.DataFrame(rows)


def _generators(case: dict, config: Rts79SimulinkBasecaseExportConfig) -> pd.DataFrame:
    rows = []
    for idx, row in enumerate(case["gen"], start=1):
        rows.append(
            {
                "gen_id": f"G{idx:02d}",
                "bus_id": int(row[GEN_BUS]),
                "pg_mw": float(row[PG]),
                "qg_mvar": float(row[QG]),
                "mva_base": float(row[MBASE]),
                "H_s": float(config.default_inertia_h_s),
                "D_pu": float(config.default_damping_pu),
                "dynamic_parameter_source": "assumed_defaults",
            }
        )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export RTS-79 simplified dynamic basecase data for MATLAB/Simulink prototype.")
    parser.add_argument("--output-dir", default=Rts79SimulinkBasecaseExportConfig.output_dir)
    parser.add_argument("--seed", type=int, default=Rts79SimulinkBasecaseExportConfig.seed)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    export_rts79_simulink_basecase(Rts79SimulinkBasecaseExportConfig(output_dir=args.output_dir, seed=args.seed))


if __name__ == "__main__":
    main()
