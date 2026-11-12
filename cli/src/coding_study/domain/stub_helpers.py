"""Starter helpers (docs/specs/problem-format.md#starter-helpers): code that the generated starter
of one language ends with, for a tool the problem needs and that language's standard library
lacks, such as SHA-256 in Rust.

`helpers/` holds at most one file per language, of any name with the language's extension.
`cstudy start` appends it to the generated stub, and `cstudy verify` builds the stub with it (D1).
A reference that uses the helper carries its own copy, since references are copied unchanged.
"""

from collections.abc import Sequence

from coding_study.domain.layout import SOURCE_EXTENSIONS
from coding_study.domain.problem import Language
from coding_study.domain.problem_files import HELPERS_DIRECTORY

_BLANK_LINES = {
    Language.PYTHON: 2,
    Language.TYPESCRIPT: 1,
    Language.JAVA: 1,
    Language.KOTLIN: 1,
    Language.GO: 1,
    Language.RUST: 1,
}
"""Blank lines between the stub and the helper: two between top-level Python definitions, as
ruff formats them, and one elsewhere."""


def helper_language(file_name: str) -> Language | None:
    """The language whose extension the file name ends with, or None."""
    stem, dot, extension = file_name.rpartition(".")
    if not dot or not stem:
        return None
    return next(
        (language for language, known in SOURCE_EXTENSIONS.items() if known == extension), None
    )


def helper_file(language: Language, file_names: Sequence[str]) -> str | None:
    """The helper of `language` among the names of `helpers/`, relative to the problem directory,
    or None when it has none."""
    name = next((name for name in file_names if helper_language(name) is language), None)
    return None if name is None else f"{HELPERS_DIRECTORY}/{name}"


def with_helper(stub: str, helper: str | None, language: Language) -> str:
    """The stub, then the helper after a blank line, ending with one line feed."""
    if helper is None:
        return stub
    separator = "\n" * (_BLANK_LINES[language] + 1)
    return f"{stub.rstrip(chr(10))}{separator}{helper.rstrip(chr(10))}\n"


def helper_issues(
    file_names: Sequence[str], languages: Sequence[Language]
) -> list[tuple[str, str]]:
    """S8: each file of `helpers/` maps to a language the problem lists, at most one each. Each
    issue is the file relative to the problem directory and its message."""
    issues: list[tuple[str, str]] = []
    seen: set[Language] = set()
    for name in file_names:
        language = helper_language(name)
        location = f"{HELPERS_DIRECTORY}/{name}"
        if language is None or language not in languages:
            issues.append((location, "maps to no language in languages"))
        elif language in seen:
            issues.append((location, f"a second helper for {language}; a language has at most one"))
        else:
            seen.add(language)
    return issues
