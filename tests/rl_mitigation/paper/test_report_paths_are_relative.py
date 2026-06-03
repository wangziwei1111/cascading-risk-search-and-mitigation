import json
import re
from pathlib import Path


ABS_PATTERNS = [
    re.compile(r"[A-Za-z]:\\"),
    re.compile(r"/home/"),
    re.compile(r"/Users/"),
]


def test_paper_reports_do_not_contain_local_absolute_paths():
    files = list(Path("results/rl_mitigation/paper").rglob("*.md")) + list(Path("results/rl_mitigation/paper").rglob("*.json"))
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8")
        for pattern in ABS_PATTERNS:
            assert not pattern.search(text), path

