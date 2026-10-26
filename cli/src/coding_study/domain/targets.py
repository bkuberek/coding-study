"""The user's solution files as command targets (docs/specs/cli.md#solution-file-targets).

The inverse of `layout.stub_path`, on workspace-relative POSIX paths: which language and which
problem name a path in the practice projects belongs to. Turning that name into a slug needs the
problem catalog, so it stays with the caller.
"""

from dataclasses import dataclass

from coding_study.domain import layout
from coding_study.domain.problem import Language

PATH_SEPARATORS = ("/", "\\")
SOLUTION_EXTENSIONS = tuple(f".{extension}" for extension in layout.SOURCE_EXTENSIONS.values())


@dataclass(frozen=True, slots=True)
class SolutionFile:
    language: Language
    name: str
    """The problem as the file system spells it: the slug in TypeScript, `snake_slug` elsewhere."""

    def belongs_to(self, slug: str) -> bool:
        if self.language is Language.TYPESCRIPT:
            return self.name == slug
        return self.name == layout.snake_case(slug)


def is_path_target(target: str) -> bool:
    """A target is a path when it has a path separator or ends in a solution file extension;
    anything else is a slug or an id, even when a file of that name exists."""
    return any(separator in target for separator in PATH_SEPARATORS) or target.endswith(
        SOLUTION_EXTENSIONS
    )


def parse_solution_file(path: str) -> SolutionFile | None:
    """The solution file `path` (relative to the workspace root) is, or None.

    On the JVM any source file directly in the problem's package counts, so helper classes
    resolve to their problem like the declared class does.
    """
    for language in Language:
        prefix = f"{layout.user_directory(language)}/"
        if path.startswith(prefix):
            return _solution_file(language, path.removeprefix(prefix).split("/"))
    return None


def _solution_file(language: Language, parts: list[str]) -> SolutionFile | None:
    match parts:
        case [file] if language not in layout.JVM_LANGUAGES:
            stem = _source_stem(language, file)
            return SolutionFile(language, stem) if stem else None
        case [problem, file] if (
            language in layout.JVM_LANGUAGES and problem and _source_stem(language, file)
        ):
            return SolutionFile(language, problem)
        case _:
            return None


def _source_stem(language: Language, file: str) -> str | None:
    stem, _, extension = file.rpartition(".")
    return stem if extension == layout.SOURCE_EXTENSIONS[language] else None
