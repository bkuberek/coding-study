"""How each language adapter prepares one runner process for `cstudy bench` (`BenchCode`)."""

import os
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm.gradle import GradleOutcome
from coding_study.adapters.languages.jvm.runner import JvmRunner
from coding_study.adapters.languages.python.runner import PythonRunner
from coding_study.adapters.languages.typescript.runner import TypeScriptRunner
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    Prepared,
    PrepareResult,
    ReferenceSource,
)
from coding_study.domain.errors import ContentError
from coding_study.domain.layout import reference_build_path
from coding_study.domain.problem import Language
from tests.adapters.languages.jvm.test_jvm_runner import (
    CLASSPATH,
    JAVA_SOURCE,
    WORKSPACE_FILES,
    FakeGradle,
    compile_failure,
)
from tests.adapters.languages.typescript.test_typescript_runner import FakeTypeChecker
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
USER_FILE = "jvm/java/src/main/java/practice/two_sum/Solution.java"


def prepared(result: PrepareResult) -> Prepared:
    assert isinstance(result, Prepared)
    return result


def ignore(_line: str) -> None:
    pass


def sources(directory: Path, extension: str) -> tuple[ReferenceSource, ...]:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"hash-map.{extension}"
    path.write_text(JAVA_SOURCE)
    return (ReferenceSource("hash-map", path),)


@pytest.fixture
def python_root(tmp_path: Path) -> Path:
    interpreter = tmp_path / "python" / ".venv" / "bin" / "python"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("")
    return tmp_path


def test_python_bench_materializes_the_references(python_root):
    scope = BenchCode(TWO_SUM, sources(python_root / "solutions", "py"))
    PythonRunner(python_root).prepare(scope, ignore)
    assert (python_root / reference_build_path(TWO_SUM, "hash-map", Language.PYTHON)).is_file()


@pytest.fixture
def typescript_root(tmp_path: Path) -> Path:
    (tmp_path / "runners" / "typescript").mkdir(parents=True)
    (tmp_path / "runners" / "typescript" / "runner.ts").write_text("")
    (tmp_path / "typescript").mkdir(parents=True)
    (tmp_path / "typescript" / "package.json").write_text("{}")
    return tmp_path


def typescript_bench(root: Path, references_only: bool = False) -> Prepared:
    scope = BenchCode(TWO_SUM, sources(root / "solutions", "ts"), references_only)
    return prepared(
        TypeScriptRunner(root, root / "runners", FakeTypeChecker()).prepare(scope, ignore)
    )


def test_typescript_bench_exposes_gc(typescript_root):
    assert "--expose-gc" in typescript_bench(typescript_root).launch.command


def test_typescript_bench_materializes_the_references(typescript_root):
    typescript_bench(typescript_root)
    built = reference_build_path(TWO_SUM, "hash-map", Language.TYPESCRIPT)
    assert (typescript_root / built).is_file()


def test_typescript_bench_with_user_code_starts_in_the_workspace(typescript_root):
    launch = typescript_bench(typescript_root).launch
    assert launch.cwd == typescript_root / "typescript"


def test_typescript_references_only_start_in_the_build_project(typescript_root):
    launch = typescript_bench(typescript_root, references_only=True).launch
    assert launch.cwd == typescript_root / ".cs" / "build" / "typescript"


@pytest.fixture
def jvm_root(tmp_path: Path) -> Path:
    workspace = tmp_path / "jvm"
    for relative in WORKSPACE_FILES:
        (workspace / relative).parent.mkdir(parents=True, exist_ok=True)
        (workspace / relative).write_text(f"// {relative}\n")
    return tmp_path


def jvm_bench(root: Path, gradle: FakeGradle, references_only: bool = False) -> PrepareResult:
    runner = JvmRunner(LanguageContext(root, root / "runners"), Language.JAVA, gradle)
    scope = BenchCode(TWO_SUM, sources(root / "solutions", "java"), references_only)
    return runner.prepare(scope, ignore)


def classpath_of(result: PrepareResult) -> str:
    command = prepared(result).launch.command
    return command[command.index("-cp") + 1]


def test_jvm_bench_joins_the_user_and_reference_classpaths(jvm_root):
    result = jvm_bench(jvm_root, FakeGradle(jvm_root))
    assert classpath_of(result) == f"{CLASSPATH}{os.pathsep}{CLASSPATH}"


def test_jvm_bench_builds_both_projects(jvm_root):
    gradle = FakeGradle(jvm_root)
    jvm_bench(jvm_root, gradle)
    assert len(gradle.builds) == 2


def test_jvm_references_only_build_one_project(jvm_root):
    gradle = FakeGradle(jvm_root)
    jvm_bench(jvm_root, gradle, references_only=True)
    assert len(gradle.builds) == 1


def test_jvm_references_that_do_not_compile_are_a_content_error(jvm_root):
    failure = compile_failure(".cs/build/jvm/java/src/main/java/ref/two_sum/x.java:3: error: oops")
    with pytest.raises(ContentError):
        jvm_bench(jvm_root, FakeGradle(jvm_root, outcome=failure))


class UserBuildFails(FakeGradle):
    """References compile; the workspace build reports a compile error in the user's file."""

    def run(self, arguments):  # type: ignore[override]
        if "-p" in arguments:
            return super().run(arguments)
        self.builds.append(tuple(arguments))
        return GradleOutcome(1, f"{USER_FILE}:3: error: ';' expected\n")


def test_jvm_user_code_that_does_not_compile_is_a_build_failure(jvm_root):
    assert isinstance(jvm_bench(jvm_root, UserBuildFails(jvm_root)), BuildFailed)
