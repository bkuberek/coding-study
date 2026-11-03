"""`.cs/lsp/`: the pnpm project of the web UI's language servers
(docs/specs/installation-and-workspaces.md#layout, docs/specs/web-ui.md#language-servers)."""

from importlib import resources
from pathlib import Path

from coding_study.application.ports import (
    CommandRunner,
    FileMissing,
    NotInstalled,
    ProbeResult,
    ServerProbe,
    ToolProbe,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import LSP_DIRECTORY, LSP_INSTALL_COMMAND, LanguageServer

MANIFEST_PACKAGE = "coding_study.adapters.language_servers"
MANIFEST_FILES = ("package.json", "pnpm-lock.yaml")
NODE_NOT_FOUND = "node not found on PATH"


class LspDirectory:
    """Locates the servers in a workspace's `.cs/lsp/` and installs them there."""

    def __init__(self, workspace: Path, tools: ToolProbe, commands: CommandRunner) -> None:
        self._workspace = workspace
        self._directory = workspace / LSP_DIRECTORY
        self._tools = tools
        self._commands = commands

    def probe(self, server: LanguageServer) -> ServerProbe:
        """Not installed without the server's scripts; a file missing when its package is there
        but the workspace's TypeScript is not; otherwise what its version command printed."""
        if not (self._directory / server.script).is_file():
            return NotInstalled()
        requirement = server.requirement
        if requirement is not None and not (self._workspace / requirement.path).is_file():
            return FileMissing(requirement.path)
        return self._version(server)

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


def _first_line(output: str) -> str:
    return next((line.strip() for line in output.splitlines() if line.strip()), "")


def _write_if_different(path: Path, content: bytes) -> None:
    if path.is_file() and path.read_bytes() == content:
        return
    path.write_bytes(content)
