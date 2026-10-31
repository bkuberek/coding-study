"""`GoRunner.prepare_project` with a fake `go`: the `go.work` of each project root, the grading
binary built through an overlay on the entry's package, the suite binary and its environment
(docs/specs/runners.md#go-project-jobs)."""

import json
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go.build_files import COLD_NOTICE
from coding_study.adapters.languages.go.runner import GoRunner
from coding_study.adapters.languages.go.toolchain import GO_ENVIRONMENT, GoOutcome
from coding_study.application.ports import (
    ProjectGrading,
    ProjectSuite,
    RunnerLaunch,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.project import Project
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.fakes import DELVE, FakeDebugServers
from tests.project_builders import project_meta

META = project_meta(language=Language.GO)
SLUG = META.slug
MODULE = f"module {SLUG}\n\ngo 1.24\n"
ENTRY = "package bank\n\ntype Bank struct{}\n\nfunc NewBank() *Bank { return &Bank{} }\n"


@dataclass
class FakeGo:
    """Answers each `go build` with the next outcome; a success writes the `-o` binary."""

    outcomes: list[GoOutcome] = field(default_factory=list[GoOutcome])
    builds: list[tuple[list[str], Path, dict[str, str]]] = field(
        default_factory=list[tuple[list[str], Path, dict[str, str]]]
    )

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> GoOutcome:
        self.builds.append((list(arguments), cwd, dict(environment)))
        outcome = self.outcomes.pop(0) if self.outcomes else GoOutcome(0, "", "")
        if outcome.exit_code == 0 and "-o" in arguments:
            binary = Path(arguments[arguments.index("-o") + 1])
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text("binary")
        return outcome


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    folder = root / "projects" / SLUG
    folder.mkdir(parents=True)
    (folder / "go.mod").write_text(MODULE)
    (folder / "bank.go").write_text(ENTRY)
    (root / ".cs/runtime/runners/go").mkdir(parents=True)
    return root


def runner(root: Path, go: FakeGo, debug_servers: FakeDebugServers | None = None) -> GoRunner:
    context = LanguageContext(root, root / ".cs/runtime/runners")
    return GoRunner(context, go, debug_servers or FakeDebugServers())


def folder(root: Path) -> Path:
    return root / "projects" / SLUG


def grade(root: Path, go: FakeGo, level: int = 1, notes: list[str] | None = None) -> RunnerLaunch:
    scope = ProjectGrading(folder(root), META, level)
    return runner(root, go).prepare_project(scope, (notes if notes is not None else []).append)


def build_directory(root: Path) -> Path:
    return root / ".cs/build/go"


def project_directory(root: Path) -> Path:
    return build_directory(root) / "project" / "projects" / SLUG


def work_file(root: Path) -> Path:
    return project_directory(root) / "go.work"


def used(root: Path) -> list[Path]:
    """The directories the root's `go.work` uses, resolved."""
    text = work_file(root).read_text()
    block = text.split("use (\n", 1)[1].split("\n)", 1)[0]
    return [(work_file(root).parent / line.strip()).resolve() for line in block.splitlines()]


def replaced(root: Path) -> dict[str, Path]:
    text = work_file(root).read_text()
    pairs = (line.removeprefix("replace ").split(" => ") for line in text.splitlines())
    return {
        module: (work_file(root).parent / target).resolve()
        for module, target in (pair for pair in pairs if len(pair) == 2)
    }


def diagnostic_output(path: str, message: str) -> str:
    output = json.dumps(f"{path}: {message}\n")
    return f'{{"Action":"build-output","Output":{output}}}\n{{"Action":"build-fail"}}\n'


# grading


def test_the_project_root_gets_a_go_work_with_the_build_module_and_the_folder(workspace):
    grade(workspace, FakeGo())
    assert used(workspace) == [build_directory(workspace).resolve(), folder(workspace).resolve()]


def test_the_go_work_replaces_the_runner_and_the_vendored_modules_with_the_runtime(workspace):
    grade(workspace, FakeGo())
    runtime = (workspace / ".cs/runtime/runners/go").resolve()
    assert replaced(workspace) == {
        "cstudy": runtime,
        "github.com/shopspring/decimal": runtime / "third_party/github.com/shopspring/decimal",
    }


def test_the_go_work_follows_a_newer_go_line_of_the_folder(workspace):
    (folder(workspace) / "go.mod").write_text(f"module {SLUG}\n\ngo 1.26\n")
    grade(workspace, FakeGo())
    assert work_file(workspace).read_text().startswith("go 1.26\n")


def test_grading_builds_the_projects_binary_through_an_overlay(workspace):
    go = FakeGo()
    grade(workspace, go)
    arguments, cwd, environment = go.builds[0]
    overlay = project_directory(workspace) / "overlay.json"
    assert (cwd, environment, arguments) == (
        build_directory(workspace),
        {"GOWORK": str(work_file(workspace))},
        [
            "-json",
            f"-overlay={overlay}",
            "-o",
            str(build_directory(workspace) / "bin/project/bank_project_go"),
            "./cmd/project/bank_project_go",
        ],
    )


def test_the_overlay_puts_the_registration_and_thunks_in_the_entry_package(workspace):
    grade(workspace, FakeGo())
    overlay = json.loads((project_directory(workspace) / "overlay.json").read_text())
    entry_directory = folder(workspace)
    assert overlay == {
        "Replace": {
            str(entry_directory / "zz_cs_targets.go"): str(
                project_directory(workspace) / "zz_cs_targets.go"
            ),
            str(entry_directory / "zz_cs_thunks.go"): str(
                project_directory(workspace) / "zz_cs_thunks.go"
            ),
        }
    }


def test_the_registration_names_the_constructor_in_the_entry_package(workspace):
    grade(workspace, FakeGo())
    registration = (project_directory(workspace) / "zz_cs_targets.go").read_text()
    assert "package bank\n" in registration
    assert '"NewBank": NewBank' in registration


def test_the_thunks_cover_the_methods_of_the_graded_levels_only(workspace):
    grade(workspace, FakeGo(), level=1)
    thunks = (project_directory(workspace) / "zz_cs_thunks.go").read_text()
    assert ('"CreateAccount"' in thunks, '"Transfer"' in thunks) == (True, False)


def test_the_main_package_imports_the_module_from_its_go_mod(workspace):
    (folder(workspace) / "go.mod").write_text("module renamed\n\ngo 1.24\n")
    grade(workspace, FakeGo())
    main = (build_directory(workspace) / "cmd/project/bank_project_go/main.go").read_text()
    assert '\tt0 "renamed"\n' in main


def test_an_entry_in_a_directory_is_imported_from_it(workspace):
    meta = replace(META, project=Project("core/bank.go"))
    scope = ProjectGrading(folder(workspace), meta, 1)
    runner(workspace, FakeGo()).prepare_project(scope, [].append)
    main = (build_directory(workspace) / "cmd/project/bank_project_go/main.go").read_text()
    assert f'\tt0 "{SLUG}/core"\n' in main


def test_grading_launches_a_private_copy_in_the_project_root(workspace):
    launch = grade(workspace, FakeGo())
    binary = Path(launch.command[0])
    assert (binary.parent.parent, launch.cwd, launch.scratch, launch.hello_timeout_ms) == (
        build_directory(workspace) / "run",
        folder(workspace),
        binary.parent,
        HELLO_TIMEOUT_MS[Language.GO],
    )


def test_a_project_that_does_not_compile_builds_a_runner_that_reports_the_errors(workspace):
    error = diagnostic_output(f"../../../projects/{SLUG}/bank.go:5:10", "undefined: account")
    go = FakeGo([GoOutcome(1, error, "")])
    grade(workspace, go)
    main = (build_directory(workspace) / "cmd/project/bank_project_go/main.go").read_text()
    assert 'runner.MainBuildFailed("user", "bank.go:5:10: undefined: account", "bank.go:5")' in main
    assert not any(argument.startswith("-overlay") for argument in go.builds[1][0])


def test_a_missing_constructor_is_left_to_the_runner(workspace):
    registration = project_directory(workspace) / "zz_cs_targets.go"
    error = diagnostic_output(f"{registration}:5:2", "undefined: NewBank")
    go = FakeGo([GoOutcome(1, error, "")])
    grade(workspace, go)
    main = (build_directory(workspace) / "cmd/project/bank_project_go/main.go").read_text()
    assert '"user": {"NewBank": "undefined: NewBank"}' in main


def test_a_folder_without_go_mod_cannot_be_graded(workspace):
    (folder(workspace) / "go.mod").unlink()
    with pytest.raises(RunnerStartError, match=f"projects/{SLUG}/go.mod is missing"):
        grade(workspace, FakeGo())


def test_the_first_build_says_it_compiles_the_runner(workspace):
    notes: list[str] = []
    grade(workspace, FakeGo(), notes=notes)
    grade(workspace, FakeGo(), notes=notes)
    assert notes == [COLD_NOTICE]


# suite


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def suite(root: Path, go: FakeGo, debug: DebugSession | None = None) -> RunnerLaunch:
    scope = ProjectSuite(folder(root), debug, META)
    return runner(root, go).prepare_project(scope, [].append)


def test_the_suite_runner_is_built_once_without_a_target(workspace):
    go = FakeGo()
    suite(workspace, go)
    arguments = go.builds[0][0]
    main = (build_directory(workspace) / "cmd/suite/main.go").read_text()
    assert arguments[-3:] == [
        "-o",
        str(build_directory(workspace) / "bin/suite/cs_go_suite"),
        "./cmd/suite",
    ]
    assert "runner.Main(nil, nil, nil)" in main


def test_the_first_suite_also_compiles_the_testing_packages(workspace):
    go = FakeGo()
    suite(workspace, go)
    assert go.builds[1][0] == ["testing", "testing/internal/testdeps"]


def test_the_suite_runs_in_the_root_with_its_go_work_and_this_machines_platform(workspace):
    launch = suite(workspace, FakeGo())
    assert (launch.cwd, launch.environment) == (
        folder(workspace),
        {**GO_ENVIRONMENT, "GOWORK": str(work_file(workspace)), "GOOS": "", "GOARCH": ""},
    )


def test_a_debugged_suite_tells_the_runner_where_delve_listens(workspace):
    session = DebugSession(Language.GO, free_port())
    launch = suite(workspace, FakeGo(), session)
    environment = launch.environment
    assert (
        environment["CSTUDY_GO_DEBUG_LISTEN"],
        environment["CSTUDY_GO_DELVE"],
        environment["CSTUDY_GO_DEBUG_PACKAGE"],
    ) == (session.address, str(DELVE.path), "tests")


def test_a_debugged_suite_waits_for_delves_ready_line(workspace):
    launch = suite(workspace, FakeGo(), DebugSession(Language.GO, free_port()))
    assert launch.debug is not None
    assert launch.debug.ready_marker == "API server listening at:"


def test_a_debugged_suite_needs_delve(workspace):
    servers = FakeDebugServers(delve_server=replace(DELVE, path=None))
    scope = ProjectSuite(folder(workspace), DebugSession(Language.GO, free_port()), META)
    with pytest.raises(RunnerStartError, match="dlv was not found"):
        runner(workspace, FakeGo(), servers).prepare_project(scope, [].append)


def test_nothing_is_written_to_the_project_folder(workspace):
    grade(workspace, FakeGo())
    suite(workspace, FakeGo())
    assert sorted(path.name for path in folder(workspace).iterdir()) == ["bank.go", "go.mod"]


# folders


def test_the_go_runner_checks_the_workspaces_go_folders(workspace):
    (check,) = runner(workspace, FakeGo()).folder_checks()
    assert check.failing == (f"projects/{SLUG} has no go.work",)


def test_the_go_runner_writes_the_missing_go_work_files(workspace):
    assert runner(workspace, FakeGo()).repair_folders() == (f"projects/{SLUG}/go.work",)
