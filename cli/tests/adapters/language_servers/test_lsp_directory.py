import json
import os
import re
from collections.abc import Mapping, Sequence
from importlib import resources
from pathlib import Path

import pytest

from coding_study.adapters.language_servers.lsp_directory import (
    MANIFEST_FILES,
    MANIFEST_PACKAGE,
    LspDirectory,
)
from coding_study.application.ports import (
    FileMissing,
    NotInstalled,
    ProbeResult,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    LANGUAGE_SERVERS,
    LSP_INSTALL_COMMAND,
    TYPESCRIPT_LANGUAGE_SERVER,
)

TYPESCRIPT = TYPESCRIPT_LANGUAGE_SERVER
PACKAGE_JSON, LOCK_FILE = MANIFEST_FILES
PNPM_SUCCEEDED = ProbeResult(0, "")


class RecordingTools:
    """Answers a version command from a table; records every command it was asked to run."""

    def __init__(self, answers: Mapping[str, ProbeResult | None] | None = None) -> None:
        self.answers = dict(answers or {})
        self.ran: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> ProbeResult | None:
        self.ran.append(tuple(command))
        return self.answers.get(command[1], ProbeResult(0, ""))


class RecordingCommands:
    def __init__(self, result: ProbeResult | None = PNPM_SUCCEEDED) -> None:
        self.result = result
        self.ran: list[tuple[tuple[str, ...], Path]] = []

    def run(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None = None
    ) -> ProbeResult | None:
        self.ran.append((tuple(command), cwd))
        return self.result


def shipped(name: str) -> bytes:
    return (resources.files(MANIFEST_PACKAGE) / name).read_bytes()


def directory(workspace: Path, tools=None, commands=None) -> LspDirectory:
    return LspDirectory(workspace, tools or RecordingTools(), commands or RecordingCommands())


def install_server(workspace: Path, script: str) -> Path:
    path = workspace / ".cs" / "lsp" / script
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("// the server\n")
    return path


def test_a_server_whose_script_is_missing_is_not_installed(tmp_path):
    assert directory(tmp_path).probe(BASEDPYRIGHT) == NotInstalled()


def test_a_missing_server_runs_nothing(tmp_path):
    tools = RecordingTools()
    directory(tmp_path, tools).probe(BASEDPYRIGHT)
    assert tools.ran == []


def test_an_installed_server_prints_its_version_through_node(tmp_path):
    script = install_server(tmp_path, BASEDPYRIGHT.version_script)
    install_server(tmp_path, BASEDPYRIGHT.script)
    tools = RecordingTools({str(script): ProbeResult(0, "basedpyright 1.40.2\n")})
    found = directory(tmp_path, tools).probe(BASEDPYRIGHT)
    assert (found, tools.ran) == (
        VersionPrinted("basedpyright 1.40.2\n"),
        [("node", str(script), "--version")],
    )


def test_a_version_command_that_exits_nonzero_gives_its_first_line(tmp_path):
    script = install_server(tmp_path, BASEDPYRIGHT.version_script)
    install_server(tmp_path, BASEDPYRIGHT.script)
    output = "\nError: Cannot find module 'x'\n    at Module._resolve\n"
    tools = RecordingTools({str(script): ProbeResult(1, output)})
    found = directory(tmp_path, tools).probe(BASEDPYRIGHT)
    assert found == VersionFailed("Error: Cannot find module 'x'")


def test_a_silent_failure_names_the_exit_code(tmp_path):
    script = install_server(tmp_path, BASEDPYRIGHT.version_script)
    install_server(tmp_path, BASEDPYRIGHT.script)
    tools = RecordingTools({str(script): ProbeResult(3, "")})
    assert directory(tmp_path, tools).probe(BASEDPYRIGHT) == VersionFailed("exited with 3")


def test_a_missing_node_fails_the_version_command(tmp_path):
    script = install_server(tmp_path, BASEDPYRIGHT.version_script)
    install_server(tmp_path, BASEDPYRIGHT.script)
    tools = RecordingTools({str(script): None})
    assert directory(tmp_path, tools).probe(BASEDPYRIGHT) == VersionFailed("node not found on PATH")


def test_typescript_without_the_workspaces_tsserver_is_missing_a_file(tmp_path):
    install_server(tmp_path, TYPESCRIPT.version_script)
    found = directory(tmp_path).probe(TYPESCRIPT)
    assert found == FileMissing("typescript/node_modules/typescript/lib/tsserver.js")


def test_typescript_with_the_workspaces_tsserver_prints_its_version(tmp_path):
    script = install_server(tmp_path, TYPESCRIPT.version_script)
    tsserver = tmp_path / "typescript/node_modules/typescript/lib/tsserver.js"
    tsserver.parent.mkdir(parents=True)
    tsserver.write_text("")
    tools = RecordingTools({str(script): ProbeResult(0, "6.0.3\n")})
    assert directory(tmp_path, tools).probe(TYPESCRIPT) == VersionPrinted("6.0.3\n")


def test_the_install_copies_the_shipped_manifest_into_the_lsp_directory(tmp_path):
    directory(tmp_path).install()
    lsp = tmp_path / ".cs" / "lsp"
    assert [(lsp / name).read_bytes() for name in MANIFEST_FILES] == [
        shipped(name) for name in MANIFEST_FILES
    ]


def test_the_install_runs_the_frozen_install_in_the_lsp_directory(tmp_path):
    commands = RecordingCommands()
    directory(tmp_path, commands=commands).install()
    assert commands.ran == [(LSP_INSTALL_COMMAND, tmp_path / ".cs" / "lsp")]


def test_the_install_returns_the_result_of_pnpm(tmp_path):
    commands = RecordingCommands(ProbeResult(1, "ERR_PNPM_FETCH_404\n"))
    assert directory(tmp_path, commands=commands).install() == ProbeResult(
        1, "ERR_PNPM_FETCH_404\n"
    )


def test_the_install_without_pnpm_returns_none(tmp_path):
    assert directory(tmp_path, commands=RecordingCommands(None)).install() is None


def test_the_install_rewrites_a_manifest_that_differs(tmp_path):
    lsp = tmp_path / ".cs" / "lsp"
    lsp.mkdir(parents=True)
    (lsp / PACKAGE_JSON).write_text('{"dependencies": {"basedpyright": "1.39.0"}}\n')
    directory(tmp_path).install()
    assert (lsp / PACKAGE_JSON).read_bytes() == shipped(PACKAGE_JSON)


def test_the_install_leaves_a_manifest_that_matches_untouched(tmp_path):
    lsp = tmp_path / ".cs" / "lsp"
    lsp.mkdir(parents=True)
    for name in MANIFEST_FILES:
        (lsp / name).write_bytes(shipped(name))
        os.utime(lsp / name, ns=(1_000_000_000, 1_000_000_000))
    directory(tmp_path).install()
    assert [(lsp / name).stat().st_mtime_ns for name in MANIFEST_FILES] == [1_000_000_000] * 2


def test_the_install_runs_pnpm_even_when_the_manifest_matches(tmp_path):
    lsp = tmp_path / ".cs" / "lsp"
    lsp.mkdir(parents=True)
    for name in MANIFEST_FILES:
        (lsp / name).write_bytes(shipped(name))
    commands = RecordingCommands()
    directory(tmp_path, commands=commands).install()
    assert len(commands.ran) == 1


def test_the_install_keeps_the_node_modules_of_an_earlier_install(tmp_path):
    kept = tmp_path / ".cs" / "lsp" / "node_modules" / "basedpyright" / "index.js"
    kept.parent.mkdir(parents=True)
    kept.write_text("// kept\n")
    directory(tmp_path).install()
    assert kept.read_text() == "// kept\n"


class TestShippedManifest:
    """The package data is the contract of `.cs/lsp/`: exact versions and integrity hashes."""

    def test_it_pins_exactly_the_versions_of_the_catalog(self):
        dependencies = json.loads(shipped(PACKAGE_JSON))["dependencies"]
        assert dependencies == {server.name: server.version for server in LANGUAGE_SERVERS}

    @pytest.mark.parametrize("server", list(LANGUAGE_SERVERS), ids=lambda s: s.name)
    def test_the_lock_names_each_server_with_an_integrity_hash(self, server):
        lock = shipped(LOCK_FILE).decode()
        package = re.escape(f"{server.name}@{server.version}")
        assert re.search(rf"{package}:\n\s+resolution: \{{integrity: sha512-", lock)

    def test_every_package_in_the_lock_has_an_integrity_hash(self):
        lock = shipped(LOCK_FILE).decode()
        packages = lock.split("\npackages:\n")[1].split("\nsnapshots:\n")[0]
        entries = re.findall(r"^  \S+@\S+:\n(.*?)(?=\n\n|\Z)", packages, flags=re.M | re.S)
        assert entries
        assert all("integrity: sha512-" in entry for entry in entries)

    def test_it_asks_for_no_install_script_to_run(self):
        document = json.loads(shipped(PACKAGE_JSON))
        assert not {"scripts", "postinstall", "preinstall"} & document.keys()

    def test_it_names_the_node_it_needs(self):
        assert json.loads(shipped(PACKAGE_JSON))["engines"] == {"node": ">=24"}
