"""Finding Delve and the LLDB debug server (docs/specs/runners.md#debug-mode)."""

from pathlib import Path

import pytest

from coding_study.adapters.languages.debug_servers import (
    InstalledDebugServers,
    Machine,
    require_installed,
)
from coding_study.application.ports import DebugServer
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language

XCODE_SERVER = "SharedFrameworks/LLDB.framework/Resources/debugserver"
TOOLS_SERVER = "Library/PrivateFrameworks/LLDB.framework/Resources/debugserver"


def executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n")
    path.chmod(0o755)
    return path


def servers(
    tmp_path: Path,
    environment: dict[str, str] | None = None,
    platform: str = "darwin",
    developer_directory: Path | None = None,
) -> InstalledDebugServers:
    machine = Machine(
        {"PATH": str(tmp_path / "path"), **(environment or {})},
        tmp_path / "home",
        platform,
        lambda: developer_directory,
    )
    return InstalledDebugServers(machine)


def test_delve_on_path_is_used(tmp_path):
    dlv = executable(tmp_path / "path/dlv")
    assert servers(tmp_path).delve().path == dlv


def test_delve_where_go_install_puts_it_with_gobin(tmp_path):
    dlv = executable(tmp_path / "gobin/dlv")
    assert servers(tmp_path, {"GOBIN": str(tmp_path / "gobin")}).delve().path == dlv


def test_delve_in_the_first_gopath_entry(tmp_path):
    dlv = executable(tmp_path / "first/bin/dlv")
    executable(tmp_path / "second/bin/dlv")
    gopath = f"{tmp_path / 'first'}:{tmp_path / 'second'}"
    assert servers(tmp_path, {"GOPATH": gopath}).delve().path == dlv


def test_delve_in_the_default_gopath(tmp_path):
    dlv = executable(tmp_path / "home/go/bin/dlv")
    assert servers(tmp_path).delve().path == dlv


def test_path_comes_before_go_install_directories(tmp_path):
    dlv = executable(tmp_path / "path/dlv")
    executable(tmp_path / "home/go/bin/dlv")
    assert servers(tmp_path).delve().path == dlv


def test_a_file_that_is_not_executable_is_not_delve(tmp_path):
    (tmp_path / "home/go/bin").mkdir(parents=True)
    (tmp_path / "home/go/bin/dlv").write_text("")
    assert servers(tmp_path).delve().path is None


def test_missing_delve_says_how_to_install_the_tested_release(tmp_path):
    assert servers(tmp_path).delve() == DebugServer(
        "dlv", "run `go install github.com/go-delve/delve/cmd/dlv@v1.27.2`"
    )


def test_debugserver_of_the_selected_xcode(tmp_path):
    server = executable(tmp_path / "Xcode.app/Contents" / XCODE_SERVER)
    developer = tmp_path / "Xcode.app/Contents/Developer"
    assert servers(tmp_path, developer_directory=developer).lldb_server().path == server


def test_debugserver_of_the_selected_command_line_tools(tmp_path):
    server = executable(tmp_path / "CommandLineTools" / TOOLS_SERVER)
    developer = tmp_path / "CommandLineTools"
    assert servers(tmp_path, developer_directory=developer).lldb_server().path == server


def test_developer_dir_outranks_xcode_select(tmp_path):
    server = executable(tmp_path / "Beta.app/Contents" / XCODE_SERVER)
    executable(tmp_path / "Xcode.app/Contents" / XCODE_SERVER)
    environment = {"DEVELOPER_DIR": str(tmp_path / "Beta.app/Contents/Developer")}
    found = servers(tmp_path, environment, developer_directory=tmp_path / "Xcode.app/Contents")
    assert found.lldb_server().path == server


def test_lldbs_own_debugserver_setting_comes_first(tmp_path):
    server = executable(tmp_path / "custom/debugserver")
    executable(tmp_path / "Xcode.app/Contents" / XCODE_SERVER)
    environment = {"LLDB_DEBUGSERVER_PATH": str(server)}
    found = servers(tmp_path, environment, developer_directory=tmp_path / "Xcode.app/Contents")
    assert found.lldb_server().path == server


def test_missing_debugserver_says_to_install_the_command_line_tools(tmp_path):
    found = servers(tmp_path, {"DEVELOPER_DIR": str(tmp_path / "none")}).lldb_server()
    assert (found.name, found.install) == ("debugserver", "run `xcode-select --install`")


def test_linux_uses_lldb_server_from_path(tmp_path):
    server = executable(tmp_path / "path/lldb-server")
    assert servers(tmp_path, platform="linux").lldb_server() == DebugServer(
        "lldb-server", "install your distribution's lldb package", server
    )


def test_an_installed_server_is_its_path(tmp_path):
    dlv = executable(tmp_path / "path/dlv")
    assert require_installed(servers(tmp_path).delve(), Language.GO) == dlv


@pytest.mark.parametrize(
    ("server", "language", "message"),
    [
        (
            DebugServer("dlv", "run `go install x@v1`"),
            Language.GO,
            "cannot debug go: dlv was not found; run `go install x@v1` "
            "(https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#go)",
        ),
        (
            DebugServer("debugserver", "run `xcode-select --install`"),
            Language.RUST,
            "cannot debug rust: debugserver was not found; run `xcode-select --install` "
            "(https://github.com/bkuberek/coding-study/blob/main/docs/guides/toolchains.md#rust)",
        ),
    ],
)
def test_a_missing_server_is_an_environment_error_with_the_install_step(server, language, message):
    with pytest.raises(RunnerStartError) as raised:
        require_installed(server, language)
    assert str(raised.value) == message
