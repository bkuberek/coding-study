"""The files beside a service project's mock config: the bodies it names and the vendor's
documentation (docs/specs/service-projects.md#where-the-files-live).

A file that is not there, or a name that leads out of the config's folder, is simply not held: S20
says what is wrong with it, and rendering refuses to go on without it.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import cast

from coding_study.domain.mock_configs import API_SUFFIX, BODY_FILE, MockFiles, response_fields
from coding_study.domain.project import PATH_SEPARATOR, relative_path_issue


def mock_files(config: Path, document: Mapping[str, object]) -> MockFiles:
    """`document` is the parsed, schema-valid file at `config`."""
    folder = config.parent
    names = {
        cast(str, fields[BODY_FILE])
        for _where, fields in response_fields(MockFiles(document))
        if BODY_FILE in fields
    }
    bodies = {
        name: _text(folder / name)
        for name in names
        if relative_path_issue(name) is None and _holds(folder, name)
    }
    api = config.with_suffix(API_SUFFIX).name
    return MockFiles(document, bodies, _text(folder / api) if _holds(folder, api) else None)


def _holds(folder: Path, name: str) -> bool:
    """A link on the way is never followed: it could name anything on this machine."""
    step = folder
    for segment in name.split(PATH_SEPARATOR):
        step /= segment
        if step.is_symlink():
            return False
    return step.is_file()


def _text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None
