"""What a project starter may not hold (docs/specs/problem-format.md#starter)."""

from coding_study.domain.project import PATH_SEPARATOR

CACHE_DIRECTORIES = frozenset(
    {
        *("__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".venv", "node_modules"),
        *("build", ".gradle", ".kotlin"),
        "target",
    }
)
BUILD_OUTPUT_SUFFIXES = (".pyc", ".tsbuildinfo", ".class", ".jar")
LOCK_FILES = frozenset(
    {
        *("uv.lock", "poetry.lock", "pdm.lock", "Pipfile.lock"),
        *("package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock"),
        *("bun.lock", "bun.lockb", "Cargo.lock"),
        "go.sum",
        *("gradle.lockfile", "buildscript-gradle.lockfile", "settings-gradle.lockfile"),
        "verification-metadata.xml",
    }
)


def cache_path(path: str) -> str | None:
    """The cache directory `path` lies in, or `path` itself when it is build output."""
    segments = path.split(PATH_SEPARATOR)
    for index, segment in enumerate(segments[:-1]):
        if segment in CACHE_DIRECTORIES:
            return PATH_SEPARATOR.join(segments[: index + 1])
    return path if path.endswith(BUILD_OUTPUT_SUFFIXES) else None
