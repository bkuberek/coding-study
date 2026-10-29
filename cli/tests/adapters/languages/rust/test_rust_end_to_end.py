"""The real Rust toolchain: `cargo build`, the Rust runner and `SubprocessRunner` together.

Marked `slow`; skipped when `cargo` is not installed. Each test works in a workspace that shares
the practice workspace's runner runtime and builds in its own `.cs/build/rust`; the conformance
fixtures run through `cstudy verify --conformance` (tests/application/test_verify_conformance.py).
"""

import shutil
import threading
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.rust import create_runner
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
    pytest.mark.skipif(shutil.which("cargo") is None, reason="cargo is not installed"),
]

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
HASH_MAP = """use std::collections::HashMap;

pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let mut seen = HashMap::new();
    for (i, n) in nums.iter().enumerate() {
        if let Some(&j) = seen.get(&(target - n)) {
            return vec![j as i32, i as i32];
        }
        seen.insert(*n, i);
    }
    vec![]
}
"""
CASE = RunCase("ex1", FunctionInput({"nums": [2, 7, 11, 15], "target": 9}), 10_000)
HOSTILE_CARGO_CONFIG = """[build]
rustc-wrapper = "/nonexistent/sccache"
rustflags = ["-C", "not-a-flag"]
target-dir = "/nonexistent/target"
target = "wasm32-unknown-unknown"

[profile.release]
overflow-checks = false
panic = "abort"
"""
STRIPPING_CARGO_CONFIG = """[profile.release]
strip = true
split-debuginfo = "packed"
"""
OVERFLOW = HASH_MAP.replace("(target - n)", "(target + n * 1_000_000)")
BIG = RunCase("big", FunctionInput({"nums": [5000, 1], "target": 2_147_000_000}), 10_000)


@pytest.fixture
def root(tmp_path: Path, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path / "ws")


def write_solution(root: Path, source: str, meta: ProblemMeta = TWO_SUM) -> None:
    path = root / stub_path(meta, Language.RUST)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)


def prepare(root: Path, meta: ProblemMeta = TWO_SUM) -> PrepareResult:
    runner = create_runner(LanguageContext(root, root / RUNTIME_RUNNERS))
    return runner.prepare(UserCode(meta), lambda _: None)


def run(root: Path, result: PrepareResult, case: RunCase = CASE) -> JobReport:
    assert isinstance(result, Prepared), result
    job = RunJob(
        job_id=TWO_SUM.slug,
        kind=TWO_SUM.kind,
        target=user_target(TWO_SUM, Language.RUST, str(root)),
        names=symbol_names(TWO_SUM.signature, Language.RUST),
        signature=TWO_SUM.signature,
        cases=(case,),
    )
    report = SubprocessRunner(root / ".cs" / "runs").run(result.launch, RunRequest((job,)))
    return report.job(TWO_SUM.slug)


def test_the_users_function_runs_and_returns(root):
    write_solution(root, HASH_MAP)
    (case,) = run(root, prepare(root)).cases
    assert isinstance(case.outcome, Returned)
    assert case.outcome.output == [0, 1]


def test_a_misnamed_function_is_a_load_error_with_the_compilers_reason(root):
    write_solution(root, HASH_MAP.replace("pub fn two_sum(", "pub fn two_summ("))
    load_error = run(root, prepare(root)).load_error
    assert load_error is not None
    assert (load_error.type, load_error.message) == (
        "SymbolNotFound",
        "cannot find function `two_sum` in `two_sum.rs`; "
        "a function with a similar name exists: `two_summ`",
    )


def test_a_compile_error_names_the_users_file(root):
    write_solution(root, HASH_MAP.replace("    vec![]\n}", "    nil\n}"))
    result = prepare(root)
    assert isinstance(result, BuildFailed)
    assert result.diagnostics[0] == (
        "rust/practice/two_sum.rs:11:5: error[E0425]: cannot find value `nil` in this scope"
    )


def test_an_overflow_panics_and_names_the_users_line(root):
    write_solution(root, OVERFLOW)
    (case,) = run(root, prepare(root), BIG).cases
    assert isinstance(case.outcome, Raised)
    assert (case.outcome.error.message, case.outcome.error.trace) == (
        "attempt to multiply with overflow",
        "two_sum.rs:6 in two_sum",
    )


def test_a_users_strip_setting_keeps_the_function_names_in_traces(root):
    (root / ".cargo").mkdir()
    (root / ".cargo/config.toml").write_text(STRIPPING_CARGO_CONFIG)
    write_solution(root, OVERFLOW)
    (case,) = run(root, prepare(root), BIG).cases
    assert isinstance(case.outcome, Raised)
    assert case.outcome.error.trace == "two_sum.rs:6 in two_sum"


def test_the_users_cargo_settings_do_not_reach_the_build(root, monkeypatch):
    (root / ".cargo").mkdir()
    (root / ".cargo/config.toml").write_text(HOSTILE_CARGO_CONFIG)
    monkeypatch.setenv("RUSTFLAGS", "-C not-a-flag")
    monkeypatch.setenv("RUSTC_WRAPPER", "/nonexistent/sccache")
    monkeypatch.setenv("CARGO_BUILD_TARGET", "wasm32-unknown-unknown")
    monkeypatch.setenv("CARGO_TARGET_DIR", "/nonexistent/target")
    write_solution(root, HASH_MAP)
    (case,) = run(root, prepare(root)).cases
    assert isinstance(case.outcome, Returned)


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
