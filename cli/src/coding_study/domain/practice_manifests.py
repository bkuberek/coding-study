"""Practice project manifests that list each started problem
(docs/specs/installation-and-workspaces.md#layout).

The Rust project's `rust/Cargo.toml` declares every problem file as an `[[example]]` built as a
library, which is what makes rust-analyzer check it; `cstudy start` adds the entry. No other
language keeps such a list.
"""

import tomllib
from typing import assert_never, cast

from coding_study.domain.layout import RUST_PROJECT, stub_path
from coding_study.domain.problem import Language, ProblemMeta

RUST_MANIFEST = f"{RUST_PROJECT}/Cargo.toml"
EXAMPLE_TABLE = "example"


def practice_manifest(language: Language) -> str | None:
    """The manifest that lists `language`'s problems, relative to the workspace root."""
    match language:
        case Language.RUST:
            return RUST_MANIFEST
        case Language.PYTHON | Language.TYPESCRIPT | Language.JAVA | Language.KOTLIN | Language.GO:
            return None
        case _:
            assert_never(language)


def with_problem(manifest: str, meta: ProblemMeta) -> str:
    """`rust/Cargo.toml` with an `[[example]]` for `meta` appended, unless one already names its
    file or its name. A manifest that does not parse is returned unchanged: only the editor
    reads it, and appending could not repair it."""
    path = stub_path(meta, Language.RUST).removeprefix(f"{RUST_PROJECT}/")
    try:
        examples = tomllib.loads(manifest).get(EXAMPLE_TABLE, [])
    except tomllib.TOMLDecodeError:
        return manifest
    if any(_names(example, meta.snake_slug, path) for example in _tables(examples)):
        return manifest
    entry = (
        f'[[{EXAMPLE_TABLE}]]\nname = "{meta.snake_slug}"\npath = "{path}"\ncrate-type = ["lib"]\n'
    )
    separator = "\n" if manifest.endswith("\n") else "\n\n"
    return f"{manifest}{separator}{entry}" if manifest else entry


def _tables(examples: object) -> list[dict[str, object]]:
    if not isinstance(examples, list):
        return []
    items = cast("list[object]", examples)
    return [cast("dict[str, object]", item) for item in items if isinstance(item, dict)]


def _names(example: dict[str, object], name: str, path: str) -> bool:
    return example.get("name") == name or example.get("path") == path
