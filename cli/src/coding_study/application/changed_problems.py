"""The problems `cstudy verify --changed` checks: those with a file changed relative to `main`
(docs/specs/cli.md#cstudy-verify)."""

from dataclasses import dataclass

from coding_study.application.ports import ChangedFiles, ProblemFiles

CHANGED_BASE = "main"


@dataclass(frozen=True, slots=True)
class ChangedProblems:
    slugs: tuple[str, ...]
    """The problems with a changed file, in directory order, each once."""
    misnamed: tuple[str, ...]
    """The directories of `problems/` with a changed file that load as no problem, by name."""

    def __bool__(self) -> bool:
        return bool(self.slugs or self.misnamed)


def changed_problems(problems: ProblemFiles, changes: ChangedFiles) -> ChangedProblems:
    """Deleted problems and other files select nothing."""
    prefix = f"{problems.directory}/"
    changed_directories = {
        name
        for path in changes.changed_since(CHANGED_BASE)
        if (name := _problem_directory(path, prefix)) is not None
    }
    return ChangedProblems(
        slugs=tuple(slug for slug in problems.slugs() if slug in changed_directories),
        misnamed=tuple(
            found.name for found in problems.misnamed() if found.name in changed_directories
        ),
    )


def _problem_directory(path: str, prefix: str) -> str | None:
    """The directory directly below `prefix` that holds `path`, if any."""
    if not path.startswith(prefix):
        return None
    name, separator, _ = path.removeprefix(prefix).partition("/")
    return name if separator else None
