"""`.cs/lsp/`: the pnpm project of the web UI's language servers, and the servers downloaded as
archives beside it (docs/specs/installation-and-workspaces.md#layout,
docs/specs/web-ui.md#language-servers)."""

import hashlib
import tarfile
import tempfile
import urllib.request
from importlib import resources
from pathlib import Path

from coding_study.application.ports import (
    CommandRunner,
    FileMissing,
    NotInstalled,
    ProbeResult,
    ServerProbe,
    ToolProbe,
    Unpacked,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import (
    LSP_DIRECTORY,
    LSP_INSTALL_COMMAND,
    Archive,
    LanguageServer,
)

MANIFEST_PACKAGE = "coding_study.adapters.language_servers"
MANIFEST_FILES = ("package.json", "pnpm-lock.yaml")
NODE_NOT_FOUND = "node not found on PATH"
DOWNLOAD_TIMEOUT_S = 60
"""How long the download may wait for the server to answer or send more."""
CHUNK_BYTES = 1024 * 1024


class LspDirectory:
    """Locates the servers in a workspace's `.cs/lsp/` and installs them there."""

    def __init__(self, workspace: Path, tools: ToolProbe, commands: CommandRunner) -> None:
        self._workspace = workspace
        self._directory = workspace / LSP_DIRECTORY
        self._tools = tools
        self._commands = commands

    def probe(self, server: LanguageServer) -> ServerProbe:
        """Not installed without the server's scripts; a file missing when its package is there
        but the workspace's TypeScript is not; unpacked for an archive whose pinned build is
        there, which has no version command; otherwise what its version command printed."""
        if not (self._directory / server.script).is_file():
            return NotInstalled()
        requirement = server.requirement
        if requirement is not None and not (self._workspace / requirement.path).is_file():
            return FileMissing(requirement.path)
        if server.version_script is None:
            return Unpacked()
        return self._version(server)

    def download(self, archive: Archive) -> ProbeResult:
        """Fetch the archive into a scratch directory of `.cs/lsp/`, check its SHA-256, unpack it
        there refusing any member that would land outside, and only then put it in place of its
        directory; whatever fails leaves the earlier build as it was and no scratch behind."""
        self._directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".download-", dir=self._directory) as scratch:
            try:
                return _unpacked(archive, Path(scratch), self._directory / archive.directory)
            except (OSError, tarfile.TarError) as error:
                return ProbeResult(1, f"{error}\n")

    def install(self) -> ProbeResult | None:
        """Write the shipped manifest where it differs, then install from the lock. Always runs
        pnpm, which has nothing to download when `node_modules/` already matches the lock."""
        self._directory.mkdir(parents=True, exist_ok=True)
        package = resources.files(MANIFEST_PACKAGE)
        for name in MANIFEST_FILES:
            _write_if_different(self._directory / name, (package / name).read_bytes())
        return self._commands.run(LSP_INSTALL_COMMAND, self._directory)

    def _version(self, server: LanguageServer) -> ServerProbe:
        result = self._tools.run(server.version_command(str(self._directory)))
        if result is None:
            return VersionFailed(NODE_NOT_FOUND)
        if result.exit_code != 0:
            return VersionFailed(_first_line(result.output) or f"exited with {result.exit_code}")
        return VersionPrinted(result.output)


def _unpacked(archive: Archive, scratch: Path, target: Path) -> ProbeResult:
    downloaded = scratch / "archive"
    digest = _fetched(archive.url, downloaded)
    if digest != archive.sha256:
        return ProbeResult(1, f"SHA-256 mismatch: expected {archive.sha256}, got {digest}\n")
    unpacked = scratch / "unpacked"
    with tarfile.open(downloaded) as tar:
        tar.extractall(unpacked, filter="data")
    if target.exists():
        target.rename(scratch / "earlier")
    unpacked.rename(target)
    return ProbeResult(0, f"unpacked into {LSP_DIRECTORY}/{archive.directory}\n")


def _fetched(url: str, path: Path) -> str:
    """Writes what `url` holds to `path`; its SHA-256."""
    digest = hashlib.sha256()
    with (
        urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response,
        path.open("wb") as out,
    ):
        while chunk := response.read(CHUNK_BYTES):
            digest.update(chunk)
            out.write(chunk)
    return digest.hexdigest()


def _first_line(output: str) -> str:
    return next((line.strip() for line in output.splitlines() if line.strip()), "")


def _write_if_different(path: Path, content: bytes) -> None:
    if path.is_file() and path.read_bytes() == content:
        return
    path.write_bytes(content)
