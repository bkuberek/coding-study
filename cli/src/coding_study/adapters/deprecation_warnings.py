"""Warns on standard error about a deprecated flag, config key or environment variable
(docs/specs/compatibility.md#deprecation), once per name per process."""

import sys
from collections.abc import Iterable, Mapping

from coding_study.adapters.toml_config import TomlConfigSource
from coding_study.domain.deprecations import (
    DEPRECATIONS,
    DeprecatedSurface,
    Deprecation,
    deprecation_notice,
)

_warned: set[str] = set()


def warn_deprecated(deprecation: Deprecation) -> None:
    """The warning line on standard error, unless this process already printed it."""
    if deprecation.name in _warned:
        return
    _warned.add(deprecation.name)
    sys.stderr.write(f"{deprecation_notice(deprecation)}\n")
    sys.stderr.flush()


def warn_about_deprecated_use(
    environ: Mapping[str, str],
    config: TomlConfigSource,
    registry: Iterable[Deprecation] = DEPRECATIONS,
) -> None:
    """Warns about each deprecated environment variable that is set and each deprecated key in
    the config file."""
    entries = tuple(registry)
    for entry in entries:
        if entry.surface is DeprecatedSurface.ENV_VAR and entry.name in environ:
            warn_deprecated(entry)
    for entry in config.deprecated_keys(entries):
        warn_deprecated(entry)
