"""The real Go toolchain: `go build`, the Go runner and `SubprocessRunner` together.

Marked `slow`; skipped when `go` is not installed. Each test works in a copy of the practice
workspace's `go/` project that shares its runner runtime; the conformance fixtures run through
`cstudy verify --conformance` (tests/application/test_verify_conformance.py).
"""

import shutil
import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.debug_servers import InstalledDebugServers, this_machine
from coding_study.adapters.languages.go import create_runner
from coding_study.adapters.languages.go.runner import GoRunner
from coding_study.adapters.languages.go.toolchain import GoOutcome, SubprocessGo
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import (
    BuildFailed,
    Prepared,
    PrepareResult,
    References,
    ReferenceSource,
    UserCode,
)
from coding_study.domain.cases import FunctionInput, OperationSequence
from coding_study.domain.layout import reference_target, stub_path, user_target
from coding_study.domain.naming import symbol_names
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import JobReport, Raised, Returned, RunCase, RunJob, RunRequest
from tests.stub_contract import STUB_CASES
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("go") is None, reason="go is not installed"),
]

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
LRU_CACHE = next(case.meta for case in STUB_CASES if case.name == "lru-cache")
HASH_MAP = """package two_sum

func twoSum(nums []int, target int) []int {
	seen := map[int]int{}
	for i, n := range nums {
		if j, ok := seen[target-n]; ok {
			return []int{j, i}
		}
		seen[n] = i
	}
	return nil
}
"""
CASE = RunCase("ex1", FunctionInput({"nums": [2, 7, 11, 15], "target": 9}), 10_000)


@pytest.fixture
def root(tmp_path: Path, practice_workspace: Path) -> Path:
    destination = workspace_like(practice_workspace, tmp_path / "ws")
    shutil.copytree(practice_workspace / "go", destination / "go")
    return destination


def write_solution(root: Path, source: str, meta: ProblemMeta = TWO_SUM) -> None:
    path = root / stub_path(meta, Language.GO)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def prepare(root: Path, meta: ProblemMeta = TWO_SUM) -> PrepareResult:
    runner = create_runner(LanguageContext(root, root / RUNTIME_RUNNERS))
    return runner.prepare(UserCode(meta), lambda _: None)


def run(
    root: Path,
    result: PrepareResult,
    meta: ProblemMeta = TWO_SUM,
    approach: str | None = None,
    case: RunCase = CASE,
) -> JobReport:
    assert isinstance(result, Prepared), result
    target = (
        user_target(meta, Language.GO, str(root))
        if approach is None
        else reference_target(meta, approach, Language.GO, str(root))
    )
    job = RunJob(
        job_id=meta.slug,
        kind=meta.kind,
        target=target,
        names=symbol_names(meta.signature, Language.GO),
        signature=meta.signature,
        cases=(case,),
    )
    report = SubprocessRunner(root / ".cs" / "runs").run(result.launch, RunRequest((job,)))
    return report.job(meta.slug)


def test_the_users_function_runs_and_returns(root):
    write_solution(root, HASH_MAP)
    (case,) = run(root, prepare(root)).cases
    assert isinstance(case.outcome, Returned)
    assert case.outcome.output == [0, 1]


def test_the_users_go_settings_do_not_reach_the_build(root, tmp_path, monkeypatch):
    settings = tmp_path / "go-env"
    settings.write_text("GOFLAGS=-mod=mod\nGOOS=windows\n")
    monkeypatch.setenv("GOENV", str(settings))
    monkeypatch.setenv("GOARCH", "386")
    write_solution(root, HASH_MAP)
    (case,) = run(root, prepare(root)).cases
    assert isinstance(case.outcome, Returned)


def test_a_misnamed_function_is_a_load_error_with_the_compilers_reason(root):
    write_solution(root, HASH_MAP.replace("func twoSum(", "func twoSumm("))
    load_error = run(root, prepare(root)).load_error
    assert load_error is not None
    assert (load_error.type, load_error.message) == (
        "SymbolNotFound",
        'the package defines no function "twoSum": undefined: twoSum',
    )


def test_a_compile_error_names_the_users_file(root):
    write_solution(root, HASH_MAP.replace("return nil", "return nill"))
    result = prepare(root)
    assert result == BuildFailed(("go/practice/two_sum/two_sum.go:11:9: undefined: nill",))


def test_a_panic_names_the_users_line(root):
    write_solution(root, HASH_MAP.replace("seen := map[int]int{}", "var seen map[int]int"))
    (case,) = run(root, prepare(root)).cases
    assert isinstance(case.outcome, Raised)
    assert (case.outcome.error.message, case.outcome.error.trace) == (
        "assignment to entry in nil map",
        "two_sum.go:9 in twoSum",
    )


def test_concurrent_builds_each_run_their_own_binary(root):
    write_solution(root, HASH_MAP)
    results: list[PrepareResult] = []
    threads = [threading.Thread(target=lambda: results.append(prepare(root))) for _ in range(3)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    binaries = {result.launch.command[0] for result in results if isinstance(result, Prepared)}
    assert len(binaries) == 3
    assert all(isinstance(run(root, result).cases[0].outcome, Returned) for result in results)


def test_a_slug_ending_in_a_test_suffix_still_builds_the_users_file(root):
    meta = replace(TWO_SUM, slug="two-sum-test")
    write_solution(root, HASH_MAP.replace("package two_sum", "package two_sum_test"), meta)
    (case,) = run(root, prepare(root, meta), meta).cases
    assert isinstance(case.outcome, Returned)


@pytest.mark.parametrize("approach", ["sort-windows", "sort-test", "sort-linux-arm64"])
def test_a_reference_named_like_a_go_build_constraint_still_builds(root, tmp_path, approach):
    path = tmp_path / "solutions" / f"{approach}.go"
    path.parent.mkdir()
    path.write_text(HASH_MAP)
    runner = create_runner(LanguageContext(root, root / RUNTIME_RUNNERS))
    prepared = runner.prepare(
        References(TWO_SUM, (ReferenceSource(approach, path),)), lambda _: None
    )
    (case,) = run(root, prepared, approach=approach).cases
    assert isinstance(case.outcome, Returned)


CACHE_OPERATIONS = RunCase(
    "ops",
    OperationSequence(("LRUCache", "put", "get", "get"), ((2,), (1, 10), (1,), (3,))),
    10_000,
)
CACHE = """package lru_cache

type LRUCache struct{ values map[int]int }

func NewLRUCache(capacity int) *LRUCache { return &LRUCache{values: map[int]int{}} }

func (c *LRUCache) Get(key int) int {
	if value, ok := c.values[key]; ok {
		return value
	}
	return -1
}

func (c *LRUCache) Put(key int, value int) { c.values[key] = value }
"""


@dataclass
class CountingGo:
    """The real `go`, counting its builds: a second one means the thunks were left out."""

    builds: int = 0
    real: SubprocessGo = field(default_factory=SubprocessGo)

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> GoOutcome:
        self.builds += 1
        return self.real.build(arguments, cwd, environment)


def prepare_class(root: Path, go: CountingGo) -> PrepareResult:
    runner = GoRunner(
        LanguageContext(root, root / RUNTIME_RUNNERS), go, InstalledDebugServers(this_machine())
    )
    return runner.prepare(UserCode(LRU_CACHE), lambda _: None)


def run_class(root: Path, source: str, go: CountingGo) -> JobReport:
    write_solution(root, source, LRU_CACHE)
    return run(root, prepare_class(root, go), LRU_CACHE, case=CACHE_OPERATIONS)


def test_a_design_problems_methods_run_through_the_generated_thunks(root):
    go = CountingGo()
    (case,) = run_class(root, CACHE, go).cases
    assert isinstance(case.outcome, Returned)
    assert (case.outcome.output, go.builds) == ([None, None, 10, -1], 1)


def test_a_panic_in_a_method_names_the_users_line_and_not_the_thunk(root):
    go = CountingGo()
    source = CACHE.replace("return -1", "return c.values[key] / (key - key)")
    (case,) = run_class(root, source, go).cases
    assert isinstance(case.outcome, Raised)
    assert (go.builds, case.outcome.error.trace) == (1, "lru_cache.go:11 in LRUCache.Get")


def test_a_method_with_another_signature_is_a_signature_mismatch(root):
    go = CountingGo()
    source = CACHE.replace(
        "Put(key int, value int) { c.values[key]", "Put(key int64, value int) { c.values[int(key)]"
    )
    report = run_class(root, source, go)
    assert report.load_error is not None
    assert (report.load_error.type, report.load_error.message) == (
        "SignatureMismatch",
        '"Put" takes int64 for "key"; int is int in Go',
    )
    assert go.builds == 2


def test_a_method_with_another_arity_is_a_signature_mismatch(root):
    go = CountingGo()
    report = run_class(
        root,
        CACHE.replace("Put(key int, value int) { c.values[key] = value }", "Put(key int) {}"),
        go,
    )
    assert report.load_error is not None
    assert report.load_error.message == '"Put" takes 1 parameters; the signature declares 2'


def test_a_method_with_another_result_is_a_signature_mismatch(root):
    go = CountingGo()
    source = CACHE.replace("Get(key int) int {", "Get(key int) int64 {").replace(
        "return value", "return int64(value)"
    )
    report = run_class(root, source, go)
    assert report.load_error is not None
    assert report.load_error.message == '"Get" must return int for int'
    assert go.builds == 1


def test_a_class_without_the_declared_type_still_runs_through_reflection(root):
    go = CountingGo()
    source = CACHE.replace("LRUCache", "Cache").replace("NewCache", "NewLRUCache")
    (case,) = run_class(root, source, go).cases
    assert isinstance(case.outcome, Returned)
    assert (case.outcome.output, go.builds) == ([None, None, 10, -1], 2)


def test_a_constructor_of_another_type_still_runs_through_reflection(root):
    go = CountingGo()
    source = CACHE.replace(
        "func NewLRUCache(capacity int) *LRUCache { return &LRUCache{values: map[int]int{}} }",
        "type Cache struct{ LRUCache }\n\n"
        "func NewLRUCache(capacity int) *Cache { return &Cache{LRUCache{values: map[int]int{}}} }",
    )
    (case,) = run_class(root, source, go).cases
    assert isinstance(case.outcome, Returned)
    assert (case.outcome.output, go.builds) == ([None, None, 10, -1], 1)
