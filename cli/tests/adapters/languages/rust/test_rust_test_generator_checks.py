"""Generated libtest files are user files: rustfmt leaves them as they are, clippy finds nothing
in them for Rust 1.80, and they agree with the grader on real projects.

rustfmt runs with its defaults on the level files of the Rust project fixture and on a seeded
random corpus that reaches the long-line layouts. The level files of the fixture then run with
`cargo test` on its reference (every one passes) and its bare starter (level 1 fails only with
`todo!()`), and so do the files of a project whose methods return every kind of value a generated
test compares: decimals, dates, doubles within a tolerance, and unordered lists.
"""

import os
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.domain.cases import JsonValue
from coding_study.domain.problem import ComparatorSpec, ComparatorType, Language, Problem
from coding_study.domain.project import ProjectTree
from coding_study.domain.project_tests import Call, LevelTest, LevelTests, level_tests
from coding_study.domain.signature import ClassSignature, Method, Param, Returns
from coding_study.domain.type_dsl import parse_return_type, parse_value_type
from tests.fakes import repository_root
from tests.helpers import REPOSITORY_ROOT, RUST_PROJECT_PROBLEMS
from tests.project_builders import method, ops_case, project_meta, project_problem

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("cargo") is None, reason="needs Rust"),
]

GENERATOR = RustTestGenerator()
VENDOR = REPOSITORY_ROOT / "runners" / "rust" / "vendor"
CORPUS_FILES = 120
CORPUS_SEED = 251
TYPES = (
    *("int", "long", "string", "double", "bool", "char", "int[]", "list<string>"),
    *("list<list<int>>", "decimal", "date", "long[]", "list<double>", "string[][]"),
)
WORDS = (
    *("account", "id", "amount", "timestamp", "source", "target", "transfer", "deposit"),
    *("top", "spenders", "merge", "history", "balance", "schedule", "with", "long", "name"),
)
CLASSES = ("Bank", "LRUCache", "Kv", "InventoryOfThingsAndStuff", "Ledger")
NOT_IMPLEMENTED = "not yet implemented"


def rustfmt_check(directory: Path) -> subprocess.CompletedProcess[str]:
    files = sorted(str(path) for path in directory.glob("*.rs"))
    command = ["rustfmt", "--edition", "2021", "--check", *files]
    return subprocess.run(command, capture_output=True, text=True, check=False)


class _Corpus:
    """Random level files: long names, many arguments, long lists, every comparator."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)

    def level_tests(self, index: int) -> LevelTests:
        methods = tuple(self._method(number) for number in range(self._random.randint(1, 4)))
        constructor = tuple(
            Param(f"seed{number}", parse_value_type(self._random.choice(TYPES)))
            for number in range(self._random.choice((0, 0, 1, 3)))
        )
        signature = ClassSignature(self._random.choice(CLASSES), constructor, methods)
        tests = tuple(self._test(number, signature) for number in range(self._random.randint(1, 3)))
        problem = project_meta(language=Language.RUST)
        assert problem.project is not None
        return LevelTests(
            f"corpus-{index}-rust", 1, Language.RUST, problem.project, signature, 1e-9, tests
        )

    def _method(self, number: int) -> Method:
        words = self._random.sample(WORDS, self._random.randint(1, 6))
        params = tuple(
            Param(
                f"{self._random.choice(WORDS)}{position}",
                parse_value_type(self._random.choice(TYPES)),
            )
            for position in range(self._random.randint(0, 5))
        )
        returns = parse_return_type(self._random.choice((*TYPES, "void", "void")))
        name = words[0] + "".join(word.capitalize() for word in words[1:]) + str(number)
        return Method(name, params, Returns(returns), level=1)

    def _test(self, number: int, signature: ClassSignature) -> LevelTest:
        calls: list[Call] = []
        for _ in range(self._random.randint(0, 6)):
            found = self._random.choice(signature.methods)
            arguments = tuple(self._value(str(param.type)) for param in found.params)
            returns = str(found.returns.type)
            expected = None if returns == "void" else self._value(returns)
            calls.append(Call(found, arguments, expected, self._comparator(returns)))
        constructor = tuple(self._value(str(param.type)) for param in signature.constructor_params)
        return LevelTest(f"ex{number}", None, constructor, tuple(calls))

    def _comparator(self, returns: str) -> ComparatorType:
        listed = returns.endswith("[]") or returns.startswith("list<")
        choices = [ComparatorType.EXACT]
        if listed and "double" not in returns:
            choices.append(ComparatorType.UNORDERED)
        if returns in ("double", "double[]", "list<double>"):
            choices.append(ComparatorType.FLOAT)
        return self._random.choice(choices)

    def _value(self, type_text: str) -> JsonValue:
        if type_text.endswith("[]") or type_text.startswith("list<"):
            element = type_text[:-2] if type_text.endswith("[]") else type_text[5:-1]
            size = self._random.choice((0, 1, 2, 3, 5, 8, 13, 25))
            return [self._value(element) for _ in range(size)]
        choices: dict[str, tuple[JsonValue, ...]] = {
            "int": (0, 1, -5, 42, 1000, 123456789, -2147483648),
            "long": (0, 7, 10000000000, -99, 9007199254740991),
            "string": ("", "ivy", "account-number-1", "a" * self._random.randint(1, 40), 'q"d'),
            "double": (0.0, 1.5, -2.25, 1e-05, 3.0, 12345.678, 1e20),
            "bool": (True, False),
            "char": ("a", "'", "\\", "\n"),
            "decimal": ("2500.50", "0", "-0", "1.000000001"),
            "date": ("2026-01-01", "1999-12-31"),
        }
        return self._random.choice(choices[type_text])


def test_rustfmt_leaves_a_random_corpus_as_it_is(tmp_path):
    corpus = _Corpus(CORPUS_SEED)
    for index in range(CORPUS_FILES):
        (tmp_path / f"corpus_{index}.rs").write_text(GENERATOR.generate(corpus.level_tests(index)))
    checked = rustfmt_check(tmp_path)
    assert checked.returncode == 0, checked.stdout[-4000:]


# real crates


def write_tree(tree: ProjectTree, root: Path) -> None:
    for file in tree.files:
        assert file.text is not None
        (root / file.path).parent.mkdir(parents=True, exist_ok=True)
        (root / file.path).write_text(file.text)


def crate(workspace: Path, problem: Problem, overlay: str | None) -> Path:
    """The problem's starter, its overlay over it, and the generated file of every level, in
    `projects/<slug>/` of a workspace whose runtime holds the vendored crates."""
    vendor = workspace / ".cs/runtime/runners/rust/vendor"
    if not vendor.exists():
        vendor.parent.mkdir(parents=True)
        vendor.symlink_to(VENDOR, target_is_directory=True)
    root = workspace / "projects" / problem.meta.slug
    files = problem.project_files
    assert files is not None
    assert files.starter is not None
    write_tree(files.starter, root)
    if overlay is not None:
        write_tree(files.overlays[overlay], root)
    for level in problem.meta.levels:
        tests = level_tests(problem, level.number)
        (root / tests.path).parent.mkdir(parents=True, exist_ok=True)
        (root / tests.path).write_text(GENERATOR.generate(tests))
    return root


def cargo(root: Path, subcommand: str, *arguments: str) -> subprocess.CompletedProcess[str]:
    """`cargo <subcommand> --offline <arguments>` in `root`, building into the workspace."""
    environment = {**os.environ, "CARGO_TARGET_DIR": str(root.parent.parent / "target")}
    command = ["cargo", subcommand, "--offline", *arguments]
    return subprocess.run(
        command, cwd=root, capture_output=True, text=True, check=False, env=environment
    )


@pytest.fixture(scope="module")
def bank(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("content"), RUST_PROJECT_PROBLEMS)
    return FsProblemRepository(root).load("bank-project-rust")


def test_the_fixtures_level_files_are_as_rustfmt_lays_them_out(bank, tmp_path):
    root = crate(tmp_path, bank, "reference")
    checked = rustfmt_check(root / "tests")
    assert checked.returncode == 0, checked.stdout


def test_the_fixtures_reference_passes_its_level_files(bank, tmp_path):
    tested = cargo(crate(tmp_path, bank, "reference"), "test")
    assert tested.returncode == 0, tested.stdout + tested.stderr


def test_the_fixtures_level_files_are_clippy_clean(bank, tmp_path):
    root = crate(tmp_path, bank, "reference")
    linted = cargo(
        root, "clippy", "--tests", "--", "-D", "warnings", "-A", "clippy::new_without_default"
    )
    assert linted.returncode == 0, linted.stderr[-4000:]


def test_the_bare_starter_fails_level_1_only_as_not_implemented(bank, tmp_path):
    root = crate(tmp_path, bank, None)
    (root / "tests" / "level_2.rs").unlink()
    tested = cargo(root, "test", "--test", "level_1")
    assert tested.returncode != 0
    assert NOT_IMPLEMENTED in tested.stdout + tested.stderr
    assert "error[" not in tested.stderr


VALUES_LIBRARY = """\
use chrono::NaiveDate;
use rust_decimal::Decimal;

#[derive(Default)]
pub struct Values {}

impl Values {
    pub fn new() -> Self {
        Values::default()
    }

    pub fn total(&mut self, amounts: Vec<Decimal>) -> Decimal {
        amounts.into_iter().sum()
    }

    pub fn next_day(&mut self, day: NaiveDate) -> NaiveDate {
        day.succ_opt().unwrap()
    }

    pub fn third(&mut self, value: f64) -> f64 {
        value / 3.0
    }

    pub fn thirds(&mut self, values: Vec<f64>) -> Vec<f64> {
        values.into_iter().map(|value| value / 3.0).collect()
    }

    pub fn names(&mut self, names: Vec<String>) -> Vec<String> {
        names.into_iter().rev().collect()
    }

    pub fn initials(&mut self, name: String) -> Vec<char> {
        name.chars().rev().collect()
    }

    pub fn empty(&mut self) -> Vec<Vec<i32>> {
        Vec::new()
    }

    pub fn even(&mut self, value: i64) -> bool {
        value % 2 == 0
    }
}
"""
VALUES_MANIFEST = """\
[package]
name = "bank"
version = "0.1.0"
edition = "2021"
rust-version = "1.80"
publish = false

[dependencies]
rust_decimal = { version = "=1.43.0", default-features = false, features = ["maths"] }
chrono = { version = "=0.4.45", default-features = false, features = ["std"] }
"""
VALUES_CONFIG = """\
[source.crates-io]
replace-with = "cstudy-vendor"

[source.cstudy-vendor]
directory = "../../.cs/runtime/runners/rust/vendor"
"""


def values_problem() -> Problem:
    methods = (
        method("total", 1, "amounts: list<decimal>", "decimal"),
        method("nextDay", 1, "day: date", "date"),
        method("third", 1, "value: double", "double"),
        method("thirds", 1, "values: double[]", "double[]"),
        method("names", 1, "names: list<string>", "list<string>"),
        method("initials", 1, "name: string", "char[]"),
        method("empty", 1, "", "list<list<int>>"),
        method("even", 1, "value: long", "bool"),
    )
    comparator = ComparatorSpec(
        ComparatorType.OPS,
        per_method={
            "third": ComparatorType.FLOAT,
            "thirds": ComparatorType.FLOAT,
            "names": ComparatorType.UNORDERED,
            "initials": ComparatorType.UNORDERED,
        },
    )
    signature = ClassSignature("Values", (), methods)
    meta = project_meta(signature=signature, comparator=comparator, language=Language.RUST)
    case = ops_case(
        "ex1",
        1,
        ("total", [["2.50", "0.25", "10"]], "12.75"),
        ("nextDay", ["2024-02-28"], "2024-02-29"),
        ("third", [1], 0.3333333333),
        ("thirds", [[3, 1.5]], [1, 0.5]),
        ("names", [["leo", "ivy"]], ["ivy", "leo"]),
        ("initials", ["ab"], ["a", "b"]),
        ("empty", [], []),
        ("even", [4], True),
        ("even", [5], False),
        class_name="Values",
    )
    return project_problem(case, meta=meta)


def test_every_kind_of_value_compiles_lints_clean_and_passes(tmp_path):
    problem = values_problem()
    vendor = tmp_path / ".cs/runtime/runners/rust/vendor"
    vendor.parent.mkdir(parents=True)
    vendor.symlink_to(VENDOR, target_is_directory=True)
    root = tmp_path / "projects" / "values"
    (root / "src").mkdir(parents=True)
    (root / ".cargo").mkdir()
    (root / "Cargo.toml").write_text(VALUES_MANIFEST)
    (root / ".cargo" / "config.toml").write_text(VALUES_CONFIG)
    (root / "src" / "lib.rs").write_text(VALUES_LIBRARY)
    tests = level_tests(problem, 1)
    (root / "tests").mkdir()
    (root / tests.path).write_text(GENERATOR.generate(tests))
    tested = cargo(root, "test")
    assert tested.returncode == 0, tested.stdout + tested.stderr
    linted = cargo(root, "clippy", "--tests", "--", "-D", "warnings")
    assert linted.returncode == 0, linted.stderr[-4000:]
