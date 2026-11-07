"""The environment the slow tests give a real `cstudy serve`: it never reaches the user's config."""

from pathlib import Path

import pytest

from coding_study.adapters.toml_config import config_path
from tests.serve_process import served_environment

HOME = Path("/home/someone")


@pytest.mark.parametrize("from_the_shell", ["/somewhere/else.toml", None], ids=["set", "unset"])
def test_a_served_cstudy_reads_the_config_file_of_its_own_directory(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, from_the_shell: str | None
):
    if from_the_shell is None:
        monkeypatch.delenv("CSTUDY_CONFIG", raising=False)
    else:
        monkeypatch.setenv("CSTUDY_CONFIG", from_the_shell)
    environment = served_environment(tmp_path / "workspace")
    assert config_path(environment, HOME) == tmp_path / "config" / "coding-study" / "config.toml"
