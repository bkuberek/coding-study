"""The deprecated public surfaces (docs/specs/compatibility.md#deprecation).

A deprecated flag, config key or environment variable keeps working until 2.0 and warns once on
standard error; a deprecated JSON field is marked `"deprecated": true` in its schema.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

REMOVED_IN = "2.0"


class DeprecatedSurface(StrEnum):
    FLAG = "flag"
    CONFIG_KEY = "config_key"
    ENV_VAR = "env_var"
    JSON_FIELD = "json_field"


@dataclass(frozen=True, slots=True)
class Deprecation:
    surface: DeprecatedSurface
    name: str
    """A flag as `cstudy <command> [<subcommand>] --<flag>`, a config key by its dotted TOML name,
    an environment variable by its name, a JSON field as `<document>.<path>`: the schema's file
    name without `.schema.json`, then the field's dotted path through properties, arrays left
    out."""
    since: str
    """The cstudy version that deprecated it."""
    replacement: str | None = None


DEPRECATIONS: tuple[Deprecation, ...] = ()


def deprecation_notice(deprecation: Deprecation) -> str:
    """The warning line: `; use <replacement>` is there only when there is a replacement."""
    notice = (
        f"warning: {deprecation.name} is deprecated since cstudy {deprecation.since}"
        f" and is removed in {REMOVED_IN}"
    )
    if deprecation.replacement:
        notice += f"; use {deprecation.replacement}"
    return notice


def deprecated_names(
    surface: DeprecatedSurface, registry: Iterable[Deprecation] = DEPRECATIONS
) -> frozenset[str]:
    return frozenset(entry.name for entry in registry if entry.surface is surface)


def is_deprecated_flag(
    command: str, flag: str, registry: Iterable[Deprecation] = DEPRECATIONS
) -> bool:
    """Whether `flag` (`--json`) of `command` (`cstudy stats`) is deprecated."""
    return f"{command} {flag}" in deprecated_names(DeprecatedSurface.FLAG, registry)
