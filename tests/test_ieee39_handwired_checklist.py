from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_ieee39_handwired_checklist_script_generates_steps() -> None:
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts/gcn_search/print_ieee39_handwired_breaker_checklist.py"
    output = root / "results/gcn_search/ieee39_graphical_dynamic_model/handwired_breaker_validation/handwired_breaker_checklist.txt"
    result = subprocess.run([sys.executable, str(script)], cwd=root, text=True, capture_output=True, check=True)
    assert "L01_HandwiredTimedBreaker" in result.stdout
    assert "L01_TripCommand" in result.stdout
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "Do not commit generated or handwired .slx files" in text
    assert "validate_ieee39_handwired_breaker_model" in text
