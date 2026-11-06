"""`cstudy config edit`: the user's `config.toml` in their editor, made from the commented template
when they have none (docs/specs/cli.md#cstudy-config)."""

from dataclasses import dataclass
from pathlib import Path

from coding_study.application.ports import EditableConfig, EditorOpener
from coding_study.domain.errors import ConfigError


@dataclass(frozen=True, slots=True)
class ProgressDbChange:
    current: str
    new: str


@dataclass(frozen=True, slots=True)
class OpenedConfig:
    created: bool
    """There was no file, so this call wrote the template."""
    editor_problem: str | None
    """Why no editor opened it, as the editor's opener words it."""
    progress_db: ProgressDbChange | None
    """The edit changed the path of the database, which moves nothing."""


def open_config(file: EditableConfig, editor: EditorOpener) -> OpenedConfig:
    """Raises ConfigError when the file does not load once the editor closed. A file that did not
    load before opens all the same, so it can be fixed."""
    created = file.create_from_template()
    before = _progress_db(file)
    problem = editor.open([Path(file.location)])
    after = file.load().progress_db
    change = ProgressDbChange(before, after) if before is not None and before != after else None
    return OpenedConfig(created, problem, change)


def _progress_db(file: EditableConfig) -> str | None:
    try:
        return file.load().progress_db
    except ConfigError:
        return None
