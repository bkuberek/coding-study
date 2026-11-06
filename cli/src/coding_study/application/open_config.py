"""`cstudy config edit`: the user's `config.toml` in their editor, made from the commented template
when they have none (docs/specs/cli.md#cstudy-config)."""

from dataclasses import dataclass
from pathlib import Path

from coding_study.application.ports import EditableConfig, EditorOpener


@dataclass(frozen=True, slots=True)
class OpenedConfig:
    created: bool
    """There was no file, so this call wrote the template."""
    editor_problem: str | None
    """Why no editor opened it, as the editor's opener words it."""


def open_config(file: EditableConfig, editor: EditorOpener) -> OpenedConfig:
    created = file.create_from_template()
    return OpenedConfig(created, editor.open([Path(file.location)]))
