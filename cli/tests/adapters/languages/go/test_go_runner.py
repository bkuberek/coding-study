"""`GoRunner.prepare` with a fake `go`: generation, the two-pass rule and the private binary."""

import os
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.adapters import workspace_setup
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go.build_files import (
    REGISTRATION_FILE,
    VENDORED_MODULES,
    vendored_path,
)
from coding_study.adapters.languages.go.runner import COLD_NOTICE, DEBUG_COLD_NOTICE, GoRunner
from coding_study.adapters.languages.go.toolchain import GoOutcome
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.adapters.workspace_setup import TEMPLATE_DIRECTORY
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    Prepared,
    PrepareResult,
    References,
    ReferenceSource,
    UserCode,
)
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import ContentError, RunnerStartError
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.runs import RunRequest
from tests.fakes import DELVE, FakeDebugServers
from tests.helpers import FAKE_RUNNER_PROGRAM, REPOSITORY_ROOT
from tests.stub_contract import STUB_CASES

TEMPLATE = Path(workspace_setup.__file__).parent / TEMPLATE_DIRECTORY
TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
LRU_CACHE = next(case.meta for case in STUB_CASES if case.name == "lru-cache")
SOLUTION = "package two_sum\n\nfunc twoSum(nums []int, target int) []int { return nil }\n"


def build_output(path: str, message: str) -> str:
    output = f"{path}: {message}\\n"
    return f'{{"Action":"build-output","Output":"{output}"}}\n{{"Action":"build-fail"}}\n'


@dataclass
class FakeGo:
    """Answers each `go build` with the next outcome; a success writes the `-o` binary, which
    holds `program`."""

    outcomes: list[GoOutcome] = field(default_factory=list[GoOutcome])
    program: str = "binary"
    builds: list[tuple[list[str], Path, dict[str, str]]] = field(
        default_factory=list[tuple[list[str], Path, dict[str, str]]]
    )

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> GoOutcome:
        self.builds.append((list(arguments), cwd, dict(environment)))
        outcome = self.outcomes.pop(0) if self.outcomes else GoOutcome(0, "", "")
        if outcome.exit_code == 0:
            binary = Path(arguments[arguments.index("-o") + 1])
            binary.parent.mkdir(parents=True, exist_ok=True)
            binary.write_text(self.program)
            binary.chmod(0o755)
        return outcome


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    (root / "go/practice/two_sum").mkdir(parents=True)
    (root / "go/go.mod").write_text("module workspace\n\ngo 1.24\n")
    (root / "go/practice/two_sum/two_sum.go").write_text(SOLUTION)
    (root / ".cs/runtime/runners/go").mkdir(parents=True)
    return root


def runner(root: Path, go: FakeGo, debug_servers: FakeDebugServers | None = None) -> GoRunner:
    context = LanguageContext(root, root / ".cs/runtime/runners")
    return GoRunner(context, go, debug_servers or FakeDebugServers())


def prepared(result: PrepareResult) -> Prepared:
    assert isinstance(result, Prepared), result
    return result


def prepare_user(root: Path, go: FakeGo, meta: ProblemMeta = TWO_SUM) -> PrepareResult:
    return runner(root, go).prepare(UserCode(meta), lambda _: None)


def reference(root: Path, approach: str = "hash-map", text: str = SOLUTION) -> ReferenceSource:
    path = root.parent / "content" / f"{approach}.go"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return ReferenceSource(approach, path)


def test_builds_the_user_package_through_an_overlay(workspace):
    go = FakeGo()
    prepare_user(workspace, go)
    arguments, cwd, environment = go.builds[0]
    build = workspace / ".cs/build/go"
    assert (cwd, environment) == (build, {"GOWORK": str(build / "go.work")})
    assert arguments == [
        "-json",
        f"-overlay={build / 'gen/two_sum/overlay.json'}",
        "-o",
        str(build / "bin/test/two_sum"),
        "./cmd/test/two_sum",
    ]
    assert (
        str(workspace / "go/practice/two_sum" / REGISTRATION_FILE)
        in (build / "gen/two_sum/overlay.json").read_text()
    )


def test_the_build_workspace_joins_the_practice_module_and_the_runner_runtime(workspace):
    prepare_user(workspace, FakeGo())
    work = (workspace / ".cs/build/go/go.work").read_text()
    assert "\t../../../go\n" in work
    assert "replace cstudy => ../../runtime/runners/go\n" in work


def test_the_build_requires_the_vendored_modules_from_the_runner_runtime(workspace):
    prepare_user(workspace, FakeGo())
    module = (workspace / ".cs/build/go/go.mod").read_text()
    work = (workspace / ".cs/build/go/go.work").read_text()
    assert "\tgithub.com/shopspring/decimal v1.5.0\n" in module
    assert (
        "replace github.com/shopspring/decimal => "
        "../../runtime/runners/go/third_party/github.com/shopspring/decimal\n"
    ) in work


def test_the_vendored_versions_match_the_runner_and_practice_modules():
    runner_module = (REPOSITORY_ROOT / "runners/go/go.mod").read_text()
    practice_module = (TEMPLATE / "go/go.mod").read_text()
    for module, version in VENDORED_MODULES.items():
        assert f"require {module} {version}\n" in runner_module
        assert f"\t{module} {version}\n" in practice_module
        assert f"\t{module} => ../.cs/runtime/runners/go/{vendored_path(module)}\n" in (
            practice_module
        )
        assert (REPOSITORY_ROOT / "runners/go" / vendored_path(module) / "go.mod").is_file()


def test_a_class_kind_registers_its_constructor(workspace):
    (workspace / "go/practice/lru_cache").mkdir()
    prepare_user(workspace, FakeGo(), LRU_CACHE)
    registration = workspace / ".cs/build/go/gen/lru_cache/user_targets.go"
    assert '"NewLRUCache": NewLRUCache,' in registration.read_text()


def test_launches_a_private_copy_of_the_binary(workspace):
    launch = prepared(prepare_user(workspace, FakeGo())).launch
    copy = Path(launch.command[0])
    assert copy.parent.parent == workspace / ".cs/build/go/run"
    assert copy.parent.name.startswith(f"{os.getpid()}-")
    assert (copy.name, copy.read_text()) == ("two_sum", "binary")


def test_the_private_copy_lies_in_the_launch_scratch_directory(workspace):
    launch = prepared(prepare_user(workspace, FakeGo())).launch
    assert Path(launch.command[0]).parent == launch.scratch


def test_no_private_copy_remains_after_the_run(workspace, tmp_path):
    launch = prepared(prepare_user(workspace, FakeGo(program=FAKE_RUNNER_PROGRAM))).launch
    SubprocessRunner(tmp_path / "runs").run(launch, RunRequest(()))
    assert list((workspace / ".cs/build/go/run").iterdir()) == []


def test_removes_the_copies_of_processes_that_ended(workspace):
    stale = workspace / ".cs/build/go/run/999999999-abc/test_two_sum"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    prepare_user(workspace, FakeGo())
    assert not stale.parent.exists()


def test_keeps_the_copies_of_processes_that_still_run(workspace):
    running = workspace / f".cs/build/go/run/{os.getpid()}-abc/test_two_sum"
    running.parent.mkdir(parents=True)
    running.write_text("in use")
    prepare_user(workspace, FakeGo())
    assert running.read_text() == "in use"


def test_a_symbol_missing_from_the_package_is_built_again_without_it(workspace):
    registration = "../../../.cs/build/go/gen/two_sum/user_targets.go:6:12"
    missing = build_output(registration, "undefined: twoSum")
    go = FakeGo([GoOutcome(1, missing, "")])
    prepared(prepare_user(workspace, go))
    build = workspace / ".cs/build/go"
    assert len(go.builds) == 2
    assert '"twoSum"' not in (build / "gen/two_sum/user_targets.go").read_text()
    main = (build / "cmd/test/two_sum/main.go").read_text()
    assert '"user": {"twoSum": "undefined: twoSum"}' in main


def test_errors_in_the_user_file_are_a_build_failure_with_workspace_paths(workspace):
    error = build_output("../../../go/practice/two_sum/two_sum.go:3:8", "undefined: x")
    result = prepare_user(workspace, FakeGo([GoOutcome(1, error, "")]))
    assert result == BuildFailed(("go/practice/two_sum/two_sum.go:3:8: undefined: x",))


def test_errors_in_a_reference_fail_verify_like_user_code(workspace):
    error = build_output("ref/two_sum/hash_map/hash_map.go:1:1", "expected 'package'")
    go = FakeGo([GoOutcome(1, error, "")])
    scope = References(TWO_SUM, (reference(workspace),))
    result = runner(workspace, go).prepare(scope, lambda _: None)
    assert result == BuildFailed(
        (".cs/build/go/ref/two_sum/hash_map/hash_map.go:1:1: expected 'package'",)
    )


def test_errors_in_a_reference_are_content_errors_in_a_bench(workspace):
    error = build_output("ref/two_sum/hash_map/hash_map.go:1:1", "expected 'package'")
    scope = BenchCode(TWO_SUM, (reference(workspace),))
    with pytest.raises(ContentError, match=r"hash_map\.go"):
        runner(workspace, FakeGo([GoOutcome(1, error, "")])).prepare(scope, lambda _: None)


def test_references_are_copied_unchanged_into_their_own_package(workspace):
    source = reference(workspace, "brute-force")
    runner(workspace, FakeGo()).prepare(References(TWO_SUM, (source,)), lambda _: None)
    package = workspace / ".cs/build/go/ref/two_sum/brute_force"
    assert (package / "brute_force.go").read_text() == SOLUTION
    main = (workspace / ".cs/build/go/cmd/verify/two_sum/main.go").read_text()
    assert '"ref/brute-force": t0.CsTargets,' in main


def test_a_failure_without_diagnostics_is_an_environment_error(workspace):
    go = FakeGo([GoOutcome(1, "", "go: go.mod requires go >= 1.24\n")])
    with pytest.raises(RunnerStartError, match=r"go\.mod requires go"):
        prepare_user(workspace, go)


def test_a_missing_go_module_is_an_environment_error(workspace):
    (workspace / "go/go.mod").unlink()
    with pytest.raises(RunnerStartError, match=r"go/go\.mod is missing"):
        prepare_user(workspace, FakeGo())


def test_says_once_that_the_first_build_compiles_the_runner(workspace):
    notices: list[str] = []
    for _ in range(2):
        runner(workspace, FakeGo()).prepare(UserCode(TWO_SUM), notices.append)
    assert notices == [COLD_NOTICE]


SESSION = DebugSession(Language.GO, 2345)


def prepare_debug(
    root: Path,
    go: FakeGo,
    debug_servers: FakeDebugServers | None = None,
    notices: list[str] | None = None,
) -> PrepareResult:
    debugging = runner(root, go, debug_servers or FakeDebugServers())
    notify = (notices if notices is not None else []).append
    return debugging.prepare(UserCode(TWO_SUM, debug=SESSION), notify)


def test_delve_starts_the_runner_headless_on_the_sessions_port(workspace):
    launch = prepared(prepare_debug(workspace, FakeGo())).launch
    assert launch.scratch is not None
    assert launch.command == (
        "/go/bin/dlv",
        "exec",
        "--headless",
        "--listen=127.0.0.1:2345",
        "--api-version=2",
        str(launch.scratch / "two_sum"),
        "--",
    )


def test_the_debug_binary_is_built_without_optimizations_or_inlining(workspace):
    go = FakeGo()
    prepare_debug(workspace, go)
    arguments = go.builds[0][0]
    assert "-gcflags=all=-N -l" in arguments
    assert arguments[arguments.index("-o") + 1] == str(workspace / ".cs/build/go/bin/debug/two_sum")


def test_the_launch_is_ready_when_delve_says_it_listens(workspace):
    debug = prepared(prepare_debug(workspace, FakeGo())).launch.debug
    assert debug is not None
    assert (debug.session, debug.ready_marker) == (SESSION, "API server listening at:")


def test_a_missing_delve_is_an_environment_error_before_building(workspace):
    go = FakeGo()
    missing = FakeDebugServers(delve_server=replace(DELVE, path=None))
    with pytest.raises(RunnerStartError, match="cannot debug go: dlv was not found; run `go"):
        prepare_debug(workspace, go, missing)
    assert go.builds == []


def test_a_port_in_use_is_an_environment_error_before_building(workspace):
    go = FakeGo()
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        busy = DebugSession(Language.GO, taken.getsockname()[1])
        debugging = runner(workspace, go, FakeDebugServers())
        with pytest.raises(RunnerStartError, match="already in use"):
            debugging.prepare(UserCode(TWO_SUM, debug=busy), lambda _: None)
    assert go.builds == []


def test_a_compile_error_while_debugging_is_a_build_failure(workspace):
    error = build_output("../../../go/practice/two_sum/two_sum.go:3:8", "undefined: x")
    go = FakeGo([GoOutcome(1, error, "")])
    assert isinstance(prepare_debug(workspace, go), BuildFailed)


def test_says_once_that_the_first_debug_build_compiles_the_standard_library(workspace):
    notices: list[str] = []
    prepare_user(workspace, FakeGo())
    for _ in range(2):
        prepare_debug(workspace, FakeGo(), notices=notices)
    assert notices == [DEBUG_COLD_NOTICE]
