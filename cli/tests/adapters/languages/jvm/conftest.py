from pathlib import Path

import pytest

from tests.adapters.languages.jvm.fake_gradle import WORKSPACE_FILES


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A workspace root whose `jvm/` project has the build files the reference build mirrors."""
    workspace = tmp_path / "jvm"
    for relative in WORKSPACE_FILES:
        (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        (workspace / relative).write_text(f"// {relative}\n")
    return tmp_path
