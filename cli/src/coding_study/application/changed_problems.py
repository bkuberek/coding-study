"""The problems `cstudy verify --changed` checks: those with a file changed relative to `main`
(docs/specs/cli.md#cstudy-verify)."""

from coding_study.application.ports import ChangedFiles, ProblemFiles

CHANGED_BASE = "main"


def changed_problem_slugs(problems: ProblemFiles, changes: ChangedFiles) -> tuple[str, ...]:
    """In directory order, each once; deleted problems and other files select nothing."""
    prefix = f"{problems.directory}/"
    changed_directories = {
        name
        for path in changes.changed_since(CHANGED_BASE)
        if (name := _problem_directory(path, prefix)) is not None
    }
    selected = (
        slug
        for slug, name in zip(problems.slugs(), problems.directory_names(), strict=True)
        if name in changed_directories
    )
    return tuple(dict.fromkeys(selected))


def _problem_directory(path: str, prefix: str) -> str | None:
    """The directory directly below `prefix` that holds `path`, if any."""
    if not path.startswith(prefix):
        return None
    name, separator, _ = path.removeprefix(prefix).partition("/")
    return name if separator else None
