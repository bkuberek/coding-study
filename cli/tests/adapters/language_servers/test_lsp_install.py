"""The real install of `.cs/lsp/` and the servers' real version commands. Needs the network
the first time, for the packages of the pinned lock, and Node 24 and pnpm."""

import shutil

import pytest

from coding_study.adapters.language_servers.lsp_directory import LspDirectory
from coding_study.adapters.subprocess_tool_probe import (
    SubprocessCommandRunner,
    SubprocessToolProbe,
)
from coding_study.application.code_intelligence import ServerStatus, language_server_states
from coding_study.domain.code_intelligence import LANGUAGE_SERVERS, LSP_DIRECTORY

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        shutil.which("node") is None or shutil.which("pnpm") is None,
        reason="node and pnpm are not installed",
    ),
]


@pytest.fixture(scope="module")
def installed(practice_workspace):
    """The practice workspace with `.cs/lsp/` installed from the shipped manifest."""
    directory = LspDirectory(practice_workspace, SubprocessToolProbe(), SubprocessCommandRunner())
    result = directory.install()
    assert result is not None
    assert result.exit_code == 0, result.output
    return directory


def test_the_install_puts_both_servers_in_the_lsp_directory(practice_workspace, installed):
    lsp = practice_workspace / LSP_DIRECTORY
    scripts = [lsp / server.script for server in LANGUAGE_SERVERS]
    assert all(script.is_file() for script in scripts)


@pytest.mark.parametrize("server", LANGUAGE_SERVERS, ids=lambda server: server.name)
def test_each_servers_version_command_prints_the_pinned_version(installed, server):
    states = {state.language: state for state in language_server_states(installed)}
    assert (states[server.language].status, states[server.language].version) == (
        ServerStatus.INSTALLED,
        server.version,
    )


def test_installing_again_changes_nothing_and_succeeds(practice_workspace, installed):
    manifest = [
        practice_workspace / LSP_DIRECTORY / name for name in ("package.json", "pnpm-lock.yaml")
    ]
    before = [path.stat().st_mtime_ns for path in manifest]
    result = installed.install()
    assert (result is not None and result.exit_code, [p.stat().st_mtime_ns for p in manifest]) == (
        0,
        before,
    )
