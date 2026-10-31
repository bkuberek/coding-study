"""Generated Go level files are user files: gofmt leaves them as they are, `go vet` accepts them,
and they agree with the grader on a real project.

The fixture's level files and a corpus that reaches every value type and comparator are checked
with gofmt; the corpus compiles against the stub of its signature, and the fixture's level files run
with `go test` on its reference (every test passes) and on its bare starter (level 1 fails only on
"not implemented"). Each project lies at `projects/<slug>/` in a temporary directory whose
`.cs/runtime/runners/go` is this checkout's runner, so the starter's `replace` resolves.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.languages.go.stub_generator import GoStubGenerator
from coding_study.adapters.languages.go.test_generator import GoTestGenerator
from coding_study.adapters.languages.go.toolchain import build_environment
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language, Level, Problem
from coding_study.domain.project import ProjectTree
from coding_study.domain.project_tests import level_tests
from coding_study.domain.signature import ClassSignature
from tests.fakes import repository_root
from tests.helpers import REPOSITORY_ROOT
from tests.project_builders import method, ops_case, project_meta, project_problem

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("go") is None, reason="needs Go"),
]

GENERATOR = GoTestGenerator()
FIXTURE_PROBLEMS = Path(__file__).resolve().parents[3] / "fixtures" / "project_go" / "problems"
SLUG = "bank-project-go"
GO_RUNTIME = Path(".cs/runtime/runners/go")
NOT_IMPLEMENTED = "panic: not implemented"
CORPUS_RETURNS: dict[str, JsonValue] = {
    "int": -3,
    "long": 9007199254740991,
    "double": -0.5,
    "bool": False,
    "string": 'tab\tquote" back`tick 50%',
    "char": "'",
    "decimal": "-12.05",
    "date": "0001-01-01",
    "int[]": [],
    "list<long>": [3, 1],
    "double[][]": [[1.5], []],
    "list<list<string>>": [["b"], ["a", "c"]],
    "char[]": ["z", "a"],
    "list<decimal>": ["2", "10.5"],
    "list<date>": ["2026-12-31", "2024-02-29"],
    "list<list<decimal>>": [["1.1"], []],
    "bool[]": [True],
}
"""A result of every type a project returns, as tests.json writes it."""
UNORDERED_RETURNS = frozenset(
    {"list<long>", "list<list<string>>", "char[]", "list<decimal>", "list<date>"}
)
FLOAT_RETURNS = frozenset({"double", "double[][]"})


@pytest.fixture(scope="module")
def fixture_problem(tmp_path_factory: pytest.TempPathFactory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("content"), FIXTURE_PROBLEMS)
    return FsProblemRepository(root).load(SLUG)


def go(*arguments: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["go", *arguments],
        cwd=cwd,
        env=build_environment(os.environ, {"GOWORK": "off"}),
        capture_output=True,
        text=True,
        check=False,
    )


def project_folder(base: Path, *trees: ProjectTree) -> Path:
    """`trees` copied, later ones over earlier ones, into `projects/<slug>` under `base`."""
    runtime = base / GO_RUNTIME
    runtime.parent.mkdir(parents=True)
    runtime.symlink_to(REPOSITORY_ROOT / "runners" / "go", target_is_directory=True)
    folder = base / "projects" / SLUG
    for tree in trees:
        for file in tree.files:
            path = folder / file.path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(file.text or "")
    return folder


def write_level_files(folder: Path, problem: Problem, levels: range) -> list[Path]:
    paths = []
    for level in levels:
        tests = level_tests(problem, level)
        path = folder / tests.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(GENERATOR.generate(tests))
        paths.append(path)
    return paths


def corpus_problem() -> Problem:
    """Two methods per type: one compared exactly, the other unordered where Go sorts the list,
    within a tolerance where it holds doubles, and exactly otherwise."""
    per_method: dict[str, ComparatorType] = {}
    methods = []
    calls = []
    for index, (returns, value) in enumerate(CORPUS_RETURNS.items()):
        exact, other = f"exact{index}", f"other{index}"
        methods += [method(name, 1, "key: string", returns) for name in (exact, other)]
        calls += [(exact, ["k"], value), (other, ["k"], value)]
        if returns in UNORDERED_RETURNS:
            per_method[other] = ComparatorType.UNORDERED
        elif returns in FLOAT_RETURNS:
            per_method[other] = ComparatorType.FLOAT
    comparator = ComparatorSpec(ComparatorType.OPS, per_method=per_method)
    signature = ClassSignature("Bank", (), tuple(methods))
    meta = project_meta(signature, comparator, Language.GO, (Level(1, "Everything"),))
    return project_problem(ops_case("everything", 1, *calls, note="every type"), meta=meta)


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The corpus's level file in a module whose root package is the stub of its signature."""
    problem = corpus_problem()
    stub = GoStubGenerator().generate(problem.meta)
    stub = re.sub(r"^package \w+", "package bank", stub, count=1, flags=re.MULTILINE)
    module = (FIXTURE_PROBLEMS / "0001-bank-project-go" / "starter" / "go.mod").read_text()
    folder = project_folder(tmp_path_factory.mktemp("corpus"))
    folder.mkdir(parents=True)
    (folder / "go.mod").write_text(module)
    (folder / "bank.go").write_text(stub)
    write_level_files(folder, problem, range(1, 2))
    return folder


def test_gofmt_leaves_the_corpus_as_it_is(corpus):
    assert go("fmt", "./...", cwd=corpus).stdout == ""


def test_the_corpus_compiles_and_passes_go_vet(corpus):
    vetted = go("vet", "./...", cwd=corpus)
    assert vetted.returncode == 0, vetted.stderr


@pytest.fixture(scope="module")
def solved(fixture_problem: Problem, tmp_path_factory: pytest.TempPathFactory) -> Path:
    files = fixture_problem.project_files
    assert files is not None
    assert files.starter is not None
    base = tmp_path_factory.mktemp("solved")
    folder = project_folder(base, files.starter, files.overlays["reference"])
    write_level_files(folder, fixture_problem, range(1, 3))
    return folder


def test_gofmt_leaves_the_fixtures_level_files_as_they_are(solved):
    assert go("fmt", "./...", cwd=solved).stdout == ""


def test_every_level_file_passes_on_the_reference(solved):
    tested = go("test", "-count=1", "./...", cwd=solved)
    assert tested.returncode == 0, tested.stdout + tested.stderr


def test_level_1_fails_on_the_starter_only_because_nothing_is_implemented(
    fixture_problem: Problem, tmp_path: Path
):
    files = fixture_problem.project_files
    assert files is not None
    assert files.starter is not None
    folder = project_folder(tmp_path, files.starter)
    write_level_files(folder, fixture_problem, range(1, 2))
    tested = go("test", "-count=1", "./...", cwd=folder)
    assert (tested.returncode, NOT_IMPLEMENTED in tested.stdout) == (1, True), tested.stdout
