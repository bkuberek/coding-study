"""Phase 4 in all four languages: a progressive problem unlocks its levels one at a time and the
rendered statement hides the locked levels (the exit criterion), and `cstudy verify` passes the
progressive and low-level design fixtures.

Marked `slow`: it drives the real runners (the workspace Python venv, Node, Gradle and the JVM)
through `cstudy start`, `cstudy test`, `cstudy done` and `cstudy verify`. The content root is
temporary (the fixture problems and a link to the real `runners/`), and the workspace is a copy of
the session's practice workspace that links its venv, `node_modules` and runner runtime.
"""

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.layout import SOURCE_EXTENSIONS
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"
SOLUTIONS = PHASE4 / "0001-level-store" / "solutions"
STATEMENT = ".statements/level-store.md"
USER_FILES = {
    Language.PYTHON: ("python/practice/level_store.py", ""),
    Language.TYPESCRIPT: ("typescript/practice/level-store.ts", ""),
    Language.JAVA: (
        "jvm/java/src/main/java/practice/level_store/LevelStore.java",
        "package practice.level_store;\n\n",
    ),
    Language.KOTLIN: (
        "jvm/kotlin/src/main/kotlin/practice/level_store/LevelStore.kt",
        "package practice.level_store\n\n",
    ),
}
LEVEL_TITLES = (
    "## Level 1: Put and get",
    "## Level 2: Remove and size",
    "## Level 3: Prefix scans",
)


@pytest.fixture(scope="module")
def content(tmp_path_factory: pytest.TempPathFactory) -> Path:
    content = tmp_path_factory.mktemp("phase4-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(PHASE4, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    """The workspace."""
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("phase4") / "ws")


@pytest.fixture
def cstudy(root: Path, content: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CSTUDY_CONTENT", str(content))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))

    def invoke(*arguments: str):
        return runner.invoke(cli.app, list(arguments))

    return invoke


def solve(root: Path, language: Language) -> None:
    """The user's file becomes the reference solution of every level."""
    path, package = USER_FILES[language]
    reference = (SOLUTIONS / f"hash-map.{SOURCE_EXTENSIONS[language]}").read_text()
    (root / path).write_text(package + reference)


def shown_levels(root: Path) -> tuple[str, ...]:
    statement = (root / STATEMENT).read_text()
    return tuple(title for title in LEVEL_TITLES if title in statement)


@pytest.mark.parametrize("language", list(Language), ids=str)
def test_levels_unlock_one_at_a_time(root, cstudy, language):
    observed: list[tuple[int, tuple[str, ...]]] = []
    started = cstudy("start", "level-store", "--lang", language, "--no-open")
    observed.append((started.exit_code, shown_levels(root)))
    observed.append((cstudy("test", "--lang", language).exit_code, shown_levels(root)))
    solve(root, language)
    for _ in range(3):
        observed.append((cstudy("test", "--lang", language).exit_code, shown_levels(root)))
    finished = cstudy("done", "level-store", "--rating", "ok")
    observed.append((finished.exit_code, shown_levels(root)))
    assert observed == [
        (0, LEVEL_TITLES[:1]),
        (1, LEVEL_TITLES[:1]),
        (0, LEVEL_TITLES[:2]),
        (0, LEVEL_TITLES[:3]),
        (0, LEVEL_TITLES[:3]),
        (0, LEVEL_TITLES[:3]),
    ]


def test_verify_passes_the_fixtures_in_every_language(cstudy):
    result = cstudy("verify", "--require-ready")
    assert (result.exit_code, result.output.splitlines()[-2:]) == (
        0,
        [
            "coverage  python 2/2 · typescript 2/2 · java 2/2 · kotlin 2/2",
            "result    0 failed · 2 passed",
        ],
    )
