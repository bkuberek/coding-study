"""The TypeScript and Python versions of coworking availability are one problem in two languages:
the same cases grade both, against the same vendors, over the same seeded desks. A service project
reads only its own files, so each holds a copy, and these tests keep the copies the same."""

from pathlib import Path

import pytest

from tests.helpers import REPOSITORY_ROOT

TYPESCRIPT = REPOSITORY_ROOT / "problems" / "0277-coworking-availability-typescript"
PYTHON = REPOSITORY_ROOT / "problems" / "0278-coworking-availability-python"


def shared_files() -> list[str]:
    """Every file the two versions share, relative to the problem's directory."""
    mocks = sorted(
        path.relative_to(TYPESCRIPT).as_posix()
        for path in (TYPESCRIPT / "mocks").rglob("*")
        if path.is_file()
    )
    return ["tests.json", "starter/data/desks.json", *mocks]


def files_under(problem: Path, directory: str) -> set[str]:
    return {
        path.relative_to(problem).as_posix()
        for path in (problem / directory).rglob("*")
        if path.is_file()
    }


def test_both_versions_hold_the_same_mock_files():
    assert files_under(PYTHON, "mocks") == files_under(TYPESCRIPT, "mocks")


def test_both_versions_hold_the_same_vendor_documents():
    assert files_under(PYTHON, "starter/vendors") == files_under(TYPESCRIPT, "starter/vendors")


@pytest.mark.parametrize("name", shared_files())
def test_a_shared_file_is_the_same_in_both_versions(name):
    assert (PYTHON / name).read_bytes() == (TYPESCRIPT / name).read_bytes()
