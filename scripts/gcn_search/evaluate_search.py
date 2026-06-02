from __future__ import annotations

import runpy

from ._bootstrap import add_legacy_to_path

add_legacy_to_path()


if __name__ == "__main__":
    runpy.run_module("evaluate_rts79_paper_gcn_search", run_name="__main__")
