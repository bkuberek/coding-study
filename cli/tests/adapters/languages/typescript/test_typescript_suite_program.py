"""Suite jobs of runners/typescript/runner.ts: a project's `node:test` files, hosted in the runner
(docs/specs/runners.md#suite-job), through SubprocessRunner.

Most tests read one report: the whole suite runs once in one runner process (module fixture), and
each test inspects one test's outcome. Selection, restarts and the edge cases each run on their own.
"""

import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import RunnerLaunch
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS, Crashed, Raised, TimedOut
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Comparison,
    Passed,
    Skipped,
    SuiteFramework,
    SuiteJob,
    SuiteOutcome,
    SuiteReport,
)
from tests.helpers import REPOSITORY_ROOT, RUNNER_TRUNCATION_NOTICE

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

RUNNER_SCRIPT = REPOSITORY_ROOT / "runners" / "typescript" / "runner.ts"
HANG_GUARD_MS = 1_000
STDOUT_LIMIT_BYTES = 4096
STATUSES = "tests/statuses.test.ts"
FLOW = "tests/flow.test.ts"
BROKEN = "tests/broken.test.ts"
LOCKED = "tests/level-2.test.ts"
EVERY_OTHER_FILE = (FLOW, BROKEN, LOCKED)

PROJECT_FILES: Mapping[str, str] = {
    "package.json": '{"type": "module"}\n',
    "src/probe.ts": """\
import { suffix } from "./words.ts";

export class Probe {
  ping(): string {
    return `p${suffix()}`;
  }
}
""",
    "src/words.ts": 'export function suffix(): string {\n  return "ong";\n}\n',
    STATUSES: """\
import assert from "node:assert/strict";
import { before, describe, it, test } from "node:test";
import { Probe } from "../src/probe.ts";

test("passes", () => {
  assert.equal(new Probe().ping(), "pong");
});

test("fails an assertion", () => {
  assert.deepEqual([1, 2], [1, 3]);
});

test("fails a match", () => {
  assert.match("abc", /z/);
});

test("raises", () => {
  throw new RangeError("out of range");
});

test("prints", () => {
  console.log("to stdout");
  process.stderr.write("to stderr\\n");
});

test("prints a lot", () => {
  process.stdout.write("x".repeat(5000));
});

test("skips", { skip: "not today" }, () => {});

test("is to do", { todo: "later" }, () => {
  assert.equal(1, 2);
});

test("is to do and passes", { todo: true }, () => {});

test("exits", () => {
  process.exit(3);
});

test("resolves later", async () => {
  await new Promise((resolve) => setTimeout(resolve, 1));
});

test("has subtests", async (t) => {
  await t.test("first", () => {});
  await t.test("second", () => {
    assert.equal(1, 2);
  });
});

describe("outer", () => {
  it("inner", () => {});
  describe("deeper", () => {
    it("leaf", () => {});
  });
});

describe("broken suite", () => {
  throw new Error("suite body failed");
});

describe("guarded", () => {
  before(() => {
    throw new Error("before failed");
  });
  it("never runs", () => {});
});
""",
    FLOW: """\
import { test } from "node:test";

test("before the hang", () => {});

test("hangs", () => {
  while (true) {}
});

test("ends the process", () => {
  process.kill(process.pid, "SIGKILL");
});

test("after the crash", () => {});
""",
    BROKEN: 'import { missing } from "../src/missing.ts";\nmissing();\n',
    LOCKED: 'import { test } from "node:test";\n\ntest("locked", () => {});\n',
    "tests/helpers.ts": 'import { test } from "node:test";\n\ntest("not a test file", () => {});\n',
    "node_modules/dep/dep.test.ts": 'import { test } from "node:test";\n\ntest("dep", () => {});\n',
}


def write_project(directory: Path) -> Path:
    for path, text in PROJECT_FILES.items():
        (directory / path).parent.mkdir(parents=True, exist_ok=True)
        (directory / path).write_text(text, encoding="utf-8")
    return directory


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_project(tmp_path_factory.mktemp("probe-project"))


def run_suite(
    project: Path,
    exclude: tuple[str, ...] = EVERY_OTHER_FILE,
    select: tuple[str, ...] = (),
) -> SuiteReport:
    launch = RunnerLaunch(
        ("node", str(RUNNER_SCRIPT)), project, HELLO_TIMEOUT_MS[Language.TYPESCRIPT]
    )
    job = SuiteJob(
        "probe/suite", SuiteFramework.NODE_TEST, str(project), HANG_GUARD_MS, exclude, select
    )
    return SubprocessRunner(project.parent / f"{project.name}-runs").run_suite(launch, job)


@pytest.fixture(scope="module")
def statuses(project: Path) -> Mapping[str, SuiteOutcome]:
    report = run_suite(project)
    assert report.load_error is None
    return {test.test_id: test.outcome for test in report.tests}


def outcome(outcomes: Mapping[str, SuiteOutcome], name: str) -> SuiteOutcome:
    return outcomes[f"{STATUSES}::{name}"]


def raised(outcomes: Mapping[str, SuiteOutcome], name: str) -> Raised:
    found = outcome(outcomes, name)
    assert isinstance(found, Raised)
    return found


def failed(outcomes: Mapping[str, SuiteOutcome], name: str) -> AssertionFailed:
    found = outcome(outcomes, name)
    assert isinstance(found, AssertionFailed)
    return found


def test_a_passing_test_that_imports_project_files_is_ok(statuses):
    assert isinstance(outcome(statuses, "passes"), Passed)


def test_a_passing_test_reports_how_long_it_ran(statuses):
    passed = outcome(statuses, "passes")
    assert isinstance(passed, Passed)
    assert passed.duration_ns > 0


def test_an_async_test_is_ok_once_it_resolves(statuses):
    assert isinstance(outcome(statuses, "resolves later"), Passed)


def test_a_failed_assertion_is_failed_with_the_assertion_message(statuses):
    assert failed(statuses, "fails an assertion").message.startswith(
        "Expected values to be strictly deep-equal:"
    )


def test_a_failed_assertion_reports_expected_and_actual_as_json(statuses):
    comparison = failed(statuses, "fails an assertion").comparison
    assert comparison == Comparison(expected=[1, 3], actual=[1, 2])


def test_a_failed_assertion_on_values_that_are_not_json_leaves_out_both_sides(statuses):
    assert failed(statuses, "fails a match").comparison is None


def test_another_exception_is_an_error_with_its_type_and_message(statuses):
    error = raised(statuses, "raises").error
    assert (error.type, error.message) == ("RangeError", "out of range")


def test_an_error_trace_names_the_test_file(statuses):
    assert "statuses.test.ts:" in (raised(statuses, "raises").error.trace or "")


def test_process_exit_in_a_test_is_an_error(statuses):
    assert "process.exit(3)" in raised(statuses, "exits").error.message


def test_output_is_captured_per_test(statuses):
    passed = outcome(statuses, "prints")
    assert isinstance(passed, Passed)
    assert passed.stdout == "to stdout\nto stderr\n"


def test_output_is_cut_at_4_kib(statuses):
    passed = outcome(statuses, "prints a lot")
    assert isinstance(passed, Passed)
    assert passed.stdout == "x" * STDOUT_LIMIT_BYTES + RUNNER_TRUNCATION_NOTICE


def test_a_skipped_test_is_skipped_with_its_reason(statuses):
    skipped = outcome(statuses, "skips")
    assert isinstance(skipped, Skipped)
    assert skipped.message == "not today"


def test_a_failing_todo_test_is_skipped_as_to_do(statuses):
    skipped = outcome(statuses, "is to do")
    assert isinstance(skipped, Skipped)
    assert skipped.message == "todo: later"


def test_a_passing_todo_test_is_ok(statuses):
    assert isinstance(outcome(statuses, "is to do and passes"), Passed)


def test_tests_in_describe_blocks_are_named_from_the_outermost_block(statuses):
    assert isinstance(outcome(statuses, "outer > deeper > leaf"), Passed)


def test_subtests_belong_to_their_test(statuses):
    assert not any("has subtests >" in test_id for test_id in statuses)


def test_a_failed_subtest_fails_its_test_with_the_subtests_name(statuses):
    assert failed(statuses, "has subtests").message.startswith("second: ")


def test_a_describe_block_that_throws_is_an_error_named_after_the_block(statuses):
    assert raised(statuses, "broken suite").error.message == "suite body failed"


def test_a_failing_before_hook_is_an_error_of_its_block(statuses):
    assert raised(statuses, "guarded").error.message == "before failed"


def test_a_test_cancelled_by_its_blocks_hook_is_an_error(statuses):
    assert isinstance(outcome(statuses, "guarded > never runs"), Raised)


def test_suites_that_only_hold_tests_are_not_reported(statuses):
    assert f"{STATUSES}::outer" not in statuses


def test_excluded_files_do_not_run(statuses):
    assert not any(test_id.startswith((FLOW, LOCKED, BROKEN)) for test_id in statuses)


def test_files_outside_the_default_test_patterns_do_not_run(statuses):
    assert not any(test_id.startswith(("tests/helpers.ts", "node_modules")) for test_id in statuses)


def test_a_test_file_that_does_not_import_is_one_error_named_after_the_file(project):
    report = run_suite(project, exclude=(STATUSES, FLOW, LOCKED))
    assert [(test.test_id, type(test.outcome)) for test in report.tests] == [(BROKEN, Raised)]


def test_a_test_that_hangs_times_out_and_the_suite_goes_on(project):
    report = run_suite(project, exclude=(STATUSES, BROKEN, LOCKED))
    assert [(test.test_id, type(test.outcome)) for test in report.tests] == [
        (f"{FLOW}::before the hang", Passed),
        (f"{FLOW}::hangs", TimedOut),
        (f"{FLOW}::ends the process", Crashed),
        (f"{FLOW}::after the crash", Passed),
    ]


def test_a_selected_test_runs_alone(project):
    report = run_suite(project, select=(f"{STATUSES}::outer > inner",))
    assert [test.test_id for test in report.tests] == [f"{STATUSES}::outer > inner"]


def test_a_test_is_selected_by_the_last_part_of_its_id(project):
    report = run_suite(project, exclude=(BROKEN, LOCKED), select=("passes",))
    assert [test.test_id for test in report.tests] == [f"{STATUSES}::passes"]


def test_a_selection_that_names_no_test_runs_nothing(project):
    assert run_suite(project, select=("absent",)).tests == ()


def test_a_file_that_does_not_import_is_reported_when_a_last_part_is_selected(project):
    report = run_suite(project, exclude=(STATUSES, FLOW, LOCKED), select=("absent",))
    assert [test.test_id for test in report.tests] == [BROKEN]


def test_a_failed_block_is_reported_when_a_test_inside_it_is_selected(project):
    report = run_suite(project, select=(f"{STATUSES}::guarded > never runs",))
    assert [test.test_id for test in report.tests] == [
        f"{STATUSES}::guarded > never runs",
        f"{STATUSES}::guarded",
    ]


def test_a_folder_without_test_files_reports_no_tests(tmp_path):
    (tmp_path / "package.json").write_text('{"type": "module"}\n')
    report = run_suite(tmp_path, exclude=())
    assert (report.tests, report.load_error, report.stopped_early) == ((), None, None)


def test_a_missing_root_is_a_load_error(tmp_path):
    launch = RunnerLaunch(("node", str(RUNNER_SCRIPT)), tmp_path, 5_000)
    job = SuiteJob("gone/suite", SuiteFramework.NODE_TEST, str(tmp_path / "gone"), HANG_GUARD_MS)
    report = SubprocessRunner(tmp_path / "runs").run_suite(launch, job)
    assert report.load_error is not None
