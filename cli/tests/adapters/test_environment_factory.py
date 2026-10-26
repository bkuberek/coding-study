from pathlib import Path

import pytest

from coding_study.adapters.environment_factory import (
    conformance_environment,
    load_catalog_environment,
    load_environment,
)
from coding_study.adapters.locations import WorkspaceError
from coding_study.domain.errors import ConfigError
from coding_study.domain.scaffold import WORKSPACE_FIRST_ID
from tests.helpers import SCHEMAS_DIRECTORY, mark_workspace


@pytest.fixture
def content(tmp_path: Path) -> Path:
    content = tmp_path / "content"
    (content / "problems").mkdir(parents=True)
    (content / "schemas").symlink_to(SCHEMAS_DIRECTORY)
    return content


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return mark_workspace(tmp_path / "workspace")


@pytest.fixture
def environ(content: Path, workspace: Path) -> dict[str, str]:
    return {"CSTUDY_CONTENT": str(content), "CSTUDY_WORKSPACE": str(workspace)}


def test_the_workspace_is_the_root(environ, workspace, tmp_path):
    assert load_environment(tmp_path, environ, tmp_path).root == workspace


def test_the_content_root_is_separate(environ, content, tmp_path):
    assert load_environment(tmp_path, environ, tmp_path).content_root == content


def test_the_workspace_is_found_from_a_directory_inside_it(content, workspace, tmp_path):
    inside = workspace / "python" / "practice"
    inside.mkdir(parents=True)
    environment = load_environment(inside, {"CSTUDY_CONTENT": str(content)}, tmp_path)
    assert environment.root == workspace


def test_progress_database_lives_at_the_configured_path_in_the_workspace(environ, workspace):
    config = workspace / "config.toml"
    config.write_text('progress_db = "state/progress.db"\n')
    environment = load_environment(workspace, {**environ, "CSTUDY_CONFIG": str(config)}, workspace)
    environment.progress.active_attempt()
    assert (workspace / "state" / "progress.db").is_file()


def test_invalid_config_is_reported(environ, workspace):
    config = workspace / "config.toml"
    config.write_text("default_lang = 3\n")
    with pytest.raises(ConfigError):
        load_environment(workspace, {**environ, "CSTUDY_CONFIG": str(config)}, workspace)


def test_outside_a_workspace(content, tmp_path):
    with pytest.raises(WorkspaceError):
        load_environment(tmp_path, {"CSTUDY_CONTENT": str(content)}, tmp_path)


def test_a_workspace_problem_overlays_the_catalog(environ, workspace, tmp_path):
    (workspace / "problems" / "5001-pair-sum").mkdir(parents=True)
    environment = load_environment(tmp_path, environ, tmp_path)
    assert environment.files.slugs() == ("pair-sum",)


def test_an_explicit_content_root_is_where_new_problems_go(environ, content, tmp_path):
    destination = load_environment(tmp_path, environ, tmp_path).new_problems
    assert (destination.writer.absolute("x"), destination.first_id) == (content / "x", 1)


def test_bundled_content_sends_new_problems_to_the_workspace(
    content, workspace, tmp_path, monkeypatch
):
    package = tmp_path / "site-packages" / "coding_study"
    package.mkdir(parents=True)
    (package / "content").symlink_to(content, target_is_directory=True)
    monkeypatch.setattr("coding_study.adapters.locations.PACKAGE_DIRECTORY", package)
    environment = load_environment(tmp_path, {"CSTUDY_WORKSPACE": str(workspace)}, tmp_path)
    destination = environment.new_problems
    assert (destination.writer.absolute("x"), destination.first_id) == (
        workspace / "x",
        WORKSPACE_FIRST_ID,
    )


def test_the_catalog_environment_works_outside_a_workspace(content, tmp_path):
    environ = {"CSTUDY_CONTENT": str(content), "XDG_CACHE_HOME": str(tmp_path / "cache")}
    environment = load_catalog_environment(tmp_path / "elsewhere", environ, tmp_path)
    assert environment.root == tmp_path / "cache" / "coding-study" / "catalog"


def test_the_catalog_environment_uses_a_workspace_when_there_is_one(environ, workspace, tmp_path):
    assert load_catalog_environment(tmp_path, environ, tmp_path).root == workspace


def test_conformance_environment_reads_the_conformance_fixtures(environ, content, tmp_path):
    fixture = content / "runners" / "conformance" / "9001-conformance-types"
    fixture.mkdir(parents=True)
    environment = conformance_environment(load_environment(tmp_path, environ, tmp_path))
    assert environment.files.slugs() == ("conformance-types",)
