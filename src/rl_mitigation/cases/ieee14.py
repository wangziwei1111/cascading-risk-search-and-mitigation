"""IEEE14 case metadata.

The default case is extracted from PYPOWER case14 so metadata used by
islanding, contingency sampling, and AC power flow share one source.
"""

from __future__ import annotations

from .pypower_case_adapter import make_case_from_pypower_case14


def make_ieee14_case(source: str = "pypower") -> dict:
    if source == "pypower":
        return make_case_from_pypower_case14()
    if source == "paper_like":
        case = make_case_from_pypower_case14()
        case["name"] = "ieee14_paper_like"
        case["source"] = "paper_like_from_pypower_topology"
        return case
    raise ValueError(f"Unknown IEEE14 case source: {source}")
