"""Generated `node:test` files are user files: Prettier leaves them as they are, `tsc` accepts
them, and they agree with the grader on real projects.

Prettier 3 runs with its defaults on the level files of the TypeScript project problems (the
fixture's and the catalog's) and on a seeded random corpus that reaches the long-line layouts. The
level files of each project then run with `node --test`, which strips their types, on its
reference (every one passes) and on its bare starter (level 1 fails only with "Not implemented"),
and type-check with the workspace's `tsc`, with the reference, in a project folder of a workspace.

Prettier is not a dependency of coding-study: these checks find it through the `PRETTIER`
environment variable (its `bin/prettier.cjs`, or any executable) or on `PATH`, and skip without
it.
"""

import difflib
import os
import random
import re
import shutil
import string
import subprocess
from pathlib import Path

import pytest
import yaml

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.languages.typescript.test_generator import TypeScriptTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language, Level, Problem
from coding_study.domain.project import ProjectTree
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature, Method, Param, Returns
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.helpers import CATALOG_PROBLEMS, SCHEMAS_DIRECTORY
from tests.project_builders import ops_case, project_meta, project_problem
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="needs Node"),
]

GENERATOR = TypeScriptTestGenerator()
TYPESCRIPT_PROJECTS = Path(__file__).resolve().parents[3] / "fixtures" / "project_typescript"
FIXTURE_PROBLEMS = TYPESCRIPT_PROJECTS / "problems"
FIXTURE = "0001-bank-project-typescript"
PRETTIER = os.environ.get("PRETTIER") or shutil.which("prettier")
PRETTIER_MAJOR_VERSION = "3."
NODE_SCRIPTS = (".cjs", ".js", ".mjs")
CORPUS_FILES = 150
CORPUS_SEED = 250
NOT_IMPLEMENTED = "Not implemented"
TAP_FAILURE = "not ok "


def typescript_projects() -> list[Path]:
    """The directories of the fixture's and the catalog's TypeScript project problems."""
    return [
        directory
        for problems in (FIXTURE_PROBLEMS, CATALOG_PROBLEMS)
        for directory in sorted(problems.iterdir())
        if is_typescript_project(directory / "meta.yaml")
    ]


def is_typescript_project(meta_file: Path) -> bool:
    if not meta_file.is_file():
        return False
    meta = yaml.safe_load(meta_file.read_text())
    return meta.get("kind") == "project" and meta.get("languages") == ["typescript"]


PROJECTS = typescript_projects()


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


def run(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)


# Prettier


def prettier(*arguments: str) -> list[str]:
    """Prettier with its defaults: no configuration or .editorconfig file is read."""
    assert PRETTIER is not None
    command = ["node", PRETTIER] if PRETTIER.endswith(NODE_SCRIPTS) else [PRETTIER]
    return [*command, "--no-config", "--no-editorconfig", *arguments]


needs_prettier = pytest.mark.skipif(
    PRETTIER is None,
    reason="needs Prettier 3: set PRETTIER to its executable or put prettier on PATH",
)


class Corpus:
    """Random level files: long names and values reach every layout, notes wrap, strings hold
    quotes, escapes and wide characters."""

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
        signature = ClassSignature(self._random.choice(CLASS_NAMES), constructor, methods)
        meta = project_meta(
            signature, comparator, language=Language.TYPESCRIPT, levels=(Level(1, "One"),)
        )
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
            returns = str(method.returns.type)
            expected = None if returns == "void" else self._value(returns)
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
                return self._random.choice([0.5, 2.0, -3.25, 1e-07, 123456.789, 1e21, 1e-06])
            case "bool":
                return self._random.choice([True, False])
            case "date":
                return self._random.choice(["2026-01-01", "1999-12-31"])
            case _:
                return self._string()

    def _string(self) -> str:
        alphabet = string.ascii_lowercase + "-" * 3 + " \"'\\\n\t\x01é中"
        return "".join(self._random.choice(alphabet) for _ in range(self._random.randint(0, 40)))

    def _note(self) -> str:
        words = [self._random.choice([*WORDS, '"quoted"', "it's", "a\\b"]) for _ in range(40)]
        return " ".join(words[: self._random.randint(1, 40)])

    def _word(self) -> str:
        return self._random.choice(WORDS)


WORDS = ("account", "transfer", "balance", "scheduled", "top", "merge", "history", "id", "x")
CLASS_NAMES = ("Bank", "LRUCache", "Ledger", "BankAccountWithAnExtremelyLongNameForItsTests")
VALUE_TYPES = (
    "long",
    "int",
    "double",
    "bool",
    "string",
    "date",
    "list<string>",
    "int[]",
    "double[]",
    "double[][]",
    "list<long>",
    "list<list<int>>",
)


@pytest.fixture(scope="module")
def generated_files(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("generated")
    corpus = Corpus(CORPUS_SEED)
    for index in range(CORPUS_FILES):
        text = GENERATOR.generate(level_tests(corpus.problem(), 1))
        (root / f"corpus-{index}.test.ts").write_text(text)
    for directory in PROJECTS:
        problem = load(directory, tmp_path_factory.mktemp("repository"))
        for path, text in level_files(problem).items():
            (root / f"{problem.meta.slug}-{Path(path).name}").write_text(text)
    return root


def first_difference(root: Path, listed: str) -> str:
    """The unified diff Prettier would apply to the first file it lists."""
    name = listed.splitlines()[0]
    original = (root / name).read_text()
    formatted = run(prettier(name), root).stdout
    diff = difflib.unified_diff(original.splitlines(), formatted.splitlines(), lineterm="")
    return f"{name}\n" + "\n".join(diff)


@needs_prettier
def test_prettier_is_version_3(tmp_path):
    assert run(prettier("--version"), tmp_path).stdout.startswith(PRETTIER_MAJOR_VERSION)


@needs_prettier
def test_every_generated_file_is_prettier_formatted(generated_files):
    listed = run(prettier("--list-different", "."), generated_files).stdout
    assert not listed, first_difference(generated_files, listed)


# node --test and tsc on the projects


def test_the_fixture_is_among_the_projects_checked():
    assert FIXTURE in {directory.name for directory in PROJECTS}


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


def node_test(root: Path, *files: str) -> subprocess.CompletedProcess[str]:
    """`node --test` in the project folder, as the starter's README says to run it."""
    return run(["node", "--test", "--test-reporter=tap", *files], root)


def test_every_level_file_passes_on_the_reference(project, tmp_path):
    root = build(tmp_path, project, project.meta.approaches[0].id)
    result = node_test(root)
    assert result.returncode == 0, result.stdout[-4000:]


def test_level_1_fails_on_the_starter_only_because_nothing_is_implemented(project, tmp_path):
    root = build(tmp_path, project, None)
    level_1 = next(iter(level_files(project)))
    output = node_test(root, level_1).stdout
    failures = output.count(f"\n{TAP_FAILURE}")
    assert failures, output[-4000:]
    assert output.count(f"error: '{NOT_IMPLEMENTED}'") == failures, output[-4000:]


@pytest.fixture(scope="module")
def workspace(practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A workspace with the practice workspace's `typescript/node_modules`, where a project
    folder finds the types of `node:test` and `node:assert`."""
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("workspace") / "ws")


def type_check(workspace: Path, root: Path) -> subprocess.CompletedProcess[str]:
    """The workspace's `tsc` on the project folder `root`, under its own tsconfig.json."""
    tsc = workspace / "typescript" / "node_modules" / "typescript" / "bin" / "tsc"
    return run(["node", str(tsc), "--noEmit", "--project", str(root)], root)


needs_pnpm = pytest.mark.skipif(shutil.which("pnpm") is None, reason="needs pnpm")


@needs_pnpm
def test_the_level_files_type_check_with_the_reference(project, workspace):
    root = build(workspace / "projects" / project.meta.slug, project, "reference")
    result = type_check(workspace, root)
    assert result.returncode == 0, result.stdout[-4000:]


@needs_pnpm
def test_a_level_file_fails_the_type_check_until_its_methods_exist(workspace, tmp_path):
    problem = load(FIXTURE_PROBLEMS / FIXTURE, tmp_path)
    root = build(workspace / "projects" / "starter-with-every-level", problem, None)
    output = type_check(workspace, root).stdout
    assert re.search(r"tests/level-2\.test\.ts\(\d+,\d+\): error TS2339", output), output[-4000:]
