from pathlib import Path

import pytest

from coding_study.adapters.locations import (
    ContentRoot,
    ContentRootError,
    WorkspaceError,
    enclosing_content_checkout,
    find_content_root,
    find_workspace,
    workspace_directory,
)
from coding_study.adapters.workspace_marker import MARKER_FILE


def make_content(directory: Path) -> Path:
    (directory / "problems").mkdir(parents=True)
    (directory / "schemas").mkdir()
    return directory


def make_workspace(directory: Path) -> Path:
    marker = directory / MARKER_FILE
    marker.parent.mkdir(parents=True)
    marker.write_text('schema = 1\ncreated_with = "0.1.0"\n')
    return directory


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A source checkout: content at the top, the package two levels below `cli/src`."""
    root = make_content(tmp_path / "checkout")
    (root / "cli" / "src" / "coding_study").mkdir(parents=True)
    return root


def package_of(checkout: Path) -> Path:
    return checkout / "cli" / "src" / "coding_study"


def test_bundled_content_is_used_by_an_installed_package(tmp_path):
    package = tmp_path / "site-packages" / "coding_study"
    make_content(package / "content")
    assert find_content_root({}, package) == ContentRoot(package / "content", editable=False)


def test_a_source_checkout_is_its_own_content_root(checkout):
    assert find_content_root({}, package_of(checkout)) == ContentRoot(checkout, editable=True)


def test_cs_content_overrides_the_bundled_content(tmp_path, checkout):
    package = tmp_path / "site-packages" / "coding_study"
    make_content(package / "content")
    found = find_content_root({"CSTUDY_CONTENT": str(checkout)}, package)
    assert found == ContentRoot(checkout, editable=True)


def test_cs_content_must_hold_problems_and_schemas(tmp_path, checkout):
    (tmp_path / "half").mkdir()
    with pytest.raises(ContentRootError, match="needs problems/ and schemas/"):
        find_content_root({"CSTUDY_CONTENT": str(tmp_path / "half")}, package_of(checkout))


def test_empty_cs_content_is_ignored(checkout):
    assert find_content_root({"CSTUDY_CONTENT": ""}, package_of(checkout)).path == checkout


def test_a_package_without_content_reports_where_it_looked(tmp_path):
    package = tmp_path / "lib" / "coding_study"
    package.mkdir(parents=True)
    with pytest.raises(ContentRootError, match="set CSTUDY_CONTENT"):
        find_content_root({}, package)


def test_cs_workspace_comes_first(tmp_path):
    chosen = make_workspace(tmp_path / "chosen")
    current = make_workspace(tmp_path / "current")
    assert workspace_directory(current, {"CSTUDY_WORKSPACE": str(chosen)}) == chosen


def test_cs_workspace_is_resolved_from_the_current_directory(tmp_path):
    make_workspace(tmp_path / "ws")
    assert workspace_directory(tmp_path, {"CSTUDY_WORKSPACE": "ws"}) == tmp_path / "ws"


def test_the_nearest_marked_ancestor_is_the_workspace(tmp_path):
    workspace = make_workspace(tmp_path / "ws")
    nested = workspace / "python" / "practice"
    nested.mkdir(parents=True)
    assert workspace_directory(nested, {}) == workspace


def test_the_current_directory_is_the_last_resort(tmp_path):
    assert workspace_directory(tmp_path, {}) == tmp_path


def test_find_workspace_returns_a_marked_directory(tmp_path):
    workspace = make_workspace(tmp_path / "ws")
    assert find_workspace(workspace, {}) == workspace


def test_find_workspace_points_at_cs_init_without_a_marker(tmp_path):
    with pytest.raises(WorkspaceError, match=r"no \.cs/workspace\.toml.*cstudy init"):
        find_workspace(tmp_path, {})


def test_find_workspace_checks_an_explicit_directory_too(tmp_path):
    (tmp_path / "plain").mkdir()
    with pytest.raises(WorkspaceError, match="plain"):
        find_workspace(tmp_path, {"CSTUDY_WORKSPACE": str(tmp_path / "plain")})


def test_find_workspace_refuses_a_newer_schema(tmp_path):
    workspace = make_workspace(tmp_path / "ws")
    (workspace / MARKER_FILE).write_text('schema = 2\ncreated_with = "9.0.0"\n')
    with pytest.raises(WorkspaceError, match=r"schema 2.*upgrade cstudy"):
        find_workspace(workspace, {})


def test_find_workspace_reports_an_unreadable_marker(tmp_path):
    workspace = make_workspace(tmp_path / "ws")
    (workspace / MARKER_FILE).write_text("schema = [\n")
    with pytest.raises(WorkspaceError, match=r"workspace\.toml"):
        find_workspace(workspace, {})


def test_a_content_checkout_encloses_its_subdirectories(checkout):
    assert enclosing_content_checkout(checkout / "cli" / "src") == checkout


def test_a_workspace_is_not_a_content_checkout(tmp_path):
    workspace = make_workspace(tmp_path / "ws")
    (workspace / "problems").mkdir()
    assert enclosing_content_checkout(workspace) is None
