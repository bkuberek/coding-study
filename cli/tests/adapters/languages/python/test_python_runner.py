from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.python import create_runner
from coding_study.application.ports import (
    BuildScope,
    Prepared,
    PrepareResult,
    References,
    ReferenceSource,
    UserCode,
)
from coding_study.domain.errors import ContentError, RunnerStartError
from coding_study.domain.layout import reference_build_path
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
WORKSPACE = Path("python")
INTERPRETER = WORKSPACE / ".venv/bin/python"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    interpreter = tmp_path / INTERPRETER
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    return tmp_path


@pytest.fixture
def solutions(tmp_path: Path) -> Path:
    directory = tmp_path / "problems" / "0001-two-sum" / "solutions"
    directory.mkdir(parents=True)
    return directory


def prepare(root: Path, scope: BuildScope, notices: list[str] | None = None) -> PrepareResult:
    notify = (notices if notices is not None else []).append
    return create_runner(LanguageContext(root, root / "runners")).prepare(scope, notify)


def prepared(root: Path, scope: BuildScope) -> Prepared:
    result = prepare(root, scope)
    assert isinstance(result, Prepared)
    return result


def reference(solutions: Path, approach_id: str, source: str) -> ReferenceSource:
    path = solutions / f"{approach_id}.py"
    path.write_text(source)
    return ReferenceSource(approach_id, path)


def built_reference(root: Path, approach_id: str) -> Path:
    return root / reference_build_path(TWO_SUM, approach_id, Language.PYTHON)


def test_user_code_runs_the_runner_module_with_the_workspace_interpreter(root):
    launch = prepared(root, UserCode(TWO_SUM)).launch
    assert launch.command == (str(root / INTERPRETER), "-m", "cs_runner")


def test_the_runner_starts_in_the_python_workspace(root):
    assert prepared(root, UserCode(TWO_SUM)).launch.cwd == root / WORKSPACE


def test_the_runner_gets_the_python_hello_timeout(root):
    launch = prepared(root, UserCode(TWO_SUM)).launch
    assert launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.PYTHON]


def test_user_code_needs_no_build(root):
    assert prepared(root, UserCode(TWO_SUM)).build_note is None


def test_preparing_prints_no_notice(root):
    notices: list[str] = []
    prepare(root, UserCode(TWO_SUM), notices)
    assert notices == []


def test_a_missing_workspace_environment_cannot_start(tmp_path):
    with pytest.raises(RunnerStartError, match="uv sync"):
        prepare(tmp_path, UserCode(TWO_SUM))


def test_references_are_copied_to_their_build_paths(root, solutions):
    source = reference(solutions, "hash-map", "def two_sum(nums, target):\n    return []\n")
    prepare(root, References(TWO_SUM, (source,)))
    assert built_reference(root, "hash-map").read_text() == source.path.read_text()


def test_references_replace_an_earlier_copy(root, solutions):
    prepare(root, References(TWO_SUM, (reference(solutions, "hash-map", "old = 1\n"),)))
    prepare(root, References(TWO_SUM, (reference(solutions, "hash-map", "new = 2\n"),)))
    assert built_reference(root, "hash-map").read_text() == "new = 2\n"


def test_every_reference_is_materialized(root, solutions):
    sources = tuple(reference(solutions, approach, "x = 1\n") for approach in ("a-1", "b-2"))
    prepare(root, References(TWO_SUM, sources))
    assert all(built_reference(root, approach).exists() for approach in ("a-1", "b-2"))


def test_references_launch_like_user_code(root, solutions):
    scope = References(TWO_SUM, (reference(solutions, "hash-map", "x = 1\n"),))
    assert prepared(root, scope).launch == prepared(root, UserCode(TWO_SUM)).launch


def test_a_missing_reference_file_is_a_content_error(root, solutions):
    missing = ReferenceSource("hash-map", solutions / "hash-map.py")
    with pytest.raises(ContentError, match=r"hash-map\.py"):
        prepare(root, References(TWO_SUM, (missing,)))
