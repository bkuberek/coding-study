import hashlib
import io
import json
import os
import platform
import re
import sys
import tarfile
import tomllib
import zipfile
from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date
from importlib import resources
from pathlib import Path

import pytest

from coding_study.adapters.language_servers.lsp_directory import (
    MANIFEST_FILES,
    MANIFEST_PACKAGE,
    LspDirectory,
)
from coding_study.adapters.workspace_marker import read_marker
from coding_study.application.ports import (
    Fetched,
    FileMissing,
    NewestBuild,
    NoBuild,
    NotInstalled,
    ProbeResult,
    Unpacked,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import (
    BASEDPYRIGHT,
    GOPLS,
    JDTLS,
    KOTLIN_LSP,
    KOTLIN_LSP_LICENSE,
    KOTLIN_LSP_LINUX,
    LANGUAGE_SERVERS,
    LSP_INSTALL_COMMAND,
    RUST_ANALYZER,
    TYPESCRIPT_LANGUAGE_SERVER,
    Archive,
    LanguageServer,
    machine_of,
)
from coding_study.domain.problem import Language

TYPESCRIPT = TYPESCRIPT_LANGUAGE_SERVER
NPM_SERVERS = [server for server in LANGUAGE_SERVERS if server.version_script is not None]
CORE_PLUGIN = "plugins/org.eclipse.jdt.ls.core_1.63.0.202610191322.jar"
PACKAGE_JSON, LOCK_FILE = MANIFEST_FILES
PNPM_SUCCEEDED = ProbeResult(0, "")
TODAY = date(2026, 11, 8)


class RecordingTools:
    """Answers a version command from a table, by the first of its arguments the table names, such
    as a Node server's script; records every command it was asked to run."""

    def __init__(self, answers: Mapping[str, ProbeResult | None] | None = None) -> None:
        self.answers = dict(answers or {})
        self.ran: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> ProbeResult | None:
        self.ran.append(tuple(command))
        named = next((argument for argument in command[1:] if argument in self.answers), None)
        return ProbeResult(0, "") if named is None else self.answers[named]


class RecordingCommands:
    def __init__(self, result: ProbeResult | None = PNPM_SUCCEEDED) -> None:
        self.result = result
        self.ran: list[tuple[tuple[str, ...], Path]] = []
        self.environments: list[Mapping[str, str] | None] = []

    def run(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None = None
    ) -> ProbeResult | None:
        self.ran.append((tuple(command), cwd))
        self.environments.append(environment)
        return self.result


def shipped(name: str) -> bytes:
    return (resources.files(MANIFEST_PACKAGE) / name).read_bytes()


def directory(workspace: Path, tools=None, commands=None) -> LspDirectory:
    """On a day of its own, so no test depends on today's date."""
    return LspDirectory(
        workspace, tools or RecordingTools(), commands or RecordingCommands(), today=lambda: TODAY
    )


def version_script(server: LanguageServer) -> str:
    """The script of a Node server whose `--version` prints its version."""
    assert server.version_script is not None
    return server.version_script


def install_server(workspace: Path, script: str | None) -> Path:
    assert script is not None
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
    script = install_server(tmp_path, version_script(BASEDPYRIGHT))
    install_server(tmp_path, BASEDPYRIGHT.script)
    tools = RecordingTools({str(script): ProbeResult(0, "basedpyright 1.40.2\n")})
    found = directory(tmp_path, tools).probe(BASEDPYRIGHT)
    assert (found, tools.ran) == (
        VersionPrinted("basedpyright 1.40.2\n"),
        [("node", "--no-addons", str(script), "--version")],
    )


def test_a_version_command_that_exits_nonzero_gives_its_first_line(tmp_path):
    script = install_server(tmp_path, version_script(BASEDPYRIGHT))
    install_server(tmp_path, BASEDPYRIGHT.script)
    output = "\nError: Cannot find module 'x'\n    at Module._resolve\n"
    tools = RecordingTools({str(script): ProbeResult(1, output)})
    found = directory(tmp_path, tools).probe(BASEDPYRIGHT)
    assert found == VersionFailed("Error: Cannot find module 'x'")


def test_a_silent_failure_names_the_exit_code(tmp_path):
    script = install_server(tmp_path, version_script(BASEDPYRIGHT))
    install_server(tmp_path, BASEDPYRIGHT.script)
    tools = RecordingTools({str(script): ProbeResult(3, "")})
    assert directory(tmp_path, tools).probe(BASEDPYRIGHT) == VersionFailed("exited with 3")


def test_a_missing_node_fails_the_version_command(tmp_path):
    script = install_server(tmp_path, version_script(BASEDPYRIGHT))
    install_server(tmp_path, BASEDPYRIGHT.script)
    tools = RecordingTools({str(script): None})
    assert directory(tmp_path, tools).probe(BASEDPYRIGHT) == VersionFailed("node not found on PATH")


def test_typescript_without_the_workspaces_tsserver_is_missing_a_file(tmp_path):
    install_server(tmp_path, version_script(TYPESCRIPT))
    found = directory(tmp_path).probe(TYPESCRIPT)
    assert found == FileMissing("typescript/node_modules/typescript/lib/tsserver.js")


def test_typescript_with_the_workspaces_tsserver_prints_its_version(tmp_path):
    script = install_server(tmp_path, version_script(TYPESCRIPT))
    tsserver = tmp_path / "typescript/node_modules/typescript/lib/tsserver.js"
    tsserver.parent.mkdir(parents=True)
    tsserver.write_text("")
    tools = RecordingTools({str(script): ProbeResult(0, "6.0.3\n")})
    assert directory(tmp_path, tools).probe(TYPESCRIPT) == VersionPrinted("6.0.3\n")


# JDT LS: an archive, with no version command


def test_jdtls_without_the_core_plugin_of_its_milestone_is_not_installed(tmp_path):
    install_server(tmp_path, "jdtls/plugins/org.eclipse.jdt.ls.core_1.62.0.202609011200.jar")
    assert directory(tmp_path).probe(JDTLS) == NotInstalled()


def test_jdtls_with_the_core_plugin_of_its_milestone_is_unpacked(tmp_path):
    install_server(tmp_path, JDTLS.script)
    assert directory(tmp_path).probe(JDTLS) == Unpacked()


def test_probing_jdtls_starts_no_jvm(tmp_path):
    install_server(tmp_path, JDTLS.script)
    tools = RecordingTools()
    directory(tmp_path, tools).probe(JDTLS)
    assert tools.ran == []


# gopls: a binary that `go install` builds into `.cs/lsp/bin/`


def test_gopls_without_its_binary_is_not_installed(tmp_path):
    assert directory(tmp_path).probe(GOPLS) == NotInstalled()


def test_gopls_prints_its_version_with_its_own_binary(tmp_path):
    binary = install_server(tmp_path, GOPLS.script)
    tools = RecordingTools({"version": ProbeResult(0, "golang.org/x/tools/gopls v0.24.0\n")})
    found = directory(tmp_path, tools).probe(GOPLS)
    assert (found, tools.ran) == (
        VersionPrinted("golang.org/x/tools/gopls v0.24.0\n"),
        [(str(binary), "version")],
    )


def test_the_selected_go_is_what_go_env_prints_with_the_local_toolchain(tmp_path):
    """`GOTOOLCHAIN=local`: asking which Go is selected never downloads another."""
    commands = RecordingCommands(ProbeResult(0, "go1.27.3\n"))
    found = directory(tmp_path, commands=commands).go_release()
    assert (found, commands.ran, commands.environments) == (
        "1.27.3",
        [(("go", "env", "GOVERSION"), tmp_path)],
        [{"GOTOOLCHAIN": "local"}],
    )


@pytest.mark.parametrize("result", [None, ProbeResult(1, "go: unknown\n"), ProbeResult(0, "\n")])
def test_without_a_go_that_runs_no_go_is_selected(tmp_path, result):
    assert directory(tmp_path, commands=RecordingCommands(result)).go_release() is None


def test_go_install_builds_the_version_into_the_lsp_bin_directory(tmp_path):
    commands = RecordingCommands()
    assert GOPLS.go_install is not None
    directory(tmp_path, commands=commands).go_install(GOPLS.go_install, "0.24.0")
    lsp = tmp_path / ".cs" / "lsp"
    assert (commands.ran, commands.environments) == (
        [(("go", "install", "golang.org/x/tools/gopls@v0.24.0"), lsp)],
        [{"GOBIN": f"{lsp}/bin", "GOTOOLCHAIN": "local", "GOWORK": "off"}],
    )


def test_go_install_returns_what_go_did(tmp_path):
    failed = ProbeResult(1, "go: golang.org/x/tools/gopls@v0.24.0: requires go >= 1.27\n")
    assert GOPLS.go_install is not None
    found = directory(tmp_path, commands=RecordingCommands(failed)).go_install(
        GOPLS.go_install, "0.24.0"
    )
    assert found == failed


# rust-analyzer: on PATH, from rustup or not


def test_rust_analyzer_on_path_prints_its_version(tmp_path):
    printed = "rust-analyzer 1.91.0 (f8297e35 2025-10-28)\n"
    tools = RecordingTools({"--version": ProbeResult(0, printed)})
    found = directory(tmp_path, tools).probe(RUST_ANALYZER)
    assert (found, tools.ran) == (VersionPrinted(printed), [("rust-analyzer", "--version")])


def test_rust_analyzer_not_on_path_is_not_installed(tmp_path):
    tools = RecordingTools({"--version": None})
    assert directory(tmp_path, tools).probe(RUST_ANALYZER) == NotInstalled()


def test_the_rustup_proxy_without_the_component_is_not_installed(tmp_path):
    proxy = (
        "error: Unknown binary 'rust-analyzer' in official toolchain "
        "'stable-aarch64-apple-darwin'.\n"
    )
    tools = RecordingTools({"--version": ProbeResult(1, proxy)})
    assert directory(tmp_path, tools).probe(RUST_ANALYZER) == NotInstalled()


def test_a_rust_analyzer_that_fails_otherwise_gives_its_first_line(tmp_path):
    tools = RecordingTools({"--version": ProbeResult(134, "dyld: Library not loaded\n")})
    found = directory(tmp_path, tools).probe(RUST_ANALYZER)
    assert found == VersionFailed("dyld: Library not loaded")


def archive_of(tmp_path: Path, files: Mapping[str, bytes], name: str = "server.tar.gz") -> Archive:
    """A gzipped tar of `files` in `tmp_path`, as a `file:` URL with its SHA-256."""
    path = tmp_path / "served" / name
    path.parent.mkdir(exist_ok=True)
    with tarfile.open(path, "w:gz") as tar:
        for member, content in files.items():
            info = tarfile.TarInfo(member)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Archive(path.as_uri(), digest, "jdtls")


JDTLS_FILES = {CORE_PLUGIN: b"core", "bin/jdtls": b"#!/bin/sh\n"}


def test_a_download_unpacks_the_archive_into_its_directory(tmp_path):
    workspace = tmp_path / "ws"
    result = directory(workspace).download(archive_of(tmp_path, JDTLS_FILES))
    unpacked = workspace / ".cs" / "lsp" / "jdtls"
    assert (result.exit_code, (unpacked / CORE_PLUGIN).read_bytes()) == (0, b"core")


def test_a_downloaded_jdtls_is_then_unpacked(tmp_path):
    workspace = tmp_path / "ws"
    lsp = directory(workspace)
    lsp.download(archive_of(tmp_path, JDTLS_FILES))
    assert lsp.probe(JDTLS) == Unpacked()


def test_a_download_whose_sha256_differs_unpacks_nothing(tmp_path):
    workspace = tmp_path / "ws"
    archive = archive_of(tmp_path, JDTLS_FILES)
    tampered = Archive(archive.url, "0" * 64, archive.directory)
    result = directory(workspace).download(tampered)
    assert (result.exit_code, (workspace / ".cs" / "lsp" / "jdtls").exists()) == (1, False)


def test_a_sha256_mismatch_names_both_digests(tmp_path):
    archive = archive_of(tmp_path, JDTLS_FILES)
    result = directory(tmp_path / "ws").download(Archive(archive.url, "0" * 64, "jdtls"))
    assert result.output == f"SHA-256 mismatch: expected {'0' * 64}, got {archive.sha256}\n"


def test_a_download_that_fails_keeps_the_earlier_build(tmp_path):
    workspace = tmp_path / "ws"
    kept = install_server(workspace, "jdtls/plugins/kept.jar")
    missing = Archive((tmp_path / "nowhere.tar.gz").as_uri(), "0" * 64, "jdtls")
    result = directory(workspace).download(missing)
    assert (result.exit_code, kept.read_text()) == (1, "// the server\n")


def test_a_download_replaces_an_earlier_build_whole(tmp_path):
    workspace = tmp_path / "ws"
    stale = install_server(workspace, "jdtls/plugins/org.eclipse.jdt.ls.core_1.62.0.jar")
    directory(workspace).download(archive_of(tmp_path, JDTLS_FILES))
    assert stale.exists() is False


def test_a_download_leaves_nothing_else_in_the_lsp_directory(tmp_path):
    workspace = tmp_path / "ws"
    directory(workspace).download(archive_of(tmp_path, JDTLS_FILES))
    assert sorted(path.name for path in (workspace / ".cs" / "lsp").iterdir()) == ["jdtls"]


def test_a_failed_download_leaves_nothing_in_the_lsp_directory(tmp_path):
    workspace = tmp_path / "ws"
    archive = archive_of(tmp_path, JDTLS_FILES)
    directory(workspace).download(Archive(archive.url, "0" * 64, "jdtls"))
    assert list((workspace / ".cs" / "lsp").iterdir()) == []


def test_an_archive_member_that_leaves_its_directory_is_refused(tmp_path):
    workspace = tmp_path / "ws"
    archive = archive_of(tmp_path, {"../escaped": b"x"})
    result = directory(workspace).download(archive)
    assert (result.exit_code, (workspace / ".cs" / "escaped").exists()) == (1, False)


EXECUTABLE = 0o755
LINK_MODE = 0o120777


def zip_of(tmp_path: Path, members: Sequence[tuple[str, bytes, int]]) -> Archive:
    """A zip of `(name, content, Unix mode)` members, as a `file:` URL with its SHA-256: a mode
    with the symbolic link bits makes the content the link's target, as `zip --symlinks` does."""
    path = tmp_path / "served" / "server.zip"
    path.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content, mode in members:
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            archive.writestr(info, content)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Archive(path.as_uri(), digest, "kotlin-lsp")


SERVER_ZIP = [
    ("server/bin/launcher", b"#!/bin/sh\n", EXECUTABLE),
    ("server/lib/server.jar", b"jar", 0o644),
]


def test_a_zip_archive_is_unpacked_into_its_directory(tmp_path):
    workspace = tmp_path / "ws"
    result = directory(workspace).download(zip_of(tmp_path, SERVER_ZIP))
    unpacked = workspace / ".cs" / "lsp" / "kotlin-lsp" / "server" / "lib" / "server.jar"
    assert (result.exit_code, unpacked.read_bytes()) == (0, b"jar")


def test_an_archive_whose_top_directory_is_stripped_puts_the_build_where_it_goes(tmp_path):
    workspace = tmp_path / "ws"
    nested = zip_of(tmp_path, [("kotlin-server-1.0/bin/launcher", b"#!/bin/sh\n", EXECUTABLE)])
    archive = Archive(nested.url, nested.sha256, "kotlin-lsp", "server", "kotlin-server-1.0")
    directory(workspace).download(archive)
    launcher = workspace / ".cs" / "lsp" / "kotlin-lsp" / "server" / "bin" / "launcher"
    assert os.access(launcher, os.X_OK)


def test_an_archive_without_the_top_directory_to_strip_is_refused(tmp_path):
    workspace = tmp_path / "ws"
    flat = zip_of(tmp_path, [("bin/launcher", b"#!/bin/sh\n", EXECUTABLE)])
    archive = Archive(flat.url, flat.sha256, "kotlin-lsp", "server", "kotlin-server-1.0")
    result = directory(workspace).download(archive)
    assert (result.exit_code, (workspace / ".cs" / "lsp" / "kotlin-lsp").exists()) == (1, False)


def test_an_archive_with_a_directory_to_go_into_is_unpacked_into_it(tmp_path):
    workspace = tmp_path / "ws"
    flat = zip_of(tmp_path, [("bin/launcher", b"#!/bin/sh\n", EXECUTABLE)])
    directory(workspace).download(Archive(flat.url, flat.sha256, "kotlin-lsp", "build-1"))
    launcher = workspace / ".cs" / "lsp" / "kotlin-lsp" / "build-1" / "bin" / "launcher"
    assert os.access(launcher, os.X_OK)


def test_a_zip_member_keeps_its_executable_mode(tmp_path):
    workspace = tmp_path / "ws"
    directory(workspace).download(zip_of(tmp_path, SERVER_ZIP))
    launcher = workspace / ".cs" / "lsp" / "kotlin-lsp" / "server" / "bin" / "launcher"
    assert os.access(launcher, os.X_OK)


def test_a_zip_member_without_a_mode_is_a_plain_file(tmp_path):
    workspace = tmp_path / "ws"
    directory(workspace).download(zip_of(tmp_path, [("server/notes.txt", b"n", 0)]))
    notes = workspace / ".cs" / "lsp" / "kotlin-lsp" / "server" / "notes.txt"
    assert (notes.read_bytes(), os.access(notes, os.X_OK)) == (b"n", False)


def test_a_zip_symbolic_link_inside_its_directory_is_kept_as_a_link(tmp_path):
    workspace = tmp_path / "ws"
    members = [*SERVER_ZIP, ("server/lib/current.jar", b"server.jar", LINK_MODE)]
    directory(workspace).download(zip_of(tmp_path, members))
    link = workspace / ".cs" / "lsp" / "kotlin-lsp" / "server" / "lib" / "current.jar"
    assert (link.is_symlink(), link.read_bytes()) == (True, b"jar")


def test_a_zip_symbolic_link_that_leaves_its_directory_is_refused(tmp_path):
    workspace = tmp_path / "ws"
    members = [*SERVER_ZIP, ("server/escape", b"../../../../outside", LINK_MODE)]
    result = directory(workspace).download(zip_of(tmp_path, members))
    assert (result.exit_code, (workspace / ".cs" / "lsp" / "kotlin-lsp").exists()) == (1, False)


def test_a_zip_member_that_leaves_its_directory_is_refused(tmp_path):
    workspace = tmp_path / "ws"
    result = directory(workspace).download(zip_of(tmp_path, [("../escaped", b"x", 0o644)]))
    assert (result.exit_code, (workspace / ".cs" / "escaped").exists()) == (1, False)


def test_an_absolute_zip_member_is_refused(tmp_path):
    workspace = tmp_path / "ws"
    result = directory(workspace).download(zip_of(tmp_path, [("/tmp/escaped", b"x", 0o644)]))
    assert result.exit_code == 1


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
        assert dependencies == {server.name: server.version for server in NPM_SERVERS}

    @pytest.mark.parametrize("server", NPM_SERVERS, ids=lambda s: s.name)
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


MARKER = '# the marker\nschema = 1\ncreated_with = "0.30.0"\n'
OTHER_TERMS = replace(KOTLIN_LSP_LICENSE, name="Another Agreement")


def with_marker(workspace: Path, text: str = MARKER) -> Path:
    marker = workspace / ".cs" / "workspace.toml"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(text)
    return marker


class TestLicenses:
    """The workspace's marker records the licenses you accepted (ADR 0018, Kotlin revisited)."""

    def test_a_license_is_not_accepted_until_you_accept_it(self, tmp_path):
        with_marker(tmp_path)
        assert directory(tmp_path).license_accepted(KOTLIN_LSP_LICENSE) is False

    def test_a_license_you_accept_is_accepted(self, tmp_path):
        with_marker(tmp_path)
        lsp = directory(tmp_path)
        lsp.accept_license(KOTLIN_LSP_LICENSE)
        assert lsp.license_accepted(KOTLIN_LSP_LICENSE) is True

    def test_the_marker_records_the_license_by_its_key_with_its_name_and_link(self, tmp_path):
        marker = with_marker(tmp_path)
        directory(tmp_path).accept_license(KOTLIN_LSP_LICENSE)
        assert tomllib.loads(marker.read_text())["licenses"]["kotlin-lsp"] == {
            "name": KOTLIN_LSP_LICENSE.name,
            "url": KOTLIN_LSP_LICENSE.url,
        }

    def test_the_marker_keeps_what_it_held(self, tmp_path):
        marker = with_marker(tmp_path)
        directory(tmp_path).accept_license(KOTLIN_LSP_LICENSE)
        assert (marker.read_text().startswith(MARKER), read_marker(tmp_path).schema) == (True, 1)

    def test_accepting_twice_records_the_license_once(self, tmp_path):
        marker = with_marker(tmp_path)
        lsp = directory(tmp_path)
        lsp.accept_license(KOTLIN_LSP_LICENSE)
        lsp.accept_license(KOTLIN_LSP_LICENSE)
        assert marker.read_text().count("[licenses.kotlin-lsp]") == 1

    def test_a_license_whose_terms_changed_is_not_accepted(self, tmp_path):
        with_marker(tmp_path)
        lsp = directory(tmp_path)
        lsp.accept_license(KOTLIN_LSP_LICENSE)
        assert lsp.license_accepted(OTHER_TERMS) is False

    def test_accepting_changed_terms_records_them_in_place_of_the_old_ones(self, tmp_path):
        marker = with_marker(tmp_path)
        lsp = directory(tmp_path)
        lsp.accept_license(KOTLIN_LSP_LICENSE)
        lsp.accept_license(OTHER_TERMS)
        recorded = tomllib.loads(marker.read_text())["licenses"]["kotlin-lsp"]["name"]
        assert (recorded, lsp.license_accepted(KOTLIN_LSP_LICENSE)) == ("Another Agreement", False)

    def test_without_a_marker_no_license_is_accepted(self, tmp_path):
        assert directory(tmp_path).license_accepted(KOTLIN_LSP_LICENSE) is False

    def test_an_unreadable_marker_accepts_no_license(self, tmp_path):
        with_marker(tmp_path, "schema = [\n")
        assert directory(tmp_path).license_accepted(KOTLIN_LSP_LICENSE) is False


def test_the_machine_is_the_platform_and_the_processor_of_this_one():
    assert directory(Path("/ws")).machine == machine_of(sys.platform, platform.machine())


class RecordingEnvironments(RecordingCommands):
    """Also records the environment each command ran with."""

    def __init__(self, result: ProbeResult | None = PNPM_SUCCEEDED) -> None:
        super().__init__(result)
        self.environments: list[Mapping[str, str] | None] = []

    def run(
        self, command: Sequence[str], cwd: Path, environment: Mapping[str, str] | None = None
    ) -> ProbeResult | None:
        self.environments.append(environment)
        return super().run(command, cwd, environment)


class TestWarmUp:
    """A warm-up runs the server's own script under cstudy's Python, with a scratch index."""

    def warmed(self, tmp_path: Path, result: ProbeResult = PNPM_SUCCEEDED) -> RecordingEnvironments:
        commands = RecordingEnvironments(result)
        directory(tmp_path, commands=commands).warm_up(KOTLIN_LSP, "jvm", Path("/jdk"))
        return commands

    def test_it_runs_the_vendor_script_isolated_under_cstudys_python_in_the_root(self, tmp_path):
        command, cwd = self.warmed(tmp_path).ran[0]
        script = f"{tmp_path}/.cs/lsp/kotlin-lsp/server/bin/warmup.py"
        assert (command[:3], cwd) == ((sys.executable, "-I", script), tmp_path / "jvm")

    def test_it_names_the_root_and_the_launcher(self, tmp_path):
        command, _cwd = self.warmed(tmp_path).ran[0]
        launcher = command[command.index("--server") + 1]
        assert (command[3], launcher.endswith("/bin/intellij-server")) == (f"{tmp_path}/jvm", True)

    def test_its_index_is_in_a_scratch_directory_of_the_lsp_directory(self, tmp_path):
        command, _cwd = self.warmed(tmp_path).ran[0]
        assert Path(command[4]).parent.parent == tmp_path / ".cs" / "lsp"

    def test_the_scratch_directory_is_gone_afterwards(self, tmp_path):
        command, _cwd = self.warmed(tmp_path).ran[0]
        assert Path(command[4]).parent.exists() is False

    def test_it_imports_with_the_jdk_it_is_given(self, tmp_path):
        environment = self.warmed(tmp_path).environments[0] or {}
        assert "-Dcom.jetbrains.ls.imports.gradle.java.home=/jdk" in environment["IJ_JAVA_OPTIONS"]

    def test_it_returns_what_the_script_did(self, tmp_path):
        commands = RecordingEnvironments(ProbeResult(1, "stopped\n"))
        result = directory(tmp_path, commands=commands).warm_up(KOTLIN_LSP, "jvm", Path("/jdk"))
        assert result == ProbeResult(1, "stopped\n")

    def test_a_server_without_a_warm_up_runs_nothing(self, tmp_path):
        commands = RecordingEnvironments()
        result = directory(tmp_path, commands=commands).warm_up(JDTLS, "jvm", Path("/jdk"))
        assert (result, commands.ran) == (None, [])


class FakeHttps:
    """Answers HTTPS reads from a table of URLs; an absent URL fails as a 404 does."""

    def __init__(self, answers: Mapping[str, bytes]) -> None:
        self.answers = dict(answers)
        self.read: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.read.append(url)
        if url not in self.answers:
            raise OSError(f"HTTP Error 404: Not Found: {url}")
        return self.answers[url]


RELEASES_URL = "https://api.github.com/repos/Kotlin/kotlin-lsp/releases"
KOTLIN_DOWNLOADS = "https://download.jetbrains.com/language-server/kotlin-server"
LICENSE_TEXT = (
    b"JETBRAINS FREE PLUGIN LICENSE AGREEMENT\n\nVersion 1.0, effective as of September 15, 2025\n"
)
LICENSE_AT_TAG = (
    "https://raw.githubusercontent.com/Kotlin/kotlin-lsp/kotlin-lsp/v263.9000.0/"
    "kotlin-vscode/LICENSE.txt"
)


def releases_answers(machine_file: str, sha256: str, url: str | None = None) -> dict[str, bytes]:
    """JetBrains' release of 263.9000.0 for this machine, its checksum and its license; `url`
    serves the archive from elsewhere while the notes name the download server."""
    named = f"{KOTLIN_DOWNLOADS}/263.9000.0/{machine_file}"
    notes = f"* [Download]({named}) | [SHA-256 checksum]({named}.sha256)"
    listed = [{"tag_name": "kotlin-lsp/v263.9000.0", "draft": False, "body": notes}]
    answers = {
        RELEASES_URL: json.dumps(listed).encode(),
        f"{named}.sha256": f"{sha256} *{machine_file}\n".encode(),
        LICENSE_AT_TAG: LICENSE_TEXT,
    }
    if url is not None:
        answers["served"] = url.encode()
    return answers


def this_machines_file() -> str:
    releases = KOTLIN_LSP.releases
    assert releases is not None
    suffix = releases.suffixes[machine_of(sys.platform, platform.machine())]
    return f"kotlin-server-263.9000.0{suffix}"


def fetching(workspace: Path, https: FakeHttps, commands=None) -> LspDirectory:
    return LspDirectory(
        workspace,
        RecordingTools(),
        commands or RecordingCommands(),
        today=lambda: TODAY,
        fetch=https,
    )


class TestNewestBuild:
    """The newest build of the Kotlin LSP: the releases list, the checksum published beside the
    archive of this machine, and the license at the release's tag; nothing is downloaded."""

    def newest(self, tmp_path: Path, answers: dict[str, bytes]) -> NewestBuild | NoBuild:
        return fetching(tmp_path, FakeHttps(answers)).newest_build(KOTLIN_LSP)

    def test_it_names_the_newest_release_and_its_archive_for_this_machine(self, tmp_path):
        found = self.newest(tmp_path, releases_answers(this_machines_file(), "a" * 64))
        assert isinstance(found, NewestBuild)
        assert (found.build.version, found.archive.url.endswith(this_machines_file())) == (
            "263.9000.0",
            True,
        )

    def test_it_checks_the_archive_against_the_published_sha256(self, tmp_path):
        found = self.newest(tmp_path, releases_answers(this_machines_file(), "A" * 64))
        assert isinstance(found, NewestBuild)
        assert found.archive.sha256 == "a" * 64

    def test_it_comes_under_the_license_of_its_release(self, tmp_path):
        found = self.newest(tmp_path, releases_answers(this_machines_file(), "a" * 64))
        assert isinstance(found, NewestBuild)
        assert found.license is KOTLIN_LSP_LICENSE

    def test_without_a_published_checksum_there_is_no_build(self, tmp_path):
        answers = releases_answers(this_machines_file(), "a" * 64)
        del answers[next(url for url in answers if url.endswith(".sha256"))]
        assert isinstance(self.newest(tmp_path, answers), NoBuild)

    def test_a_checksum_file_that_names_another_archive_gives_no_build(self, tmp_path):
        answers = releases_answers(this_machines_file(), "a" * 64)
        checksum = next(url for url in answers if url.endswith(".sha256"))
        answers[checksum] = f"{'a' * 64} *another.sit".encode()
        found = self.newest(tmp_path, answers)
        assert isinstance(found, NoBuild)
        assert "holds no SHA-256" in found.reason

    def test_without_the_license_of_the_release_there_is_no_build(self, tmp_path):
        answers = releases_answers(this_machines_file(), "a" * 64)
        del answers[LICENSE_AT_TAG]
        assert isinstance(self.newest(tmp_path, answers), NoBuild)

    def test_without_the_network_there_is_no_build_and_it_says_why(self, tmp_path):
        found = self.newest(tmp_path, {})
        assert isinstance(found, NoBuild)
        assert found.reason.startswith("cannot read the releases of kotlin-lsp: HTTP Error 404")

    def test_a_release_without_an_archive_for_this_machine_gives_no_build(self, tmp_path):
        found = self.newest(tmp_path, releases_answers("kotlin-server-263.9000.0.vsix", "a" * 64))
        assert isinstance(found, NoBuild)

    def test_nothing_is_downloaded_yet(self, tmp_path):
        https = FakeHttps(releases_answers(this_machines_file(), "a" * 64))
        fetching(tmp_path, https).newest_build(KOTLIN_LSP)
        assert not any(url.endswith(this_machines_file()) for url in https.read)


STATUS = (
    "License: licensed\nSource: eap (Valid), licensed to kotlin-server EAP User, valid through "
    "2026-11-12 (4 days left)\nThis build does not require a license.\n"
)


class TestInstallBuild:
    """The newest build put in place, checked, asked its last day and recorded."""

    def installed(self, tmp_path: Path, status: str = STATUS):
        workspace = tmp_path / "ws"
        top = "" if sys.platform == "win32" else "kotlin-server-263.9000.0/"
        launcher = "bin/intellij-server.exe" if sys.platform == "win32" else "bin/intellij-server"
        served = zip_of(tmp_path, [(f"{top}{launcher}", b"#!/bin/sh\n", EXECUTABLE)])
        https = FakeHttps(releases_answers(this_machines_file(), served.sha256))
        commands = RecordingEnvironments(ProbeResult(0, status))
        lsp = fetching(workspace, https, commands)
        newest = lsp.newest_build(KOTLIN_LSP)
        assert isinstance(newest, NewestBuild)
        local = replace(newest, archive=replace(newest.archive, url=served.url))
        return lsp, lsp.install_build(KOTLIN_LSP, local), commands, workspace

    def test_the_build_is_in_place_and_says_until_when_it_runs(self, tmp_path):
        _lsp, result, _commands, _workspace = self.installed(tmp_path)
        expected = "kotlin-lsp 263.9000.0 in .cs/lsp/kotlin-lsp, runs until 2026-11-12\n"
        assert result.output == expected

    def test_its_probe_names_the_version_the_last_day_and_the_license(self, tmp_path):
        lsp, _result, _commands, _workspace = self.installed(tmp_path)
        expected = Fetched("263.9000.0", date(2026, 11, 12), KOTLIN_LSP_LICENSE)
        assert lsp.probe(KOTLIN_LSP) == expected

    def test_it_asks_the_build_its_last_day_without_starting_a_server(self, tmp_path):
        _lsp, _result, commands, _workspace = self.installed(tmp_path)
        command, _cwd = commands.ran[0]
        assert command[1:] == ("license", "status")

    def test_the_record_beside_the_build_holds_where_it_came_from(self, tmp_path):
        _lsp, _result, _commands, workspace = self.installed(tmp_path)
        written = workspace / ".cs" / "lsp" / "kotlin-lsp" / "installed.json"
        record = json.loads(written.read_text())
        assert (record["version"], record["last_day"], record["license"]["name"]) == (
            "263.9000.0",
            "2026-11-12",
            KOTLIN_LSP_LICENSE.name,
        )

    def test_a_build_that_has_expired_already_is_a_failure(self, tmp_path):
        expired = "This build of kotlin-server has expired.\nThe IDE will now close.\n"
        _lsp, result, _commands, _workspace = self.installed(tmp_path, expired)
        assert (result.exit_code, result.output) == (
            1,
            "kotlin-lsp 263.9000.0, JetBrains' newest, has expired\n",
        )

    def test_a_status_without_a_last_day_records_none(self, tmp_path):
        lsp, _result, _commands, _workspace = self.installed(tmp_path, "License: licensed\n")
        assert lsp.probe(KOTLIN_LSP) == Fetched("263.9000.0", None, KOTLIN_LSP_LICENSE)

    def test_a_download_that_fails_its_check_records_nothing(self, tmp_path):
        workspace = tmp_path / "ws"
        https = FakeHttps(releases_answers(this_machines_file(), "0" * 64))
        lsp = fetching(workspace, https)
        newest = lsp.newest_build(KOTLIN_LSP)
        assert isinstance(newest, NewestBuild)
        served = zip_of(tmp_path, [("x", b"x", 0o644)])
        result = lsp.install_build(
            KOTLIN_LSP, replace(newest, archive=replace(newest.archive, url=served.url))
        )
        assert (result.exit_code, lsp.probe(KOTLIN_LSP)) == (1, NotInstalled())


def kotlin_record(workspace: Path, content: str) -> None:
    record = workspace / ".cs" / "lsp" / "kotlin-lsp" / "installed.json"
    record.parent.mkdir(parents=True)
    record.write_text(content)


def test_a_kotlin_lsp_without_its_record_is_not_installed(tmp_path):
    assert directory(tmp_path).probe(KOTLIN_LSP) == NotInstalled()


def test_a_record_whose_build_is_gone_is_not_installed(tmp_path):
    named = {"version": "1", "last_day": None, "license": {"name": "n", "url": "u"}}
    kotlin_record(tmp_path, json.dumps(named))
    assert directory(tmp_path).probe(KOTLIN_LSP) == NotInstalled()


def test_an_unreadable_record_is_not_installed(tmp_path):
    kotlin_record(tmp_path, "{")
    assert directory(tmp_path).probe(KOTLIN_LSP) == NotInstalled()


def test_today_is_the_clock_it_was_given(tmp_path):
    assert directory(tmp_path).today() == TODAY


def linux_file() -> str:
    """The Linux archive for this machine's processor, which a sidecar runs."""
    releases = KOTLIN_LSP.releases
    assert releases is not None
    suffix = releases.suffixes[machine_of("linux", platform.machine())]
    return f"kotlin-server-263.9000.0{suffix}"


def tooling_jar(directory: Path, version: str = "9.7.0") -> bytes:
    """A jar of the Gradle tooling API with its build receipt, as the Kotlin LSP bundles it."""
    jar = directory / "tooling.jar"
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("org/gradle/build-receipt.properties", f"versionNumber={version}\n")
    return jar.read_bytes()


class TestLinuxBuild:
    """The Linux build of the Kotlin LSP, for a Kotlin service project's sidecar: fetched as this
    machine's is, put beside it, never run here."""

    def installed(self, tmp_path: Path, host_version: str | None = "263.9000.0"):
        workspace = tmp_path / "ws"
        if host_version is not None:
            this_machines_build(workspace, host_version)
        members = [
            ("kotlin-server-263.9000.0/bin/intellij-server", b"#!/bin/sh\n", EXECUTABLE),
            (
                "kotlin-server-263.9000.0/plugins/kotlin.lsp/lib/modules/"
                "intellij.libraries.gradle.tooling.jar",
                tooling_jar(tmp_path),
                0o644,
            ),
        ]
        served = zip_of(tmp_path, members)
        https = FakeHttps(releases_answers(linux_file(), served.sha256))
        commands = RecordingEnvironments(ProbeResult(0, STATUS))
        lsp = fetching(workspace, https, commands)
        newest = lsp.newest_build(KOTLIN_LSP_LINUX)
        assert isinstance(newest, NewestBuild)
        local = replace(newest, archive=replace(newest.archive, url=served.url))
        return lsp, lsp.install_build(KOTLIN_LSP_LINUX, local), commands, workspace

    def test_the_newest_build_is_linuxs_for_this_machines_processor(self, tmp_path):
        https = FakeHttps(releases_answers(linux_file(), "a" * 64))
        found = fetching(tmp_path, https).newest_build(KOTLIN_LSP_LINUX)
        assert isinstance(found, NewestBuild)
        assert (found.archive.url.endswith(linux_file()), found.archive.into) == (True, "linux")

    def test_it_goes_beside_this_machines_build_which_stays(self, tmp_path):
        _lsp, result, _commands, workspace = self.installed(tmp_path)
        builds = workspace / ".cs" / "lsp" / "kotlin-lsp"
        assert (result.exit_code, sorted(entry.name for entry in builds.iterdir())) == (
            0,
            ["installed.json", "linux", "linux.json", "server"],
        )

    def test_it_is_never_run_on_this_machine(self, tmp_path):
        _lsp, _result, commands, _workspace = self.installed(tmp_path)
        assert commands.ran == []

    def test_its_last_day_is_that_of_this_machines_build_of_the_same_version(self, tmp_path):
        lsp, _result, _commands, _workspace = self.installed(tmp_path)
        expected = Fetched("263.9000.0", date(2026, 11, 12), KOTLIN_LSP_LICENSE, "9.7.0")
        assert lsp.probe(KOTLIN_LSP_LINUX) == expected

    def test_without_this_machines_build_of_its_version_it_names_no_last_day(self, tmp_path):
        lsp, _result, _commands, _workspace = self.installed(tmp_path, "263.8000.0")
        probe = lsp.probe(KOTLIN_LSP_LINUX)
        assert isinstance(probe, Fetched)
        assert probe.last_day is None

    def test_its_record_names_the_gradle_tooling_api_it_bundles(self, tmp_path):
        _lsp, _result, _commands, workspace = self.installed(tmp_path)
        record = json.loads((workspace / ".cs/lsp/kotlin-lsp/linux.json").read_text())
        assert record["gradle_tooling"] == "9.7.0"


def this_machines_build(workspace: Path, version: str) -> None:
    """This machine's Kotlin LSP build in place, as `--fix` records it, running until
    2026-11-12."""
    lsp = workspace / ".cs" / "lsp" / "kotlin-lsp"
    launcher = lsp / "server" / "bin" / "intellij-server"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("#!/bin/sh\n")
    named = {"name": KOTLIN_LSP_LICENSE.name, "url": KOTLIN_LSP_LICENSE.url}
    record = {"version": version, "last_day": "2026-11-12", "license": named}
    (lsp / "installed.json").write_text(json.dumps(record))


def install_record(workspace: Path, slug: str, document: object) -> None:
    record = workspace / ".cs" / "projects" / f"{slug}.install.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(document))


def test_the_service_languages_are_those_the_install_records_name(tmp_path):
    install_record(tmp_path, "rooms-kotlin", {"lock_sha256": "x", "language": "kotlin"})
    install_record(tmp_path, "rooms-go", {"lock_sha256": "x", "language": "go"})
    install_record(tmp_path, "old", {"lock_sha256": "x"})
    assert directory(tmp_path).installed_service_languages() == {Language.KOTLIN, Language.GO}


def test_an_unreadable_install_record_names_no_language(tmp_path):
    record = tmp_path / ".cs" / "projects" / "broken.install.json"
    record.parent.mkdir(parents=True)
    record.write_text("{")
    assert directory(tmp_path).installed_service_languages() == frozenset()
