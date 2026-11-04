"""The catalog of language servers behind the web UI's code intelligence
(docs/specs/web-ui.md#language-servers, ADR 0018).

Paths are POSIX strings: relative to the workspace root, or to `.cs/lsp/` where the field says so.
Commands take the absolute directory they run from, so no path type is needed here.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from coding_study.domain.cases import JsonValue
from coding_study.domain.layout import PYTHON_PROJECT, TYPESCRIPT_PROJECT
from coding_study.domain.problem import Language

LSP_DIRECTORY = ".cs/lsp"
"""The pnpm project that cstudy owns in the workspace, ignored by git."""
LSP_INSTALL_COMMAND = ("pnpm", "install", "--frozen-lockfile", "--ignore-scripts")
"""Run in `LSP_DIRECTORY`: the lock pins every version with its integrity hash, and no package
script runs."""
NOT_AVAILABLE_YET = "not available yet"
NODE = "node"
IDLE_SECONDS = 60
"""How long the page keeps a session whose files are all closed."""

_VERSION = re.compile(r"\d+(?:\.\d+)+")


@dataclass(frozen=True, slots=True)
class Requirement:
    """A workspace file the server needs besides its own package."""

    path: str
    """Relative to the workspace root."""
    missing: str
    """What the `code intelligence` row says while the file is not there."""


@dataclass(frozen=True, slots=True)
class LanguageServer:
    language: Language
    name: str
    version: str
    """The pinned version: `package.json` and `pnpm-lock.yaml` name the same one."""
    script: str
    """The `bin` script the package's `package.json` names for the server, relative to
    `.cs/lsp/`, never a `.bin/` shim."""
    version_script: str
    """The script whose `--version` prints the version, relative to `.cs/lsp/`."""
    root_project: str
    """The practice project that roots a single-file attempt; an attempt in a project folder is
    rooted in that folder."""
    initialization_options: Callable[[str], dict[str, JsonValue]]
    """The server's `initializationOptions` for the workspace at the given absolute path."""
    settings: Mapping[str, JsonValue]
    """What `workspace/configuration` answers, by the section the server asks for: basedpyright asks
    for `basedpyright`, `pyright` and `python`, never for a dotted `basedpyright.analysis`."""
    capabilities: Mapping[str, JsonValue]
    """The client capabilities the broker declares in `initialize`."""
    requirement: Requirement | None = None
    idle_s: int = IDLE_SECONDS

    def command(self, lsp_directory: str) -> tuple[str, ...]:
        return (NODE, f"{lsp_directory}/{self.script}", "--stdio")

    def version_command(self, lsp_directory: str) -> tuple[str, ...]:
        return (NODE, f"{lsp_directory}/{self.version_script}", "--version")

    def printed_version(self, output: str) -> str | None:
        """The version on the first line the version command printed; None if it has none."""
        first_line = output.strip().partition("\n")[0]
        found = _VERSION.search(first_line)
        return found[0] if found else None


_DOCUMENTATION_FORMATS: list[JsonValue] = ["markdown", "plaintext"]

CLIENT_CAPABILITIES: dict[str, JsonValue] = {
    "general": {"positionEncodings": ["utf-16"]},
    "textDocument": {
        "synchronization": {"dynamicRegistration": False, "didSave": True},
        "publishDiagnostics": {"tagSupport": {"valueSet": [1, 2]}, "relatedInformation": False},
        "hover": {"contentFormat": _DOCUMENTATION_FORMATS},
        "definition": {"linkSupport": True},
        "completion": {
            "contextSupport": True,
            "completionItem": {
                "snippetSupport": False,
                "documentationFormat": _DOCUMENTATION_FORMATS,
                "resolveSupport": {"properties": ["documentation", "detail"]},
                "labelDetailsSupport": True,
            },
        },
        "signatureHelp": {
            "contextSupport": True,
            "signatureInformation": {
                "documentationFormat": _DOCUMENTATION_FORMATS,
                "parameterInformation": {"labelOffsetSupport": True},
                "activeParameterSupport": True,
            },
        },
    },
    "workspace": {
        "configuration": True,
        "workspaceFolders": True,
        "didChangeWatchedFiles": {"dynamicRegistration": True},
    },
    "window": {"workDoneProgress": False},
}
"""What the broker implements (docs/specs/web-ui.md#the-broker): the same for every server. Every
session declares completion and signature help, whatever the `autocomplete` preference says, and
no snippet support, so an item never leaves placeholders to step through."""


def _no_options(_workspace: str) -> dict[str, JsonValue]:
    return {}


def _typescript_options(workspace: str) -> dict[str, JsonValue]:
    """The compiler that `--typecheck` runs, no typings fetched from npm (NFR-6), and no
    completion that adds an import: adding one is a quick fix, which is out of scope."""
    return {
        "tsserver": {"path": f"{workspace}/{TYPESCRIPT_PROJECT}/node_modules/typescript/lib"},
        "disableAutomaticTypingAcquisition": True,
        "preferences": {"includeCompletionsForModuleExports": False},
    }


TSSERVER_SCRIPT = f"{TYPESCRIPT_PROJECT}/node_modules/typescript/lib/tsserver.js"

BASEDPYRIGHT = LanguageServer(
    language=Language.PYTHON,
    name="basedpyright",
    version="1.40.2",
    script="node_modules/basedpyright/langserver.index.js",
    version_script="node_modules/basedpyright/index.js",
    root_project=PYTHON_PROJECT,
    initialization_options=_no_options,
    settings={
        "basedpyright": {
            "analysis": {
                "autoImportCompletions": False,
                "typeCheckingMode": "standard",
            }
        }
    },
    capabilities=CLIENT_CAPABILITIES,
)

TYPESCRIPT_LANGUAGE_SERVER = LanguageServer(
    language=Language.TYPESCRIPT,
    name="typescript-language-server",
    version="6.0.3",
    script="node_modules/typescript-language-server/lib/cli.mjs",
    version_script="node_modules/typescript-language-server/lib/cli.mjs",
    root_project=TYPESCRIPT_PROJECT,
    initialization_options=_typescript_options,
    settings={},
    capabilities=CLIENT_CAPABILITIES,
    requirement=Requirement(TSSERVER_SCRIPT, f"{TYPESCRIPT_PROJECT}/node_modules missing"),
)

LANGUAGE_SERVERS = (BASEDPYRIGHT, TYPESCRIPT_LANGUAGE_SERVER)
"""The languages with a server in slice 1; Go, Rust, Java and Kotlin have none yet. A tuple, not a
table keyed by `Language`, since a table must have a row for every language."""


def server_for(language: Language) -> LanguageServer | None:
    return next((server for server in LANGUAGE_SERVERS if server.language is language), None)
