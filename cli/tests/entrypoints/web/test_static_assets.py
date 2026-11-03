"""The front end committed under entrypoints/web/static/: its manifest records every file's SHA-256,
the wheel ships every file, and a rebuild from tools/web-ui/ gives the same bytes
(docs/specs/web-ui.md#front-end-assets). The wheel also ships the script that keeps the hidden
directories from a language server (docs/specs/web-ui.md#hidden-directories)."""

import hashlib
import json
import shutil
import subprocess
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

import pytest

from tests.helpers import REPOSITORY_ROOT

STATIC = REPOSITORY_ROOT / "cli" / "src" / "coding_study" / "entrypoints" / "web" / "static"
MANIFEST_NAME = "manifest.json"
LICENSE_NOTICE = "THIRD_PARTY_LICENSES.txt"
BUILD_SCRIPT = REPOSITORY_ROOT / "tools" / "web-ui" / "build.sh"
HIDE_PATHS = PurePosixPath("cli/src/coding_study/entrypoints/web/hide_paths.cjs")
REQUIRED_NODE = 24
"""build.sh's `required_node`."""


def manifest() -> dict[str, Any]:
    return json.loads((STATIC / MANIFEST_NAME).read_text())


def digests(directory: Path) -> dict[str, str]:
    """Each file under the directory, by its `/`-separated relative path, with its SHA-256."""
    return {
        path.relative_to(directory).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


def repository_paths() -> list[PurePosixPath]:
    """The manifest and every file it names, relative to the repository root, as hatch sees them."""
    static = PurePosixPath(STATIC.relative_to(REPOSITORY_ROOT).as_posix())
    return [static / name for name in (MANIFEST_NAME, *manifest()["files"])]


def excluded_by(path: PurePosixPath, pattern: str) -> bool:
    """Whether a hatch `exclude` pattern names the path or a directory holding it."""
    return path.full_match(pattern) or path.full_match(f"{pattern}/**")


def wheel_selects(path: PurePosixPath) -> bool:
    """Whether pyproject.toml's `only-include` and `exclude` settings put the path in the wheel."""
    pyproject = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text())
    build = pyproject["tool"]["hatch"]["build"]
    wheel = build["targets"]["wheel"]
    included = any(path.is_relative_to(root) for root in wheel["only-include"])
    patterns = [*build.get("exclude", []), *wheel.get("exclude", [])]
    return included and not any(excluded_by(path, pattern) for pattern in patterns)


def node_major_version() -> int | None:
    if shutil.which("node") is None or shutil.which("pnpm") is None:
        return None
    printed = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True)
    return int(printed.stdout.strip().removeprefix("v").split(".")[0])


def test_the_manifest_records_the_digest_of_every_static_file():
    on_disk = {path: digest for path, digest in digests(STATIC).items() if path != MANIFEST_NAME}
    assert on_disk == manifest()["files"]


def test_the_manifest_names_an_entry_module_it_records():
    entry = manifest()["entry"]
    assert entry in manifest()["files"]


def test_the_static_files_carry_the_third_party_license_notice():
    assert LICENSE_NOTICE in manifest()["files"]


def test_the_wheel_settings_select_every_static_file():
    assert [path for path in repository_paths() if not wheel_selects(path)] == []


def test_the_wheel_ships_the_script_that_hides_directories_from_a_language_server():
    assert (wheel_selects(HIDE_PATHS), (REPOSITORY_ROOT / HIDE_PATHS).is_file()) == (True, True)


def test_git_does_not_ignore_the_script_that_hides_directories_from_a_language_server():
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", str(HIDE_PATHS)],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ignored.stdout.split() == []


def test_git_ignores_no_static_file():
    """hatch leaves files the repository ignores out of the wheel."""
    listed = "\n".join(str(path) for path in repository_paths())
    ignored = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin"],
        cwd=REPOSITORY_ROOT,
        input=listed,
        capture_output=True,
        text=True,
        check=False,
    )
    assert ignored.stdout.split() == []


@pytest.mark.slow
def test_a_rebuild_reproduces_the_committed_static_files(tmp_path):
    found = node_major_version()
    if found is None or found < REQUIRED_NODE:
        pytest.skip(f"needs pnpm and node {REQUIRED_NODE} or later on PATH (found node {found})")
    rebuilt = tmp_path / "static"
    subprocess.run(["bash", str(BUILD_SCRIPT), str(rebuilt)], check=True, capture_output=True)
    assert digests(rebuilt) == digests(STATIC)
