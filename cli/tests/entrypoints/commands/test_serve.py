"""`cstudy serve` (docs/specs/cli.md#cstudy-serve), with the server loop replaced."""

import signal
import socket
import stat
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from starlette.types import ASGIApp
from typer.testing import CliRunner

from coding_study.adapters.workspace_marker import tool_version
from coding_study.application.ports import WebServerLibraries, WebUiAssets
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import serve
from coding_study.entrypoints.shared import ExitCode
from coding_study.entrypoints.web import app, server
from coding_study.entrypoints.web.context import ServerSettings
from tests.web_server import web_workspace

runner = CliRunner()
URL_PREFIX = "http://127.0.0.1:"


class FakeWebUi:
    def __init__(self, assets: WebUiAssets, libraries: WebServerLibraries) -> None:
        self._assets = assets
        self._libraries = libraries

    def assets(self) -> WebUiAssets:
        return self._assets

    def server_libraries(self) -> WebServerLibraries:
        return self._libraries


class ServerLoop:
    """Stands in for uvicorn: records the app and the socket, runs `during`, then stops the
    way `stop` says, as Ctrl-C (KeyboardInterrupt) or SIGTERM (server.Terminated) do, or
    returns, as a server that failed to start does."""

    def __init__(
        self, stop: type[BaseException] | None, during: Callable[[], None] = lambda: None
    ) -> None:
        self.stop = stop
        self.during = during
        self.apps: list[ASGIApp] = []
        self.addresses: list[tuple[str, int]] = []

    def __call__(self, app: ASGIApp, listener: socket.socket) -> None:
        self.apps.append(app)
        self.addresses.append(listener.getsockname())
        self.during()
        if self.stop is not None:
            raise self.stop

    @property
    def app(self) -> ASGIApp:
        return self.apps[0]

    @property
    def address(self) -> tuple[str, int]:
        return self.addresses[0]


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    root.mkdir()
    environment = web_workspace(root)
    monkeypatch.setattr(serve, "load_environment", lambda *_: environment)
    return root


@pytest.fixture
def opened(monkeypatch) -> list[str]:
    """The URLs handed to the default browser."""
    urls: list[str] = []
    monkeypatch.setattr(serve.webbrowser, "open", lambda url: urls.append(url) or True)
    return urls


def serving(monkeypatch, loop: ServerLoop, *arguments: str):
    monkeypatch.setattr(server, "serve_forever", loop)
    return runner.invoke(cli.app, ["serve", *arguments])


def printed_url(output: str) -> str:
    return next(word for word in output.split() if word.startswith(URL_PREFIX))


def redirect_file(workspace: Path, loop: ServerLoop) -> Path:
    return workspace / ".cs" / "serve" / f"{loop.address[1]}.html"


def test_serve_needs_a_workspace():
    assert runner.invoke(cli.app, ["serve"]).exit_code == ExitCode.USAGE_ERROR


@pytest.mark.parametrize("port", ["65536", "-1", "http"])
def test_a_port_outside_1_to_65535_is_a_usage_error(workspace, port):
    result = runner.invoke(cli.app, ["serve", "--port", port])
    assert result.exit_code == ExitCode.USAGE_ERROR


def test_a_port_in_use_exits_4_naming_it(workspace):
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        result = runner.invoke(cli.app, ["serve", "--port", str(port)])
    assert (result.exit_code, result.stderr) == (
        ExitCode.ENVIRONMENT_ERROR,
        f"error: port {port} on 127.0.0.1 is already in use; choose another with --port\n",
    )


def test_assets_that_do_not_match_their_manifest_exit_4(workspace, monkeypatch):
    web = FakeWebUi(WebUiAssets(0, "missing editor.js"), WebServerLibraries(("starlette 1",)))
    monkeypatch.setattr(serve, "InstalledWebUi", lambda _directory: web)
    result = runner.invoke(cli.app, ["serve"])
    assert (result.exit_code, result.stderr) == (
        ExitCode.ENVIRONMENT_ERROR,
        "error: the page's assets do not match their manifest: missing editor.js; "
        "fix: reinstall cstudy\n",
    )


def test_server_libraries_that_do_not_import_exit_4(workspace, monkeypatch):
    web = FakeWebUi(WebUiAssets(1), WebServerLibraries((), "uvicorn does not import: gone"))
    monkeypatch.setattr(serve, "InstalledWebUi", lambda _directory: web)
    result = runner.invoke(cli.app, ["serve"])
    assert (result.exit_code, result.stderr) == (
        ExitCode.ENVIRONMENT_ERROR,
        "error: the web server libraries are missing: uvicorn does not import: gone; "
        "fix: reinstall cstudy\n",
    )


def test_serve_listens_on_the_loopback_address_only(workspace, monkeypatch):
    loop = ServerLoop(KeyboardInterrupt)
    serving(monkeypatch, loop)
    assert loop.address[0] == "127.0.0.1"


def test_serve_listens_on_the_port_asked_for(workspace, monkeypatch):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    loop = ServerLoop(KeyboardInterrupt)
    serving(monkeypatch, loop, "--port", str(port))
    assert loop.address == ("127.0.0.1", port)


def test_serve_prints_its_version_workspace_and_the_url_with_the_token(workspace, monkeypatch):
    loop = ServerLoop(KeyboardInterrupt)
    lines = serving(monkeypatch, loop).stdout.splitlines()
    assert [line.split("?token=")[0] for line in lines[:2]] == [
        f"cstudy serve {tool_version()} · workspace {workspace}",
        f"open       http://127.0.0.1:{loop.address[1]}/",
    ]


def test_a_workspace_under_home_is_shown_from_home(workspace, monkeypatch):
    monkeypatch.setenv("HOME", str(workspace.parent))
    first = serving(monkeypatch, ServerLoop(KeyboardInterrupt)).stdout.splitlines()[0]
    assert first.endswith(" · workspace ~/ws")


def test_the_printed_token_logs_in_to_the_workspaces_server(workspace, monkeypatch):
    loop = ServerLoop(KeyboardInterrupt)
    url = printed_url(serving(monkeypatch, loop).stdout)
    with TestClient(loop.app, base_url=url.split("/?")[0]) as client:
        client.get(url)
        document = client.get("/api/v1/session").json()
    assert document["workspace"] == str(workspace)


def test_each_start_prints_a_new_token(workspace, monkeypatch):
    first = printed_url(serving(monkeypatch, ServerLoop(KeyboardInterrupt)).stdout)
    second = printed_url(serving(monkeypatch, ServerLoop(KeyboardInterrupt)).stdout)
    assert first.split("token=")[1] != second.split("token=")[1]


def test_ctrl_c_exits_130_saying_how_it_stopped(workspace, monkeypatch):
    result = serving(monkeypatch, ServerLoop(KeyboardInterrupt))
    assert (result.exit_code, result.stdout.splitlines()[-1]) == (
        ExitCode.INTERRUPTED,
        "stop       Ctrl-C",
    )


def test_sigterm_exits_143(workspace, monkeypatch):
    result = serving(monkeypatch, ServerLoop(server.Terminated))
    assert (result.exit_code, result.stdout.splitlines()[-1]) == (143, "stop       SIGTERM")


def test_a_server_that_stops_by_itself_exits_70(workspace, monkeypatch):
    result = serving(monkeypatch, ServerLoop(None))
    assert (result.exit_code, result.stderr) == (
        ExitCode.INTERNAL_ERROR,
        "error: the web server stopped without being asked to\n",
    )


def test_the_stop_signals_are_restored_when_the_server_stops(workspace, monkeypatch):
    before = (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM))
    serving(monkeypatch, ServerLoop(server.Terminated))
    assert (signal.getsignal(signal.SIGINT), signal.getsignal(signal.SIGTERM)) == before


def blocked_signals() -> set[int]:
    return set(signal.pthread_sigmask(signal.SIG_BLOCK, []))


def test_the_stop_signals_wait_blocked_until_uvicorn_takes_them(workspace, monkeypatch):
    blocked: list[set[int]] = []
    serving(monkeypatch, ServerLoop(KeyboardInterrupt, lambda: blocked.append(blocked_signals())))
    assert {signal.SIGINT, signal.SIGTERM} <= blocked[0]


def test_the_stop_signals_are_unblocked_when_the_server_stops(workspace, monkeypatch):
    serving(monkeypatch, ServerLoop(KeyboardInterrupt))
    assert {signal.SIGINT, signal.SIGTERM}.isdisjoint(blocked_signals())


def test_the_socket_is_closed_when_the_server_stops(workspace, monkeypatch):
    bound: list[socket.socket] = []
    bind = server.bind_loopback

    def recorded(port: int) -> socket.socket:
        bound.append(bind(port))
        return bound[0]

    monkeypatch.setattr(server, "bind_loopback", recorded)
    serving(monkeypatch, ServerLoop(KeyboardInterrupt))
    assert bound[0].fileno() == -1


def served_settings(monkeypatch) -> list[ServerSettings]:
    """The settings `cstudy serve` builds its app from."""
    built: list[ServerSettings] = []
    create_app = app.create_app

    def recorded(settings: ServerSettings) -> ASGIApp:
        built.append(settings)
        return create_app(settings)

    monkeypatch.setattr(app, "create_app", recorded)
    return built


def test_children_get_the_content_the_server_was_started_with(workspace, monkeypatch, tmp_path):
    content = tmp_path / "content"
    content.mkdir()
    settings = served_settings(monkeypatch)
    monkeypatch.setattr(server, "serve_forever", ServerLoop(KeyboardInterrupt))
    runner.invoke(cli.app, ["--content", str(content), "serve"])
    assert settings[0].child.content == content


def test_children_get_no_content_when_the_server_was_started_without(workspace, monkeypatch):
    settings = served_settings(monkeypatch)
    serving(monkeypatch, ServerLoop(KeyboardInterrupt))
    assert settings[0].child.content is None


def test_without_open_no_browser_opens(workspace, monkeypatch, opened):
    serving(monkeypatch, ServerLoop(KeyboardInterrupt))
    assert opened == []


def test_open_opens_the_redirect_file_in_the_browser(workspace, monkeypatch, opened):
    loop = ServerLoop(KeyboardInterrupt)
    serving(monkeypatch, loop, "--open")
    assert opened == [redirect_file(workspace, loop).as_uri()]


def test_the_redirect_file_sends_the_browser_to_the_url(workspace, monkeypatch, opened):
    contents: list[str] = []
    loop = ServerLoop(KeyboardInterrupt)
    loop.during = lambda: contents.append(redirect_file(workspace, loop).read_text())
    url = printed_url(serving(monkeypatch, loop, "--open").stdout)
    assert f'<meta http-equiv="refresh" content="0; url={url}">' in contents[0]


def test_the_redirect_file_is_readable_by_its_owner_only(workspace, monkeypatch, opened):
    modes: list[int] = []
    loop = ServerLoop(KeyboardInterrupt)
    loop.during = lambda: modes.append(stat.S_IMODE(redirect_file(workspace, loop).stat().st_mode))
    serving(monkeypatch, loop, "--open")
    assert modes == [0o600]


def test_the_redirect_file_is_removed_when_the_server_stops(workspace, monkeypatch, opened):
    loop = ServerLoop(server.Terminated)
    serving(monkeypatch, loop, "--open")
    assert not redirect_file(workspace, loop).exists()


def test_importing_the_cli_loads_no_web_server():
    """NFR-2: only `cstudy serve` pays for Starlette and uvicorn."""
    script = (
        "import sys, coding_study.entrypoints.cli; "
        "print(sorted({m.split('.')[0] for m in sys.modules} & {'starlette', 'uvicorn'}))"
    )
    finished = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert finished.stdout == "[]\n"
