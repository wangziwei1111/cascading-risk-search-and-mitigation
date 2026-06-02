from __future__ import annotations

import sys
from pathlib import Path


def add_legacy_to_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    legacy = root / "src" / "gcn_search" / "legacy_rts79"
    if str(legacy) not in sys.path:
        sys.path.insert(0, str(legacy))
    return root
