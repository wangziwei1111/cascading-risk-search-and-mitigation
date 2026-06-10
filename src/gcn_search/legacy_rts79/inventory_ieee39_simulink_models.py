from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd


SEARCH_TOKENS = (
    "ieee39",
    "ieee 39",
    "39bus",
    "39 bus",
    "newengland",
    "new england",
    "10machine",
    "10-machine",
    "kundur",
)


@dataclass
class ModelInventoryRow:
    model_path: str
    model_name: str
    is_slx_or_mdl: bool
    can_open_in_matlab: bool
    requires_toolboxes: str
    contains_generators: bool
    contains_exciters: bool
    contains_governors: bool
    contains_breakers: bool
    contains_lines: bool
    contains_loads: bool
    contains_measurements: bool
    contains_protection: bool
    likely_model_type: str
    license_or_source_note: str


def inventory_ieee39_simulink_models(
    search_roots: list[str | Path] | None = None,
    output_dir: str | Path = "results/gcn_search/ieee39_graphical_dynamic_model",
    verified_open_paths: list[str | Path] | None = None,
) -> dict[str, str]:
    roots = [Path(p).expanduser() for p in (search_roots or _default_search_roots())]
    verified = {str(Path(p).resolve()).lower() for p in (verified_open_paths or []) if Path(p).exists()}
    candidates = _find_candidate_models(roots)
    rows = [_classify_candidate(path, verified) for path in candidates]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "model_inventory.csv"
    json_path = out / "model_inventory.json"
    table = pd.DataFrame([asdict(row) for row in rows], columns=list(ModelInventoryRow.__annotations__.keys()))
    table.to_csv(csv_path, index=False, encoding="utf-8-sig")
    json_path.write_text(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path), "num_candidates": str(len(rows))}


def _default_search_roots() -> list[Path]:
    home = Path.home()
    roots = [
        Path.cwd(),
        home / "Documents" / "MATLAB" / "Examples",
        home / "Desktop",
        Path("E:/matlab2025a"),
    ]
    return [root for root in roots if root.exists()]


def _find_candidate_models(search_roots: list[Path]) -> list[Path]:
    found: dict[str, Path] = {}
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in ("*.slx", "*.mdl"):
            for path in root.rglob(pattern):
                haystack = str(path).lower().replace("_", " ").replace("-", " ")
                if any(token in haystack for token in SEARCH_TOKENS):
                    found[str(path.resolve()).lower()] = path
    return sorted(found.values(), key=lambda p: str(p).lower())


def _classify_candidate(path: Path, verified_open_paths: set[str]) -> ModelInventoryRow:
    lower_path = str(path).lower()
    name = path.stem
    is_mathworks_example = "matlab" in lower_path and "examples" in lower_path and "ieee39bussystemexample" in lower_path
    is_user_copy = "ieee39bussystemexample" in lower_path and not is_mathworks_example
    can_open = str(path.resolve()).lower() in verified_open_paths
    likely_type = "phasor_RMS" if "ieee39bussystem" in lower_path else "unknown"
    source_note = "MathWorks local example; do not commit copied .slx" if is_mathworks_example else "local user candidate; license must be checked before committing model"
    if is_user_copy:
        source_note = "local user copy of IEEE39BusSystemExample; do not commit copied .slx unless license permits"

    text = lower_path
    return ModelInventoryRow(
        model_path=str(path),
        model_name=name,
        is_slx_or_mdl=path.suffix.lower() in {".slx", ".mdl"},
        can_open_in_matlab=can_open,
        requires_toolboxes="Simulink; Simscape Electrical; Specialized Power Systems likely; Stateflow optional for protection",
        contains_generators="ieee39bussystem" in text,
        contains_exciters="ieee39bussystem" in text,
        contains_governors="ieee39bussystem" in text,
        contains_breakers=False,
        contains_lines="ieee39bussystem" in text,
        contains_loads="ieee39bussystem" in text,
        contains_measurements="ieee39bussystem" in text,
        contains_protection=False,
        likely_model_type=likely_type,
        license_or_source_note=source_note,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inventory local IEEE39/New England Simulink dynamic model candidates.")
    parser.add_argument("--search-root", action="append", default=None, help="Root directory to search; can be repeated.")
    parser.add_argument("--verified-open-path", action="append", default=None, help="Candidate path already verified open in MATLAB.")
    parser.add_argument("--output-dir", default="results/gcn_search/ieee39_graphical_dynamic_model")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = inventory_ieee39_simulink_models(args.search_root, args.output_dir, args.verified_open_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
