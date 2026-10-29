"""Bench mode of every runner (Python, TypeScript, JVM) through `SubprocessRunner.bench`.

The same behaviors are checked in each runtime; only the sources differ. Marked `slow`: it starts
the real runtimes, and the JVM case compiles its sources with Gradle once per module.
"""

import shutil
import textwrap
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.jvm.gradle import WrapperGradle, default_gradle_user_home
from coding_study.adapters.languages.jvm.runner import JvmRunner
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import Prepared, References, ReferenceSource, RunnerLaunch
from coding_study.domain.bench_runs import (
    BenchInput,
    BenchJob,
    BenchReport,
    BenchRequest,
    BenchSettings,
    BenchTarget,
    Warmup,
)
from coding_study.domain.cases import FunctionInput, OperationSequence
from coding_study.domain.layout import reference_target
from coding_study.domain.naming import symbol_names
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.runs import FileTarget, Raised, RunTarget
from coding_study.domain.signature import ClassSignature, FunctionSignature, Method, Param, Returns
from coding_study.domain.type_dsl import ArrayType, Scalar, ScalarType
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

INT = ScalarType(Scalar.INT)
LINEAR = ComplexityClass.LINEAR
APPROACHES = tuple(
    Approach(name, name, ApproachRole.OPTIMAL, "O(n)", "O(1)", LINEAR, LINEAR)
    for name in ("echo", "raises", "slow", "drains", "counter")
)


def meta(
    slug: str, kind: ProblemKind, signature: FunctionSignature | ClassSignature
) -> ProblemMeta:
    return ProblemMeta(
        id="9999",
        slug=slug,
        title=slug,
        status=ContentStatus.DRAFT,
        difficulty=Difficulty.EASY,
        track=Track.PRACTICAL,
        kind=kind,
        signature=signature,
        comparator=ComparatorSpec(ComparatorType.EXACT),
        approaches=APPROACHES,
    )


ECHO = meta(
    "bench-echo",
    ProblemKind.FUNCTION,
    FunctionSignature("echo", (Param("value", INT),), Returns(INT)),
)
DRAIN = meta(
    "bench-drain",
    ProblemKind.FUNCTION,
    FunctionSignature("echo", (Param("value", ArrayType(INT)),), Returns(INT)),
)
COUNTER = meta(
    "bench-counter",
    ProblemKind.DESIGN,
    ClassSignature(
        "Counter", (Param("start", INT),), (Method("add", (Param("amount", INT),), Returns(INT)),)
    ),
)


def source(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


PYTHON_SOURCES = {
    "echo": source(
        """
        def echo(value):
            return value
        """
    ),
    "raises": source(
        """
        def echo(value):
            if value == 2:
                raise ValueError("two")
            return value
        """
    ),
    "slow": source(
        """
        import time


        def echo(value):
            time.sleep(value / 1000)
            return value
        """
    ),
    "drains": source(
        """
        def echo(value):
            if not value:
                raise ValueError("reused input")
            value.clear()
            return 0
        """
    ),
    "counter": source(
        """
        class Counter:
            def __init__(self, start):
                self.total = start

            def add(self, amount):
                self.total += amount
                return self.total
        """
    ),
}
TYPESCRIPT_SOURCES = {
    "echo": source(
        """
        export function echo(value: number): number {
          return value;
        }
        """
    ),
    "raises": source(
        """
        export function echo(value: number): number {
          if (value === 2) {
            throw new Error("two");
          }
          return value;
        }
        """
    ),
    "slow": source(
        """
        export function echo(value: number): number {
          const end = Date.now() + value;
          while (Date.now() < end) {}
          return value;
        }
        """
    ),
    "drains": source(
        """
        export function echo(value: number[]): number {
          if (value.length === 0) {
            throw new Error("reused input");
          }
          value.length = 0;
          return 0;
        }
        """
    ),
    "counter": source(
        """
        export class Counter {
          total: number;
          constructor(start: number) {
            this.total = start;
          }
          add(amount: number): number {
            this.total += amount;
            return this.total;
          }
        }
        """
    ),
}
JAVA_SOURCES = {
    "echo": source(
        """
        public class Solution {
            public int echo(int value) {
                return value;
            }
        }
        """
    ),
    "raises": source(
        """
        public class Solution {
            public int echo(int value) {
                if (value == 2) {
                    throw new IllegalStateException("two");
                }
                return value;
            }
        }
        """
    ),
    "slow": source(
        """
        public class Solution {
            public int echo(int value) {
                long end = System.nanoTime() + value * 1_000_000L;
                while (System.nanoTime() < end) {
                }
                return value;
            }
        }
        """
    ),
    "drains": source(
        """
        public class Solution {
            public int echo(int[] value) {
                if (value[0] == -1) {
                    throw new IllegalStateException("reused input");
                }
                value[0] = -1;
                return 0;
            }
        }
        """
    ),
    "counter": source(
        """
        public class Counter {
            private int total;

            public Counter(int start) {
                total = start;
            }

            public int add(int amount) {
                total += amount;
                return total;
            }
        }
        """
    ),
}
PROBLEM_APPROACHES = {
    ECHO.slug: ("echo", "raises", "slow"),
    DRAIN.slug: ("drains",),
    COUNTER.slug: ("counter",),
}
MEMORY_METRICS = {
    Language.PYTHON: "tracemalloc_peak",
    Language.TYPESCRIPT: "heap_used_delta",
    Language.JAVA: "thread_allocated_bytes",
}


@dataclass(frozen=True)
class Runtime:
    """Launches one language's runner on references materialized for it."""

    language: Language
    launch: Callable[[ProblemMeta, Mapping[str, Path]], RunnerLaunch]
    sources: Mapping[str, str]
    extension: str


class PythonLaunch:
    """The practice workspace's interpreter, whose venv provides `cs_runner`."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    def __call__(self, meta: ProblemMeta, files: Mapping[str, Path]) -> RunnerLaunch:
        interpreter = self._workspace / "python" / ".venv" / "bin" / "python"
        return RunnerLaunch((str(interpreter), "-m", "cs_runner"), self._workspace, 5_000)


def typescript_launch(meta: ProblemMeta, files: Mapping[str, Path]) -> RunnerLaunch:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    script = REPOSITORY_ROOT / "runners" / "typescript" / "runner.ts"
    return RunnerLaunch(("node", "--expose-gc", str(script)), REPOSITORY_ROOT, 5_000)


class JvmLaunches:
    """Compiles each problem's references once, in a temporary copy of the workspace.

    A launch is reused for every run of its problem, so it keeps its private class copy: without
    `scratch`, `SubprocessRunner` does not remove it after the first run.
    """

    def __init__(self, root: Path) -> None:
        self._root = root
        self._built: dict[str, RunnerLaunch] = {}

    def __call__(self, meta: ProblemMeta, files: Mapping[str, Path]) -> RunnerLaunch:
        if meta.slug not in self._built:
            gradle = WrapperGradle(self._root / "jvm", default_gradle_user_home())
            runner = JvmRunner(
                LanguageContext(self._root, self._root / RUNTIME_RUNNERS), Language.JAVA, gradle
            )
            sources = tuple(ReferenceSource(name, path) for name, path in files.items())
            prepared = runner.prepare(References(meta, sources), lambda _line: None)
            assert isinstance(prepared, Prepared), prepared
            self._built[meta.slug] = replace(prepared.launch, scratch=None)
        return self._built[meta.slug]


@pytest.fixture(scope="module")
def jvm_root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("jvm-bench") / "ws")


@pytest.fixture(scope="module")
def jvm_launches(jvm_root: Path) -> JvmLaunches:
    return JvmLaunches(jvm_root)


@pytest.fixture(params=[Language.PYTHON, Language.TYPESCRIPT, Language.JAVA], ids=str)
def runtime(request: pytest.FixtureRequest) -> Runtime:
    match request.param:
        case Language.PYTHON:
            launch = PythonLaunch(request.getfixturevalue("practice_workspace"))
            return Runtime(Language.PYTHON, launch, PYTHON_SOURCES, "py")
        case Language.TYPESCRIPT:
            return Runtime(Language.TYPESCRIPT, typescript_launch, TYPESCRIPT_SOURCES, "ts")
        case _:
            launches = request.getfixturevalue("jvm_launches")
            return Runtime(Language.JAVA, launches, JAVA_SOURCES, "java")


SETTINGS = BenchSettings(2, Warmup(1, 3, 0.05), 2000, True, 0)
SIZES = (1, 2, 3)


class Bench:
    def __init__(self, runtime: Runtime, directory: Path) -> None:
        self._runtime = runtime
        self._directory = directory

    def run(
        self,
        meta: ProblemMeta,
        targets: Mapping[str, str],
        inputs: tuple[BenchInput, ...],
        settings: BenchSettings = SETTINGS,
        outputs: frozenset[str] = frozenset(),
    ) -> BenchReport:
        """`targets` maps target id to approach; `missing` names no file."""
        files = self._write(meta)
        launch = self._runtime.launch(meta, files)
        names = symbol_names(meta.signature, self._runtime.language)
        job = BenchJob(
            job_id=meta.slug,
            kind=meta.kind,
            signature=meta.signature,
            targets=tuple(
                BenchTarget(
                    target_id, self._target(meta, approach, files), names, target_id in outputs
                )
                for target_id, approach in targets.items()
            ),
            inputs=inputs,
            settings=settings,
            hang_guard_ms=10_000,
        )
        return SubprocessRunner(self._directory / "runs").bench(launch, BenchRequest(job))

    def _write(self, meta: ProblemMeta) -> dict[str, Path]:
        """Every approach of the problem, so the JVM compiles them all on first use."""
        files: dict[str, Path] = {}
        for approach in PROBLEM_APPROACHES[meta.slug]:
            path = self._directory / meta.slug / f"{approach}.{self._runtime.extension}"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(self._runtime.sources[approach], encoding="utf-8")
            files[approach] = path
        return files

    def _target(self, meta: ProblemMeta, approach: str, files: Mapping[str, Path]) -> RunTarget:
        if self._runtime.language is Language.JAVA:
            return reference_target(meta, approach, Language.JAVA, str(REPOSITORY_ROOT))
        missing = self._directory / f"{approach}.{self._runtime.extension}"
        return FileTarget(str(files.get(approach, missing)))


def echo_inputs(*sizes: int, max_batch: int = 1) -> tuple[BenchInput, ...]:
    return tuple(BenchInput(size, FunctionInput({"value": size}), max_batch) for size in sizes)


@pytest.fixture
def bench(runtime: Runtime, tmp_path: Path) -> Bench:
    return Bench(runtime, tmp_path)


def test_every_target_gets_a_sample_per_rep_and_size(bench):
    report = bench.run(ECHO, {"a": "echo", "b": "echo"}, echo_inputs(*SIZES))
    counts = [[len(measured.samples) for measured in report.target(t).sizes] for t in ("a", "b")]
    assert counts == [[2, 2, 2], [2, 2, 2]]


def test_fast_calls_are_batched(bench):
    settings = replace(SETTINGS, min_sample_ns=10**9)
    report = bench.run(ECHO, {"a": "echo"}, echo_inputs(1, max_batch=40), settings)
    assert {sample.calls for sample in report.target("a").sizes[0].samples} == {40}


def test_output_targets_report_each_check_call(bench):
    report = bench.run(ECHO, {"a": "echo"}, echo_inputs(*SIZES), outputs=frozenset({"a"}))
    assert [m.output.value for m in report.target("a").sizes if m.output] == [1, 2, 3]


def test_a_call_over_the_budget_stops_the_target(bench):
    settings = replace(SETTINGS, budget_ms=10)
    report = bench.run(ECHO, {"a": "slow"}, echo_inputs(1, 30, 40), settings)
    assert [(m.size, m.exceeded_ns is not None) for m in report.target("a").sizes] == [
        (1, False),
        (30, True),
    ]


def test_an_exception_stops_the_target(bench):
    report = bench.run(ECHO, {"a": "raises"}, echo_inputs(*SIZES))
    failure = report.target("a").sizes[-1].failure
    assert (report.target("a").sizes[-1].size, isinstance(failure, Raised)) == (2, True)


def test_memory_uses_the_runtimes_metric(bench, runtime):
    report = bench.run(ECHO, {"a": "echo"}, echo_inputs(*SIZES))
    metrics = {m.memory.metric for m in report.target("a").sizes if m.memory}
    assert metrics == {MEMORY_METRICS[runtime.language]}


def test_a_target_that_does_not_load_has_a_load_error(bench):
    report = bench.run(ECHO, {"gone": "missing", "a": "echo"}, echo_inputs(*SIZES))
    assert report.target("gone").load_error is not None


def test_the_other_targets_run_when_one_does_not_load(bench):
    report = bench.run(ECHO, {"gone": "missing", "a": "echo"}, echo_inputs(*SIZES))
    assert [m.size for m in report.target("a").sizes if m.samples] == list(SIZES)


def test_every_call_gets_a_fresh_input(bench):
    settings = replace(SETTINGS, min_sample_ns=10**8)
    inputs = (BenchInput(3, FunctionInput({"value": [1, 2, 3]}), 30),)
    report = bench.run(DRAIN, {"a": "drains"}, inputs, settings)
    assert report.target("a").sizes[0].failure is None


def counter_input(size: int) -> BenchInput:
    sequence = OperationSequence(("Counter", *(["add"] * size)), ((0,), *([(1,)] * size)))
    return BenchInput(size, sequence, 1)


def test_class_kinds_time_the_whole_sequence(bench):
    report = bench.run(COUNTER, {"a": "counter"}, (counter_input(3),), outputs=frozenset({"a"}))
    measured = report.target("a").sizes[0]
    assert (measured.output.value if measured.output else None, len(measured.samples)) == (
        [None, 1, 2, 3],
        2,
    )


def test_the_runner_reports_its_runtime(bench, runtime):
    report = bench.run(ECHO, {"a": "echo"}, echo_inputs(1))
    assert report.runner.runner == {"python": "python", "typescript": "typescript"}.get(
        runtime.language, "jvm"
    )
