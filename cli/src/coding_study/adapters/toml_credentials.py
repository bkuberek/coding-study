"""`credentials.toml`: the AI providers' keys, beside `config.toml` (docs/specs/ai.md#keys).

The file is read strictly and rewritten whole, atomically, with mode 0600 in a directory of mode
0700. It is never read or written when it would lie inside the workspace. A key leaves this module
only as an `ApiKey`, and no message holds one.
"""

import contextlib
import json
import os
import secrets
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from coding_study.adapters.toml_config import config_path
from coding_study.domain.ai import ApiKey, Provider
from coding_study.domain.errors import ConfigError, UsageError

CREDENTIALS_FILE = "credentials.toml"
FILE_MODE = 0o600
DIRECTORY_MODE = 0o700
API_KEY = "api_key"
HEADER = (
    "# Your AI provider keys (docs/specs/ai.md#keys). cstudy rewrites this file whole when a key\n"
    "# changes: comments you add here do not survive."
)
_TEMPORARY_NAME_BYTES = 8
_PROVIDER_NAMES = tuple(str(provider) for provider in Provider)


def credentials_path(config_file: Path) -> Path:
    """The file beside `config_file`."""
    return config_file.with_name(CREDENTIALS_FILE)


def git_tree_of(path: Path) -> Path | None:
    """The working tree that holds `path`: the nearest directory above it with a `.git` entry (a
    directory, or the file of a worktree or a submodule); None when there is none."""
    resolved = path.resolve()
    for directory in resolved.parents:
        if (directory / ".git").exists():
            return directory
    return None


class TomlCredentials:
    """`Credentials` on the file at `path`, which may be missing, or a link. `workspace` is the
    workspace root, which the file may not lie in; None when there is no workspace."""

    def __init__(self, path: Path, workspace: Path | None) -> None:
        self._path = path
        self._workspace = workspace

    @property
    def location(self) -> str:
        return str(self._path)

    def issue(self) -> str | None:
        """Never raises."""
        inside = self._inside_workspace()
        if inside is not None:
            return inside
        problem = self._problem()
        return None if problem is None else f"{CREDENTIALS_FILE}: {problem}"

    def keys_set(self) -> frozenset[Provider]:
        """Raises UsageError for a file inside the workspace and ConfigError for one that does not
        load."""
        return frozenset(self._load())

    def key(self, provider: Provider) -> ApiKey | None:
        """Raises as `keys_set` does."""
        return self._load().get(provider)

    def save_key(self, provider: Provider, key: ApiKey) -> None:
        """Raises as `keys_set` does, and ConfigError for a file that cannot be written, which
        stays as it was."""
        self._write({**self._load(), provider: key})

    def remove_key(self, provider: Provider) -> bool:
        """Raises as `save_key` does."""
        keys = self._load()
        if provider not in keys:
            return False
        del keys[provider]
        self._write(keys)
        return True

    def _inside_workspace(self) -> str | None:
        if self._workspace is None:
            return None
        target = self._path.resolve()
        if not target.is_relative_to(self._workspace.resolve()):
            return None
        return (
            f"{CREDENTIALS_FILE} would be inside this workspace ({self._path}): keys never go in "
            "a workspace; point CSTUDY_CONFIG at a config.toml outside it"
        )

    def _load(self) -> dict[Provider, ApiKey]:
        inside = self._inside_workspace()
        if inside is not None:
            raise UsageError(inside)
        keys, problem = self._read()
        if problem is not None:
            raise ConfigError(self.location, [problem])
        return keys

    def _problem(self) -> str | None:
        return self._read()[1]

    def _read(self) -> tuple[dict[Provider, ApiKey], str | None]:
        try:
            text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return {}, None
        except (OSError, UnicodeDecodeError):
            return {}, "it cannot be read"
        try:
            values = tomllib.loads(text)
        except tomllib.TOMLDecodeError:
            return {}, "it is not valid TOML"
        return _keys_of(values)

    def _write(self, keys: Mapping[Provider, ApiKey]) -> None:
        """The whole file, or nothing: a temporary file beside it, then a rename. The file goes
        with its last key."""
        target = self._path.resolve()
        try:
            if not keys:
                target.unlink(missing_ok=True)
                return
            target.parent.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
            _replace(target, _text_of(keys))
        except OSError as error:
            raise ConfigError(self.location, [f"it cannot be written: {error.strerror}"]) from None


def open_credentials(
    environ: Mapping[str, str], home: Path, workspace: Path | None
) -> TomlCredentials:
    """The credentials beside the `config.toml` that `environ` and `home` select; `workspace` is
    the workspace root, or None when there is none."""
    return TomlCredentials(credentials_path(config_path(environ, home)), workspace)


def _keys_of(values: Mapping[str, object]) -> tuple[dict[Provider, ApiKey], str | None]:
    keys: dict[Provider, ApiKey] = {}
    for name, table in values.items():
        if name not in _PROVIDER_NAMES:
            return {}, f'unknown provider "{name}"'
        if not isinstance(table, dict):
            return {}, f"{name}: expected a table"
        fields = cast(dict[str, object], table)
        for field in fields:
            if field != API_KEY:
                return {}, f'{name}: unknown key "{field}"'
        value = fields.get(API_KEY)
        if not isinstance(value, str) or not value:
            return {}, f"{name}: {API_KEY} must be a non-empty string"
        try:
            keys[Provider(name)] = ApiKey(value)
        except UsageError:
            return {}, f"{name}: {API_KEY} must be one line of text with no spaces"
    return keys, None


def _text_of(keys: Mapping[Provider, ApiKey]) -> str:
    tables = [
        f"[{provider}]\n{API_KEY} = {_quoted(keys[provider])}\n"
        for provider in Provider
        if provider in keys
    ]
    return HEADER + "\n\n" + "\n".join(tables)


def _quoted(key: ApiKey) -> str:
    """A TOML basic string: JSON's escapes are TOML's, for what a key may hold."""
    return json.dumps(key.reveal(), ensure_ascii=False)


def _replace(target: Path, text: str) -> None:
    temporary = target.with_name(f"{target.name}.{secrets.token_hex(_TEMPORARY_NAME_BYTES)}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, FILE_MODE)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            os.fchmod(file.fileno(), FILE_MODE)
            file.write(text)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temporary.unlink()
