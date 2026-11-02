"""A virtual-clock Go project graded through the real toolchain: `go test -c` of the entry's
package, the generated test main and the runner in a `testing/synctest` bubble per case
(docs/specs/runners.md#go-project-jobs).

Marked `slow`; skipped when `go` is not installed. The project is the conformance fixture
9034-conformance-project-clock-go, whose cases that deadlock or hang run through
`cstudy verify --conformance`.
"""

import shutil
from pathlib import Path

import pytest

from coding_study.adapters.conformance_fixtures import conformance_repository
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.debug_servers import InstalledDebugServers, this_machine
from coding_study.adapters.languages.go.runner import GoRunner
from coding_study.adapters.languages.go.toolchain import SubprocessGo
from coding_study.adapters.runner_runtime import RUNTIME_RUNNERS
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import ProjectGrading
from coding_study.domain.cases import OperationSequence
from coding_study.domain.layout import COMPILED_USER_TARGET
from coding_study.domain.naming import symbol_names
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.runner_grading import graded_signature
from coding_study.domain.runs import (
    CompiledTarget,
    JobReport,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunRequest,
)
from tests.helpers import REPOSITORY_ROOT
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("go") is None, reason="go is not installed"),
]

SLUG = "conformance-project-clock-go"
FIXTURE = REPOSITORY_ROOT / "runners" / "conformance" / "9034-conformance-project-clock-go"
HANG_GUARD_MS = 10_000
ADVANCE = RunCase(
    "advance",
    OperationSequence(
        ("Inbox", "@now", "@advance", "@now", "sleep", "@now"),
        ((), (), (1500,), (), (2500,), ()),
    ),
    HANG_GUARD_MS,
)
SPAWN_JOIN = RunCase(
    "spawn-join",
    OperationSequence(
        ("Inbox", "@spawn", "@advance", "publish", "@join", "@now", "receive", "@now"),
        ((), ("r1", "receive", 5000), (1000,), ("a",), ("r1",), (), (2000,), ()),
    ),
    HANG_GUARD_MS,
)


@pytest.fixture(scope="module")
def meta() -> ProblemMeta:
    return conformance_repository(REPOSITORY_ROOT).load(SLUG).meta


@pytest.fixture
def workspace(tmp_path: Path, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path / "ws")


@pytest.fixture
def root(workspace: Path) -> Path:
    """The reference: the starter, then the reference's overlay."""
    folder = workspace / "projects" / SLUG
    shutil.copytree(FIXTURE / "starter", folder)
    shutil.copytree(FIXTURE / "solutions" / "reference", folder, dirs_exist_ok=True)
    return folder


def grade(workspace: Path, root: Path, meta: ProblemMeta, *cases: RunCase) -> JobReport:
    assert meta.project is not None
    context = LanguageContext(workspace, workspace / RUNTIME_RUNNERS)
    runner = GoRunner(context, SubprocessGo(), InstalledDebugServers(this_machine()))
    launch = runner.prepare_project(ProjectGrading(root, meta, 1), lambda _: None)
    signature = graded_signature(meta.signature, 1)
    job = RunJob(
        job_id=SLUG,
        kind=ProblemKind.PROJECT,
        target=CompiledTarget(COMPILED_USER_TARGET),
        names=symbol_names(signature, Language.GO),
        signature=signature,
        cases=cases,
        clock=meta.project.clock,
    )
    report = SubprocessRunner(workspace / ".cs" / "runs").run(launch, RunRequest((job,)))
    return report.job(SLUG)


def outputs(job: JobReport) -> list[object]:
    return [
        case.outcome.output if isinstance(case.outcome, Returned) else case for case in job.cases
    ]


def test_each_case_runs_on_a_virtual_clock_of_its_own(workspace, root, meta):
    job = grade(workspace, root, meta, ADVANCE, SPAWN_JOIN)
    assert outputs(job) == [
        [None, 0, None, 1500, 2500, 4000],
        [None, None, None, 1, "a", 1000, "", 3000],
    ]


def test_the_packages_own_test_files_never_block_grading(workspace, root, meta):
    (root / "inbox_test.go").write_text("package inbox\n\nfunc TestMain(\n")
    assert outputs(grade(workspace, root, meta, ADVANCE)) == [[None, 0, None, 1500, 2500, 4000]]


def test_a_vet_finding_does_not_block_grading(workspace, root, meta):
    (root / "noise.go").write_text(
        'package inbox\n\nimport "fmt"\n\nfunc noise() { fmt.Printf("%d\\n", "x") }\n'
    )
    assert outputs(grade(workspace, root, meta, ADVANCE)) == [[None, 0, None, 1500, 2500, 4000]]


def test_a_panic_in_a_spawned_call_is_the_error_of_its_join(workspace, root, meta):
    source = (root / "inbox.go").read_text()
    (root / "inbox.go").write_text(source.replace("\tb.messages <- body\n", '\tpanic("closed")\n'))
    case = RunCase(
        "panics",
        OperationSequence(("Inbox", "@spawn", "@join"), ((), ("p", "publish", "a"), ("p",))),
        HANG_GUARD_MS,
    )
    (report,) = grade(workspace, root, meta, case).cases
    outcome = report.outcome
    assert isinstance(outcome, Raised)
    assert (outcome.error.message, outcome.op_index, outcome.error.trace) == (
        "closed",
        2,
        "inbox.go:30 in Inbox.Publish",
    )


def test_a_project_that_does_not_compile_is_a_load_error(workspace, root, meta):
    (root / "inbox.go").write_text((root / "inbox.go").read_text() + "\nfunc broken() { x }\n")
    job = grade(workspace, root, meta, ADVANCE)
    error = job.load_error
    assert error is not None
    assert (error.type, error.message, error.trace) == (
        "CompileError",
        "inbox.go:71:17: undefined: x",
        "inbox.go:71",
    )
