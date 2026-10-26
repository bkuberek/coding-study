import pytest


@pytest.fixture(autouse=True)
def no_real_workspace(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch):
    """A command whose environment a test forgot to replace finds no workspace and exits 3: it
    never finds a workspace above the working directory, and never writes a progress.db."""
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(tmp_path_factory.mktemp("no-workspace")))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path_factory.mktemp("cache")))
