"""`config.toml` as the Settings view reads and writes it (docs/specs/web-ui.md#settings-view).

Only the keys that changed are written, by tomlkit, which keeps the user's comments, formatting and
any key this `cstudy` does not know ([ADR 0022](docs/decisions/0022-settings-and-reset.md)). Only
the web server imports this module, so no other command loads tomlkit (NFR-2).
"""

import contextlib
import os
import secrets
import tomllib
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import cast

import tomlkit
from tomlkit.exceptions import ParseError
from tomlkit.toml_document import TOMLDocument

from coding_study.adapters.toml_config import CONFIG_KEYS, config_issues
from coding_study.domain.config_keys import ConfigKey, ConfigKeyState, ConfigView
from coding_study.domain.errors import ConfigError, UsageError

_NEW_FILE_MODE = 0o644
_TEMPORARY_NAME_BYTES = 8
_KEYS_BY_NAME = {key.name: key for key in CONFIG_KEYS}
_NOT_PARSED = "it does not parse, so nothing was written"
type _Table = MutableMapping[str, object]


class TomlConfigFile:
    """`ConfigFile` on the file at `path`, which may be missing, or a link."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def location(self) -> str:
        return str(self._path)

    def read(self) -> ConfigView:
        text = self._text()
        exists = text is not None
        try:
            values = tomllib.loads(text or "")
        except tomllib.TOMLDecodeError as error:
            return ConfigView(self.location, exists, False, (str(error),), _states({}))
        return ConfigView(self.location, exists, True, config_issues(values), _states(values))

    def apply(self, changes: Mapping[str, object]) -> tuple[str, ...]:
        """Writes the values that differ from those in force, null removing a key, and returns
        their names. Raises UsageError, writing nothing, for a key the file can't take or a value
        the CLI would refuse, and ConfigError for a file that does not parse."""
        for name in changes:
            _require_editable(name)
        document = self._document()
        held = document.unwrap()
        before = config_issues(held)
        table = cast(_Table, document)
        changed = tuple(
            name for name, value in changes.items() if _change(table, held, name, value)
        )
        if not changed:
            return ()
        new_issues = [issue for issue in config_issues(document.unwrap()) if issue not in before]
        if new_issues:
            raise UsageError("; ".join(new_issues))
        self._write(tomlkit.dumps(document))
        return changed

    def _text(self) -> str | None:
        try:
            return self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None

    def _document(self) -> TOMLDocument:
        try:
            return tomlkit.parse(self._text() or "")
        except ParseError as error:
            raise ConfigError(self.location, [f"{_NOT_PARSED}: {error}"]) from None

    def _write(self, text: str) -> None:
        """A new file beside the real one, then a rename, so a crash leaves one or the other; a
        link keeps pointing where it did."""
        target = self._path.resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(
            f"{target.name}.{secrets.token_hex(_TEMPORARY_NAME_BYTES)}.tmp"
        )
        mode = target.stat().st_mode & 0o777 if target.exists() else _NEW_FILE_MODE
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                os.fchmod(file.fileno(), mode)
                file.write(text)
                file.flush()
                os.fsync(file.fileno())
            temporary.replace(target)
        finally:
            with contextlib.suppress(FileNotFoundError):
                temporary.unlink()


def _states(values: Mapping[str, object]) -> tuple[ConfigKeyState, ...]:
    return tuple(_state(key, values) for key in CONFIG_KEYS)


def _state(key: ConfigKey, values: Mapping[str, object]) -> ConfigKeyState:
    table = values.get(key.table, {}) if key.table else values
    if not isinstance(table, Mapping) or key.short_name not in table:
        return ConfigKeyState(key, key.default, False)
    held = cast(Mapping[str, object], table)[key.short_name]
    return ConfigKeyState(key, _plain(held), True)


def _plain(value: object) -> object:
    """A value the file holds, as JSON can carry it; a date or a float is invalid in every key."""
    if isinstance(value, bool | int | str):
        return value
    if isinstance(value, list):
        return [_plain(item) for item in cast(list[object], value)]
    return str(value)


def _require_editable(name: str) -> None:
    key = _KEYS_BY_NAME.get(name)
    if key is None:
        raise UsageError(f"{name}: unknown key")
    if key.reserved:
        raise UsageError(f"{name} is reserved: it does nothing yet")


def _change(document: _Table, held: Mapping[str, object], name: str, value: object) -> bool:
    """Sets the key, or removes it for null; False when that would change nothing. `held` is what
    the document holds, as plain values."""
    key = _KEYS_BY_NAME[name]
    state = _state(key, held)
    if value is None:
        if not state.is_set:
            return False
        del _writable_table(document, key)[key.short_name]
        return True
    if _same(value, state.value):
        return False
    _writable_table(document, key)[key.short_name] = value
    return True


def _writable_table(document: _Table, key: ConfigKey) -> _Table:
    """The table that holds `key`, made when missing; the document for a top-level key. Raises
    UsageError for a value of that name that is not a table."""
    if not key.table:
        return document
    if key.table not in document:
        document[key.table] = tomlkit.table()
    table = document[key.table]
    if not isinstance(table, MutableMapping):
        raise UsageError(f"{key.table}: expected a table")
    return cast(_Table, table)


def _same(left: object, right: object) -> bool:
    """`1 == True` in Python, and never in the file."""
    return type(left) is type(right) and left == right
