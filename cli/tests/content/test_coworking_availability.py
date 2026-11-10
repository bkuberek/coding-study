"""The TypeScript, Python, Java and Kotlin versions of coworking availability are one problem in four
languages: the same cases grade them all, against the same vendors, over the same seeded desks. A
service project reads only its own files, so each holds a copy, and these tests keep the copies the
same as the TypeScript version's."""

from pathlib import Path

import pytest

from tests.helpers import REPOSITORY_ROOT

PROBLEMS = REPOSITORY_ROOT / "problems"
TYPESCRIPT = PROBLEMS / "0277-coworking-availability-typescript"
OTHER_VERSIONS = {
    "python": PROBLEMS / "0278-coworking-availability-python",
    "java": PROBLEMS / "0305-coworking-availability-java",
    "kotlin": PROBLEMS / "0306-coworking-availability-kotlin",
}


def shared_files() -> list[str]:
    """Every file the versions share, relative to the problem's directory."""
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


@pytest.mark.parametrize("version", OTHER_VERSIONS)
def test_every_version_holds_the_same_mock_files(version):
    assert files_under(OTHER_VERSIONS[version], "mocks") == files_under(TYPESCRIPT, "mocks")


@pytest.mark.parametrize("version", OTHER_VERSIONS)
def test_every_version_holds_the_same_vendor_documents(version):
    found = files_under(OTHER_VERSIONS[version], "starter/vendors")

    assert found == files_under(TYPESCRIPT, "starter/vendors")


@pytest.mark.parametrize("version", OTHER_VERSIONS)
@pytest.mark.parametrize("name", shared_files())
def test_a_shared_file_is_the_same_in_every_version(version, name):
    assert (OTHER_VERSIONS[version] / name).read_bytes() == (TYPESCRIPT / name).read_bytes()
