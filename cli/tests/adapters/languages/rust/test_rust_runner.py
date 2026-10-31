"""`RustRunner.prepare` with a fake `cargo`: generation, the two-pass rule, the pinned build and
the private binary. Failures replay Cargo output recorded from real builds (recorded/)."""

import json
import os
import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.rust.runner import COLD_NOTICE, DEBUG_COLD_NOTICE, RustRunner
from coding_study.adapters.languages.rust.toolchain import CargoOutcome
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.ports import (
    BenchCode,
    BuildFailed,
    DebugServer,
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
from tests.fakes import DEBUGSERVER, FakeDebugServers
from tests.helpers import FAKE_RUNNER_PROGRAM
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
LRU_CACHE = next(case.meta for case in STUB_CASES if case.name == "lru-cache")
SOLUTION = "pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {\n    vec![]\n}\n"
HOST = "aarch64-apple-darwin"
RECORDED = Path(__file__).parent / "recorded"


def recorded(name: str, root: Path) -> CargoOutcome:
    stdout = (RECORDED / f"{name}.jsonl").read_text().replace("{root}", str(root))
    return CargoOutcome(101, stdout, "error: could not compile `test_two_sum`\n")


@dataclass
class FakeCargo:
    """Answers each build with the next outcome; a success reports and writes the binary of the
    package named after `-p`, which holds `program`."""

    outcomes: list[CargoOutcome] = field(default_factory=list[CargoOutcome])
    program: str = "binary"
    builds: list[tuple[list[str], Path, dict[str, str]]] = field(
        default_factory=list[tuple[list[str], Path, dict[str, str]]]
    )
    hosts: int = 0

    def build(
        self, arguments: Sequence[str], cwd: Path, environment: Mapping[str, str]
    ) -> CargoOutcome:
        self.builds.append((list(arguments), cwd, dict(environment)))
        outcome = self.outcomes.pop(0) if self.outcomes else CargoOutcome(0, "", "")
        if outcome.exit_code != 0:
            return outcome
        package = arguments[arguments.index("-p") + 1]
        profile = "debug" if "--profile" in arguments else "release"
        binary = Path(environment["CARGO_TARGET_DIR"]) / HOST / profile / package
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text(self.program)
        binary.chmod(0o755)
        artifact = {"reason": "compiler-artifact", "target": {"name": package}}
        stdout = json.dumps({**artifact, "executable": str(binary)}) + "\n"
        return CargoOutcome(0, stdout, "")

    def host(self, cwd: Path) -> str:
        self.hosts += 1
        return HOST

    def release(self, cwd: Path) -> str:
        return "1.92.0"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = (tmp_path / "ws").resolve()
    (root / "rust/practice").mkdir(parents=True)
    (root / "rust/practice/two_sum.rs").write_text(SOLUTION)
    (root / ".cs/runtime/runners/rust").mkdir(parents=True)
    return root


def runner(
    root: Path, cargo: FakeCargo, debug_servers: FakeDebugServers | None = None
) -> RustRunner:
    context = LanguageContext(root, root / ".cs/runtime/runners")
    return RustRunner(context, cargo, debug_servers or FakeDebugServers())


def prepared(result: PrepareResult) -> Prepared:
    assert isinstance(result, Prepared), result
    return result


def prepare_user(root: Path, cargo: FakeCargo, meta: ProblemMeta = TWO_SUM) -> PrepareResult:
    return runner(root, cargo).prepare(UserCode(meta), lambda _: None)


def reference(root: Path, approach: str = "hash-map", text: str = SOLUTION) -> ReferenceSource:
    path = root.parent / "content" / f"{approach}.rs"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return ReferenceSource(approach, path)


def bridge(root: Path, scope: str = "test", snake: str = "two_sum") -> str:
    return (root / f".cs/build/rust/{scope}/{snake}/main.rs").read_text()


def test_builds_the_problems_harness_package_offline_for_the_host(workspace):
    cargo = FakeCargo()
    prepare_user(workspace, cargo)
    arguments, cwd, environment = cargo.builds[0]
    build = workspace / ".cs/build/rust"
    assert (cwd, environment) == (build, {"CARGO_TARGET_DIR": str(build / "target")})
    assert arguments[:7] == [
        "--offline",
        "--release",
        "--message-format=json",
        "--target",
        HOST,
        "-p",
        "test_two_sum",
    ]
    assert "profile.release.overflow-checks=true" in arguments


def test_crates_resolve_from_the_vendored_directory_of_the_runtime(workspace):
    cargo = FakeCargo()
    prepare_user(workspace, cargo)
    arguments = cargo.builds[0][0]
    vendor = workspace / ".cs/runtime/runners/rust/vendor"
    assert f'source.cstudy-vendor.directory="{vendor}"' in arguments


def test_the_bridge_brings_in_the_users_file_by_its_path(workspace):
    prepare_user(workspace, FakeCargo())
    assert f'#[path = "{workspace}/rust/practice/two_sum.rs"]\nmod user;' in bridge(workspace)


def test_the_workspace_lists_the_package_that_links_the_runtime_crates(workspace):
    prepare_user(workspace, FakeCargo())
    build = workspace / ".cs/build/rust"
    assert '    "test/two_sum",\n' in (build / "Cargo.toml").read_text()
    package = (build / "test/two_sum/Cargo.toml").read_text()
    assert 'cs_runner = { path = "../../../../runtime/runners/rust/cs_runner" }' in package


def test_a_class_kind_constructs_and_dispatches_operations(workspace):
    (workspace / "rust/practice/lru_cache.rs").write_text("")
    prepare_user(workspace, FakeCargo(), LRU_CACHE)
    assert "user::LRUCache::new(arg_capacity)" in bridge(workspace, snake="lru_cache")


def test_launches_a_private_copy_of_the_binary(workspace):
    launch = prepared(prepare_user(workspace, FakeCargo())).launch
    copy = Path(launch.command[0])
    assert copy.parent.parent == workspace / ".cs/build/rust/run"
    assert copy.parent.name.startswith(f"{os.getpid()}-")
    assert (copy.name, copy.read_text()) == ("test_two_sum", "binary")


def test_the_private_copy_lies_in_the_launch_scratch_directory(workspace):
    launch = prepared(prepare_user(workspace, FakeCargo())).launch
    assert Path(launch.command[0]).parent == launch.scratch


def test_no_private_copy_remains_after_the_run(workspace, tmp_path):
    launch = prepared(prepare_user(workspace, FakeCargo(program=FAKE_RUNNER_PROGRAM))).launch
    SubprocessRunner(tmp_path / "runs").run(launch, RunRequest(()))
    assert list((workspace / ".cs/build/rust/run").iterdir()) == []


def test_removes_the_copies_of_processes_that_ended(workspace):
    stale = workspace / ".cs/build/rust/run/999999999-abc/test_two_sum"
    stale.parent.mkdir(parents=True)
    stale.write_text("old")
    prepare_user(workspace, FakeCargo())
    assert not stale.parent.exists()


def test_keeps_the_copies_of_processes_that_still_run(workspace):
    running = workspace / f".cs/build/rust/run/{os.getpid()}-abc/test_two_sum"
    running.parent.mkdir(parents=True)
    running.write_text("in use")
    prepare_user(workspace, FakeCargo())
    assert running.read_text() == "in use"


def test_asks_rustc_for_the_host_once(workspace):
    cargo = FakeCargo()
    for _ in range(2):
        prepare_user(workspace, cargo)
    assert cargo.hosts == 1


def test_unchanged_generated_files_keep_their_timestamps(workspace):
    prepare_user(workspace, FakeCargo())
    main = workspace / ".cs/build/rust/test/two_sum/main.rs"
    os.utime(main, (1, 1))
    prepare_user(workspace, FakeCargo())
    assert main.stat().st_mtime == 1


def test_a_symbol_missing_from_the_file_is_built_again_without_it(workspace):
    cargo = FakeCargo([recorded("misnamed", workspace)])
    prepared(prepare_user(workspace, cargo))
    assert len(cargo.builds) == 2
    text = bridge(workspace)
    assert "fn user_call" not in text
    assert 'error_type: "SymbolNotFound"' in text
    assert "cannot find function `two_sum` in `two_sum.rs`" in text


def test_errors_in_the_users_file_are_a_build_failure_with_workspace_paths(workspace):
    result = prepare_user(workspace, FakeCargo([recorded("user-error", workspace)]))
    assert result == BuildFailed(
        (
            "rust/practice/two_sum.rs:11:5: error[E0425]: cannot find value `nil` in this scope",
            "    not found in this scope",
        )
    )


def reference_error(root: Path) -> CargoOutcome:
    """The recorded user error, as if it were in the copied reference."""
    outcome = recorded("user-error", root)
    copy = root / ".cs/build/rust/ref/two_sum/hash_map.rs"
    stdout = outcome.stdout.replace(str(root / "rust/practice/two_sum.rs"), str(copy))
    return CargoOutcome(101, stdout, "")


def test_errors_in_a_reference_fail_verify_like_user_code(workspace):
    scope = References(TWO_SUM, (reference(workspace),))
    result = runner(workspace, FakeCargo([reference_error(workspace)])).prepare(scope, print)
    assert isinstance(result, BuildFailed)
    assert result.diagnostics[0].startswith(".cs/build/rust/ref/two_sum/hash_map.rs:11:5:")


def test_errors_in_a_reference_are_content_errors_in_a_bench(workspace):
    scope = BenchCode(TWO_SUM, (reference(workspace),))
    with pytest.raises(ContentError, match=r"hash_map\.rs"):
        runner(workspace, FakeCargo([reference_error(workspace)])).prepare(scope, print)


def test_references_are_copied_unchanged_into_the_build(workspace):
    source = reference(workspace, "brute-force")
    runner(workspace, FakeCargo()).prepare(References(TWO_SUM, (source,)), lambda _: None)
    copy = workspace / ".cs/build/rust/ref/two_sum/brute_force.rs"
    assert copy.read_text() == SOLUTION
    assert 'id: "ref/brute-force",' in bridge(workspace, "verify")


def test_a_failure_without_diagnostics_is_an_environment_error(workspace):
    cargo = FakeCargo([CargoOutcome(101, "", "error: failed to load manifest\n")])
    with pytest.raises(RunnerStartError, match="failed to load manifest"):
        prepare_user(workspace, cargo)


def test_says_once_that_the_first_build_compiles_the_runner(workspace):
    notices: list[str] = []
    for _ in range(2):
        runner(workspace, FakeCargo()).prepare(UserCode(TWO_SUM), notices.append)
    assert notices == [COLD_NOTICE]


SESSION = DebugSession(Language.RUST, 12345)
LLDB_SERVER = DebugServer("lldb-server", "install lldb", Path("/usr/bin/lldb-server"))


def prepare_debug(
    root: Path,
    cargo: FakeCargo,
    debug_servers: FakeDebugServers | None = None,
    notices: list[str] | None = None,
) -> PrepareResult:
    debugging = runner(root, cargo, debug_servers or FakeDebugServers())
    notify = (notices if notices is not None else []).append
    return debugging.prepare(UserCode(TWO_SUM, debug=SESSION), notify)


def test_debugserver_starts_the_runner_and_writes_its_port_to_the_ready_file(workspace):
    launch = prepared(prepare_debug(workspace, FakeCargo())).launch
    assert launch.scratch is not None
    ready_file = launch.scratch / "debug-port"
    assert launch.command == (
        "/xcode/debugserver",
        "--named-pipe",
        str(ready_file),
        "127.0.0.1:12345",
        "--",
        str(launch.scratch / "test_two_sum"),
    )
    assert launch.debug is not None
    assert (launch.debug.session, launch.debug.ready_file) == (SESSION, ready_file)


def test_lldb_server_runs_as_a_gdbserver(workspace):
    linux = FakeDebugServers(lldb=LLDB_SERVER)
    command = prepared(prepare_debug(workspace, FakeCargo(), linux)).launch.command
    assert command[:3] == ("/usr/bin/lldb-server", "gdbserver", "--named-pipe")


def test_the_debug_build_uses_the_pinned_dev_profile(workspace):
    cargo = FakeCargo()
    prepare_debug(workspace, cargo)
    arguments = cargo.builds[0][0]
    assert "--release" not in arguments
    assert arguments[arguments.index("--profile") + 1] == "dev"
    assert "profile.dev.opt-level=0" in arguments


def test_a_missing_debug_server_is_an_environment_error_before_building(workspace):
    cargo = FakeCargo()
    missing = FakeDebugServers(lldb=replace(DEBUGSERVER, path=None))
    with pytest.raises(RunnerStartError, match="cannot debug rust: debugserver was not found"):
        prepare_debug(workspace, cargo, missing)
    assert cargo.builds == []


def test_a_port_in_use_is_an_environment_error_before_building(workspace):
    cargo = FakeCargo()
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        busy = DebugSession(Language.RUST, taken.getsockname()[1])
        debugging = runner(workspace, cargo, FakeDebugServers())
        with pytest.raises(RunnerStartError, match="already in use"):
            debugging.prepare(UserCode(TWO_SUM, debug=busy), lambda _: None)
    assert cargo.builds == []


def test_a_compile_error_while_debugging_is_a_build_failure(workspace):
    cargo = FakeCargo([recorded("user-error", workspace)])
    assert isinstance(prepare_debug(workspace, cargo), BuildFailed)


def test_says_once_that_the_first_debug_build_compiles_the_runner(workspace):
    notices: list[str] = []
    prepare_user(workspace, FakeCargo())
    for _ in range(2):
        prepare_debug(workspace, FakeCargo(), notices=notices)
    assert notices == [DEBUG_COLD_NOTICE]
