"""The TypeScript runner under the Node inspector (docs/specs/runners.md#debug-mode)."""

import socket
from pathlib import Path

import pytest
import yaml

from coding_study.adapters.languages.typescript.runner import INSPECTOR_MARKER, TypeScriptRunner
from coding_study.adapters.problem_documents import meta_from_document
from coding_study.application.ports import Prepared, ProbeResult, UserCode
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.stub_contract import SIGNATURES_DIRECTORY

TWO_SUM = meta_from_document(
    yaml.safe_load((SIGNATURES_DIRECTORY / "two-sum.yaml").read_text()), "two-sum.yaml"
)
SESSION = DebugSession(Language.TYPESCRIPT, 9229)


class PassingTypeChecker:
    def check(self, project: Path) -> ProbeResult | None:
        return ProbeResult(0, "")


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "runners" / "typescript").mkdir(parents=True)
    (tmp_path / "runners" / "typescript" / "runner.ts").write_text("")
    workspace = tmp_path / "typescript"
    (workspace / "node_modules").mkdir(parents=True)
    (workspace / "package.json").write_text("{}")
    return tmp_path


def prepare_debug(
    root: Path, session: DebugSession = SESSION, notices: list[str] | None = None
) -> Prepared:
    runner = TypeScriptRunner(root, root / "runners", PassingTypeChecker())
    result = runner.prepare(
        UserCode(TWO_SUM, debug=session), (notices if notices is not None else []).append
    )
    assert isinstance(result, Prepared)
    return result


def test_node_waits_for_the_inspector_client_before_running_the_runner(root):
    script = str(root / "runners" / "typescript" / "runner.ts")
    command = prepare_debug(root).launch.command
    assert command == ("node", "--inspect-wait=127.0.0.1:9229", script)


def test_the_inspector_listens_on_the_sessions_port_and_the_loopback_interface(root):
    command = prepare_debug(root, DebugSession(Language.TYPESCRIPT, 9300)).launch.command
    assert command[1] == "--inspect-wait=127.0.0.1:9300"


def test_the_launch_asks_for_the_marker_node_prints_when_it_listens(root):
    debug = prepare_debug(root).launch.debug
    assert debug is not None
    assert debug.ready_marker == INSPECTOR_MARKER == "Debugger listening on"


def test_the_launch_announces_through_the_notice(root):
    notices: list[str] = []
    debug = prepare_debug(root, notices=notices).launch.debug
    assert debug is not None
    debug.announce("a line")
    assert notices == ["a line"]


def test_the_launch_carries_the_session(root):
    debug = prepare_debug(root).launch.debug
    assert debug is not None
    assert debug.session == SESSION


def test_the_runner_still_starts_in_the_typescript_workspace(root):
    assert prepare_debug(root).launch.cwd == root / "typescript"


def test_the_debug_launch_keeps_the_typescript_hello_timeout(root):
    assert prepare_debug(root).launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.TYPESCRIPT]


def test_a_normal_run_starts_no_inspector(root):
    runner = TypeScriptRunner(root, root / "runners", PassingTypeChecker())
    result = runner.prepare(UserCode(TWO_SUM), lambda _line: None)
    assert isinstance(result, Prepared)
    assert result.launch.debug is None
    assert result.launch.command[1].endswith("runner.ts")


def test_a_port_in_use_is_an_environment_error(root):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        busy = DebugSession(Language.TYPESCRIPT, listener.getsockname()[1])
        with pytest.raises(RunnerStartError, match="--debug-port"):
            prepare_debug(root, busy)
