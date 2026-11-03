"""The files a definition names outside the attempt (docs/specs/web-ui.md#definitions-and-library-
files): read as they are, over links, and never from cstudy's build area or the content root,
where the reference solutions are, by the named path or the one its links lead to."""

import os
from pathlib import Path
from urllib.parse import quote

import pytest

from coding_study.entrypoints.web.library_files import (
    LIMIT,
    LibraryRefusalError,
    Reason,
    display_path,
    read_library_file,
)

BUILD = ".cs/build"
REFERENCE = "def solve():\n    return 42\n"
BUILTINS = ".cs/lsp/node_modules/basedpyright/dist/typeshed-fallback/stdlib/builtins.pyi"


@pytest.fixture
def workspace(tmp_path) -> Path:
    root = tmp_path / "ws"
    root.mkdir()
    return root


@pytest.fixture
def content(tmp_path) -> Path:
    root = tmp_path / "content"
    (root / "problems" / "0001-two-sum").mkdir(parents=True)
    (root / "problems" / "0001-two-sum" / "reference.py").write_text(REFERENCE)
    return root


def written(path: Path, text: str = "text\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def read(path: Path | str, workspace: Path, content: Path):
    uri = path if isinstance(path, str) else path.as_uri()
    return read_library_file(uri, workspace, (workspace / BUILD, content))


def refusal(path: Path | str, workspace: Path, content: Path) -> tuple[Reason, str]:
    with pytest.raises(LibraryRefusalError) as refused:
        read(path, workspace, content)
    return refused.value.reason, refused.value.path


# reading


def test_a_file_in_the_workspace_is_read_and_named_relative_to_it(workspace, content):
    written(workspace / BUILTINS, "def sorted(): ...\n")
    found = read(workspace / BUILTINS, workspace, content)
    assert (found.path, found.text) == (BUILTINS, "def sorted(): ...\n")


def test_the_answer_names_the_uri_it_was_asked_for(workspace, content):
    path = written(workspace / "lib" / "a b.py")
    uri = path.as_uri()
    assert read(uri, workspace, content).uri == uri


def test_a_file_outside_the_workspace_is_named_absolute(tmp_path, workspace, content):
    outside = written(tmp_path / "elsewhere" / "typing.pyi")
    assert read(outside, workspace, content).path == str(outside)


def test_a_file_under_the_home_directory_is_named_with_a_tilde(
    tmp_path, workspace, content, monkeypatch
):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    path = written(tmp_path / "home" / ".local" / "lib" / "site.py")
    assert read(path, workspace, content).path == "~/.local/lib/site.py"


def test_a_uri_is_percent_decoded(workspace, content):
    path = written(workspace / "lib" / "café ü.py", "x = 1\n")
    uri = "file://" + quote(str(path))
    assert read(uri, workspace, content).text == "x = 1\n"


def test_localhost_is_this_machine(workspace, content):
    path = written(workspace / "lib" / "a.py")
    assert read(f"file://localhost{path}", workspace, content).text == "text\n"


def test_a_link_is_followed_and_the_named_path_is_shown(tmp_path, workspace, content):
    target = written(tmp_path / "python" / "lib" / "site-packages" / "heapq.py", "# heap\n")
    (workspace / "project").mkdir()
    (workspace / "project" / ".venv").symlink_to(target.parents[2], target_is_directory=True)
    found = read(
        workspace / "project" / ".venv" / "lib" / "site-packages" / "heapq.py", workspace, content
    )
    assert (found.path, found.text) == ("project/.venv/lib/site-packages/heapq.py", "# heap\n")


def test_a_file_of_exactly_4_mib_is_read(workspace, content):
    written(workspace / "big.py", "x" * LIMIT)
    assert len(read(workspace / "big.py", workspace, content).text) == LIMIT


def test_text_beyond_ascii_is_read(workspace, content):
    written(workspace / "uni.py", "# héllo 🌍\n")
    assert read(workspace / "uni.py", workspace, content).text == "# héllo 🌍\n"


# what is not a library file


@pytest.mark.parametrize(
    "uri",
    [
        "jdt://contents/java.base/java.lang/String.class",
        "https://example.com/x.py",
        "untitled:Untitled-1",
        "file://other-host/etc/passwd",
        "file:relative/path.py",
        "file:///etc/hosts#L3",
        "file:///etc/hosts?x=1",
        "file://[::1/x",
        "/etc/hosts",
        "",
    ],
)
def test_a_uri_that_is_not_a_local_file_is_refused(workspace, content, uri):
    assert refusal(uri, workspace, content) == (Reason.NOT_A_FILE_URI, uri)


# the build area and the content root


def test_a_file_under_the_build_area_is_refused(workspace, content):
    solution = written(workspace / BUILD / "python" / "reference" / "two_sum" / "hash_map.py")
    assert refusal(solution, workspace, content) == (
        Reason.BUILD_AREA,
        ".cs/build/python/reference/two_sum/hash_map.py",
    )


def test_a_file_that_is_not_there_under_the_build_area_is_refused_not_missing(workspace, content):
    assert refusal(workspace / BUILD / "none.py", workspace, content)[0] is Reason.BUILD_AREA


def test_the_build_area_itself_is_refused(workspace, content):
    (workspace / BUILD).mkdir(parents=True)
    assert refusal(workspace / BUILD, workspace, content)[0] is Reason.BUILD_AREA


def test_a_file_of_the_content_root_is_refused(workspace, content):
    reference = content / "problems" / "0001-two-sum" / "reference.py"
    assert refusal(reference, workspace, content)[0] is Reason.BUILD_AREA


def test_a_path_that_climbs_into_the_build_area_is_refused(workspace, content):
    written(workspace / BUILD / "python" / "x.py")
    (workspace / "python").mkdir()
    climbing = f"{workspace}/python/../{BUILD}/python/x.py"
    assert refusal(Path(climbing), workspace, content)[0] is Reason.BUILD_AREA


def test_a_link_in_the_workspace_to_the_build_area_is_refused(workspace, content):
    written(workspace / BUILD / "python" / "x.py", REFERENCE)
    (workspace / "shortcut").symlink_to(workspace / BUILD, target_is_directory=True)
    reason, shown = refusal(workspace / "shortcut" / "python" / "x.py", workspace, content)
    assert (reason, shown) == (Reason.BUILD_AREA, "shortcut/python/x.py")


def test_a_link_to_a_file_of_the_build_area_is_refused(workspace, content):
    solution = written(workspace / BUILD / "python" / "x.py", REFERENCE)
    link = workspace / "python" / "solution.py"
    link.parent.mkdir()
    link.symlink_to(solution)
    assert refusal(link, workspace, content)[0] is Reason.BUILD_AREA


def test_a_link_to_the_content_root_is_refused(workspace, content):
    (workspace / "lib").symlink_to(content, target_is_directory=True)
    reference = workspace / "lib" / "problems" / "0001-two-sum" / "reference.py"
    assert refusal(reference, workspace, content)[0] is Reason.BUILD_AREA


def test_a_chain_of_links_to_the_content_root_is_refused(tmp_path, workspace, content):
    (tmp_path / "hop").symlink_to(content, target_is_directory=True)
    (workspace / "lib").symlink_to(tmp_path / "hop", target_is_directory=True)
    assert refusal(workspace / "lib" / "problems", workspace, content)[0] is Reason.BUILD_AREA


def test_a_link_under_the_build_area_is_refused_though_it_leads_elsewhere(
    tmp_path, workspace, content
):
    harmless = written(tmp_path / "elsewhere" / "ok.py")
    (workspace / BUILD).mkdir(parents=True)
    (workspace / BUILD / "ok.py").symlink_to(harmless)
    assert refusal(workspace / BUILD / "ok.py", workspace, content)[0] is Reason.BUILD_AREA


def test_a_link_to_the_workspace_root_does_not_hide_the_build_area(tmp_path, workspace, content):
    written(workspace / BUILD / "x.py")
    (tmp_path / "back").symlink_to(workspace, target_is_directory=True)
    assert refusal(tmp_path / "back" / BUILD / "x.py", workspace, content)[0] is Reason.BUILD_AREA


def test_other_hidden_directories_of_the_workspace_are_readable(workspace, content):
    written(workspace / ".cs" / "runtime" / "support.py", "# support\n")
    assert (
        read(workspace / ".cs" / "runtime" / "support.py", workspace, content).text == "# support\n"
    )


def test_a_name_that_only_starts_like_the_build_area_is_readable(workspace, content):
    written(workspace / ".cs" / "build-notes" / "a.txt", "notes\n")
    assert read(workspace / ".cs" / "build-notes" / "a.txt", workspace, content).text == "notes\n"


def test_the_build_area_is_found_by_what_it_is_on_a_case_insensitive_file_system(
    workspace, content
):
    written(workspace / BUILD / "x.py")
    if not (workspace / ".CS").exists():
        pytest.skip("this file system tells .cs from .CS")
    assert refusal(workspace / ".CS" / "BUILD" / "x.py", workspace, content)[0] is Reason.BUILD_AREA


def test_a_content_root_that_is_not_there_hides_nothing(tmp_path, workspace):
    written(workspace / "a.py")
    assert read_library_file((workspace / "a.py").as_uri(), workspace, (tmp_path / "none",)).text


# what is not a readable file


def test_a_file_that_is_not_there_is_missing(workspace, content):
    assert refusal(workspace / "none.py", workspace, content) == (Reason.MISSING, "none.py")


def test_a_link_that_leads_nowhere_is_missing(workspace, content):
    (workspace / "dangling.py").symlink_to(workspace / "gone.py")
    assert refusal(workspace / "dangling.py", workspace, content)[0] is Reason.MISSING


def test_a_nul_in_the_path_is_missing(workspace, content):
    assert refusal("file://" + str(workspace) + "/a%00.py", workspace, content)[0] is Reason.MISSING


def test_a_directory_is_not_a_regular_file(workspace, content):
    (workspace / "lib").mkdir()
    assert refusal(workspace / "lib", workspace, content) == (Reason.NOT_A_FILE, "lib")


def test_a_link_to_a_directory_is_not_a_regular_file(workspace, content):
    (workspace / "lib").mkdir()
    (workspace / "shortcut").symlink_to(workspace / "lib", target_is_directory=True)
    assert refusal(workspace / "shortcut", workspace, content)[0] is Reason.NOT_A_FILE


def test_a_pipe_is_not_a_regular_file_and_is_not_waited_for(workspace, content):
    os.mkfifo(workspace / "pipe")
    assert refusal(workspace / "pipe", workspace, content)[0] is Reason.NOT_A_FILE


def test_a_file_over_4_mib_is_too_large(workspace, content):
    written(workspace / "big.py", "x" * (LIMIT + 1))
    assert refusal(workspace / "big.py", workspace, content) == (Reason.TOO_LARGE, "big.py")


def test_a_file_that_is_not_utf8_is_not_text(workspace, content):
    (workspace / "binary.so").write_bytes(b"\x7fELF\xff\xfe\x00")
    assert refusal(workspace / "binary.so", workspace, content) == (Reason.NOT_TEXT, "binary.so")


def test_size_is_checked_before_the_encoding(workspace, content):
    (workspace / "big.bin").write_bytes(b"\xff" * (LIMIT + 1))
    assert refusal(workspace / "big.bin", workspace, content)[0] is Reason.TOO_LARGE


# the reasons


def test_every_reason_has_the_message_of_the_spec():
    assert {reason: reason.message for reason in Reason} == {
        Reason.NOT_A_DEFINITION: "not a definition target of this session",
        Reason.NOT_A_FILE_URI: "not a file: URI",
        Reason.BUILD_AREA: "not shown: cstudy's build area",
        Reason.MISSING: "no such file",
        Reason.NOT_A_FILE: "not a regular file",
        Reason.TOO_LARGE: "over 4 MiB",
        Reason.NOT_TEXT: "not UTF-8 text",
    }


def test_a_displayed_path_is_relative_to_the_workspace_when_inside_it(workspace):
    assert display_path(workspace / "python" / "x.py", workspace) == "python/x.py"
