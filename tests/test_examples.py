"""Guard against syntax rot in the example scripts."""

from __future__ import annotations

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"

example_paths = sorted(EXAMPLES_DIR.glob("*.py"))


@pytest.mark.parametrize("example", example_paths, ids=lambda path: path.name)
def test_example_compiles(example: Path) -> None:
    compile(example.read_text(encoding="utf-8"), str(example), "exec")
