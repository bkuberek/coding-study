"""The real Go toolchain: `go build`, the Go runner and `SubprocessRunner` together.

Marked `slow`; skipped when `go` is not installed. Each test works in a copy of the practice
workspace's `go/` project that shares its runner runtime; the conformance fixtures run through
`cstudy verify --conformance` (tests/application/test_verify_conformance.py).
"""

import shutil
import threading
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go import create_runner
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import BuildFailed, Prepared, PrepareResult, UserCode
from coding_study.domain.cases import FunctionInput
from coding_study.domain.layout import stub_path, user_target
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


def run(root: Path, result: PrepareResult, meta: ProblemMeta = TWO_SUM) -> JobReport:
    assert isinstance(result, Prepared), result
    job = RunJob(
        job_id=meta.slug,
        kind=meta.kind,
        target=user_target(meta, Language.GO, str(root)),
        names=symbol_names(meta.signature, Language.GO),
        signature=meta.signature,
        cases=(CASE,),
    )
    report = SubprocessRunner(root / ".cs" / "runs").run(result.launch, RunRequest((job,)))
    return report.job(meta.slug)


def test_the_users_function_runs_and_returns(root):
    write_solution(root, HASH_MAP)
    (case,) = run(root, prepare(root)).cases
    assert isinstance(case.outcome, Returned)
    assert case.outcome.output == [0, 1]


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
