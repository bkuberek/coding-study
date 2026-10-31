"""Generated pytest files are user files: ruff leaves them as they are, and they agree with the
grader on real projects.

ruff runs with the starter's own settings (its `pyproject.toml`) on the level files of the
fixture project, the catalog's Python project problems and a seeded random corpus that reaches
the long-line layouts. The level files of each project then run with pytest on its reference
(every one passes) and on its bare starter (level 1 fails only with `NotImplementedError`).
"""

import random
import shutil
import string
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Level, Problem
from coding_study.domain.project import ProjectTree
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method, Param, Returns
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.helpers import CATALOG_PROBLEMS, PROJECT_PROBLEMS, SCHEMAS_DIRECTORY
from tests.project_builders import ops_case, project_meta, project_problem

pytestmark = pytest.mark.slow

GENERATOR = PythonTestGenerator()
TOOLS = Path(sys.executable).parent
STARTER_SETTINGS = '[tool.ruff]\ntarget-version = "py313"\n'
"""The ruff table of a Python starter (docs/specs/problem-format.md#starter)."""
CORPUS_FILES = 150
CORPUS_SEED = 249
NOT_IMPLEMENTED = "NotImplementedError"


def python_projects() -> list[Path]:
    """The directories of the fixture's and the catalog's Python project problems."""
    return [
        directory
        for problems in (PROJECT_PROBLEMS, CATALOG_PROBLEMS)
        for directory in sorted(problems.iterdir())
        if is_python_project(directory / "meta.yaml")
    ]


def is_python_project(meta_file: Path) -> bool:
    if not meta_file.is_file():
        return False
    meta = yaml.safe_load(meta_file.read_text())
    return meta.get("kind") == "project" and meta.get("languages") == ["python"]


PROJECTS = python_projects()


def load(directory: Path, root: Path) -> Problem:
    """The problem in `directory`, read from a repository holding only it and the schemas."""
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    shutil.copytree(directory, root / "problems" / directory.name)
    return FsProblemRepository(root).load(directory.name.split("-", 1)[1])


def level_files(problem: Problem) -> dict[str, str]:
    return {
        tests.path: GENERATOR.generate(tests)
        for tests in (level_tests(problem, level.number) for level in problem.meta.levels)
    }


def write_tree(root: Path, tree: ProjectTree | None) -> None:
    for file in tree.files if tree else ():
        path = root / file.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(file.text or "")


def ruff(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(TOOLS / "ruff"), *arguments, "--no-cache", "."],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def pytest_run(root: Path, *files: str) -> subprocess.CompletedProcess[str]:
    """pytest as `.venv/bin/pytest` would run it in the project: its own settings, no plugins,
    the project root off `sys.path` until `pythonpath` puts it there."""
    environment = {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run(
        [sys.executable, "-P", "-m", "pytest", "-q", "-rf", "--tb=line", *files],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


# ruff


class Corpus:
    """Random level files: long names and values reach every layout, notes wrap, strings hold
    quotes and escapes."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)

    def problem(self) -> Problem:
        methods = tuple(self._method(index) for index in range(self._random.randint(1, 4)))
        constructor = self._params(self._random.randint(0, 3))
        per_method = {
            method.name: self._random.choice(
                [ComparatorType.EXACT, ComparatorType.UNORDERED, ComparatorType.FLOAT]
            )
            for method in methods
        }
        comparator = ComparatorSpec(
            ComparatorType.OPS, self._random.choice([1e-6, 0.001]), per_method
        )
        signature = ClassSignature(
            self._random.choice(["Bank", "LRUCache", "Ledger"]), constructor, methods
        )
        meta = project_meta(signature, comparator, levels=(Level(1, "One"),))
        cases = [self._case(signature, index) for index in range(self._random.randint(1, 3))]
        return project_problem(*cases, meta=meta)

    def _method(self, index: int) -> Method:
        name = self._word() + "".join(
            self._word().capitalize() for _ in range(self._random.randint(0, 4))
        )
        returns = self._random.choice(["void", *VALUE_TYPES])
        params = self._params(self._random.randint(0, 5))
        return Method(f"{name}{index}", params, Returns(parse_return_type(returns)), level=1)

    def _params(self, count: int) -> tuple[Param, ...]:
        return tuple(
            Param(f"p{index}", parse_value_type(self._random.choice(VALUE_TYPES)))
            for index in range(count)
        )

    def _case(self, signature: ClassSignature, index: int):
        calls = []
        for _ in range(self._random.randint(0, 6)):
            method = self._random.choice(signature.methods)
            arguments = [self._value(str(param.type)) for param in method.params]
            expected = (
                None
                if str(method.returns.type) == "void"
                else self._value(str(method.returns.type))
            )
            calls.append((method.name, arguments, expected))
        constructor = [self._value(str(param.type)) for param in signature.constructor_params]
        note = self._note() if self._random.random() < 0.6 else None
        return ops_case(
            f"ex{index}-{self._word()}",
            1,
            *calls,
            note=note,
            constructor=constructor,
            class_name=signature.name,
        )

    def _value(self, type_text: str) -> JsonValue:
        if type_text.endswith("[]") or type_text.startswith("list<"):
            element = type_text[5:-1] if type_text.startswith("list<") else type_text[:-2]
            return [self._value(element) for _ in range(self._random.choice([0, 1, 2, 3, 8, 14]))]
        match type_text:
            case "long" | "int":
                return self._random.choice([0, -1, 7, 1000000, 9007199254740991])
            case "double":
                return self._random.choice([0.5, 2.0, -3.25, 1e-07, 123456.789])
            case "bool":
                return self._random.choice([True, False])
            case "decimal":
                return self._random.choice(["2.50", "10", "-0.01", "123456789.123"])
            case "date":
                return self._random.choice(["2026-01-01", "1999-12-31"])
            case _:
                return self._string()

    def _string(self) -> str:
        alphabet = string.ascii_lowercase + "-" * 3 + " \"'\\\n\t"
        return "".join(self._random.choice(alphabet) for _ in range(self._random.randint(0, 40)))

    def _note(self) -> str:
        words = [self._random.choice([*WORDS, '"quoted"', "it's", "a\\b"]) for _ in range(40)]
        return " ".join(words[: self._random.randint(1, 40)])

    def _word(self) -> str:
        return self._random.choice(WORDS)


WORDS = ("account", "transfer", "balance", "scheduled", "top", "merge", "history", "id", "x")
VALUE_TYPES = (
    "long",
    "int",
    "double",
    "bool",
    "string",
    "decimal",
    "date",
    "list<string>",
    "int[]",
    "double[]",
    "double[][]",
    "list<decimal>",
    "list<list<int>>",
)


@pytest.fixture(scope="module")
def generated_files(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("generated")
    (root / "pyproject.toml").write_text(STARTER_SETTINGS)
    (root / "bank").mkdir()
    (root / "bank" / "bank.py").write_text("")
    corpus = Corpus(CORPUS_SEED)
    for index in range(CORPUS_FILES):
        (root / f"test_corpus_{index}.py").write_text(
            GENERATOR.generate(level_tests(corpus.problem(), 1))
        )
    for directory in PROJECTS:
        problem = load(directory, tmp_path_factory.mktemp("repository"))
        for path, text in level_files(problem).items():
            (root / f"{problem.meta.slug}_{Path(path).name}").write_text(text)
    return root


def test_every_generated_file_is_ruff_formatted(generated_files):
    result = ruff(generated_files, "format", "--diff")
    assert result.returncode == 0, result.stdout[:6000]


def test_every_generated_file_passes_ruff_check(generated_files):
    result = ruff(generated_files, "check")
    assert result.returncode == 0, result.stdout[:6000]


def test_every_generated_line_fits_88_columns(generated_files):
    result = ruff(generated_files, "check", "--select", "E501,I")
    assert result.returncode == 0, result.stdout[:6000]


# pytest on the projects


@pytest.fixture(params=PROJECTS, ids=[directory.name for directory in PROJECTS])
def project(request, tmp_path_factory) -> Problem:
    return load(request.param, tmp_path_factory.mktemp("repository"))


def build(root: Path, problem: Problem, overlay: str | None) -> Path:
    files = problem.project_files
    assert files is not None
    write_tree(root, files.starter)
    if overlay is not None:
        write_tree(root, files.overlays[overlay])
    for path, text in level_files(problem).items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text)
    return root


def test_the_pilot_is_among_the_projects_checked():
    assert "0249-bank-project-python" in {directory.name for directory in PROJECTS}


def test_every_level_file_passes_on_the_reference(project, tmp_path):
    approach = project.meta.approaches[0].id
    root = build(tmp_path, project, approach)
    result = pytest_run(root, *level_files(project))
    assert result.returncode == 0, result.stdout[-4000:]


def test_level_1_fails_on_the_starter_only_because_nothing_is_implemented(project, tmp_path):
    root = build(tmp_path, project, None)
    level_1 = next(iter(level_files(project)))
    result = pytest_run(root, level_1)
    failures = [line for line in result.stdout.splitlines() if line.startswith("FAILED")]
    assert failures, result.stdout[-4000:]
    assert all(NOT_IMPLEMENTED in line for line in failures), result.stdout[-4000:]
