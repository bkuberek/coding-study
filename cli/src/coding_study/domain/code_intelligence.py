"""The catalog of language servers behind the web UI's code intelligence
(docs/specs/web-ui.md#language-servers, ADR 0018).

Paths are POSIX strings: relative to the workspace root, or to `.cs/lsp/` where the field says so.
Commands take the absolute directories they run with (`Launch`), so no path type is needed here.
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from coding_study.domain.cases import JsonValue
from coding_study.domain.jdk import JdkRange
from coding_study.domain.layout import JVM_PROJECT, PYTHON_PROJECT, TYPESCRIPT_PROJECT
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.service_project import service_of

LSP_DIRECTORY = ".cs/lsp"
"""The pnpm project that cstudy owns in the workspace, ignored by git, with the servers that are
downloaded as archives beside it."""
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
class Archive:
    """A server that is no npm package: one archive, downloaded by `cstudy doctor --fix` and
    checked by its SHA-256 before it is unpacked."""

    url: str
    sha256: str
    directory: str
    """Where it is unpacked, relative to `.cs/lsp/`."""


@dataclass(frozen=True, slots=True)
class Launch:
    """What a session's command names: absolute POSIX paths, and the platform it runs on."""

    lsp_directory: str
    data_directory: str | None = None
    """The session's own directory under `.cs/lsp/`, for a server that keeps data (`data`)."""
    java: str | None = None
    """The `java` of the selected JDK, for a server that runs on a JDK (`jdks`)."""
    platform: str = ""
    """As Python's `sys.platform` spells it: `darwin`, `linux`, `win32`."""


def node_command(server: "LanguageServer", launch: Launch) -> tuple[str, ...]:
    return (NODE, f"{launch.lsp_directory}/{server.script}", "--stdio")


def _no_environment(_launch: Launch) -> dict[str, str]:
    return {}


@dataclass(frozen=True, slots=True)
class LanguageServer:
    language: Language
    name: str
    version: str
    """The pinned version: `package.json` and `pnpm-lock.yaml` name the same one, or the archive."""
    script: str
    """What counts as the server being installed, relative to `.cs/lsp/`: the `bin` script the
    package's `package.json` names for the server, never a `.bin/` shim; for an archive, a file
    whose name holds the pinned build."""
    version_script: str | None
    """The script whose `--version` prints the version, relative to `.cs/lsp/`; None for an
    archive, whose `script` already pins the version."""
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
    launcher: Callable[["LanguageServer", Launch], tuple[str, ...]] = node_command
    """The command that starts the server, without a shell."""
    environment: Callable[[Launch], dict[str, str]] = _no_environment
    """Variables the server starts with, on top of what `cstudy serve` lets user code inherit."""
    archive: Archive | None = None
    """Set for a server downloaded as an archive rather than installed with pnpm."""
    jdks: JdkRange | None = None
    """The JDKs it runs on, for a server that is a Java program: it runs on the selected one."""
    data: str | None = None
    """The directory under `.cs/lsp/` that keeps a data directory per root and session."""
    data_files: Mapping[str, str] = field(default_factory=dict[str, str])
    """Files written into a session's data directory before the server starts, by their path in
    it."""

    def command(self, launch: Launch) -> tuple[str, ...]:
        return self.launcher(self, launch)

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

JDTLS_DIRECTORY = "jdtls"
JDTLS_PLUGINS = f"{JDTLS_DIRECTORY}/plugins"
JDTLS_LAUNCHER = f"{JDTLS_PLUGINS}/org.eclipse.equinox.launcher_1.8.0.v20260804-1928.jar"
JDTLS_HEAP = "-Xmx1g"
"""A Gradle import and the JDK's index stay under it: the spike measured 0.5 to 1.2 GB resident."""
JDTLS_JVM_OPTIONS = (
    "-Declipse.application=org.eclipse.jdt.ls.core.id1",
    "-Dosgi.bundles.defaultStartLevel=4",
    "-Declipse.product=org.eclipse.jdt.ls.core.product",
    "-Dosgi.checkConfiguration=true",
    "-Dosgi.sharedConfiguration.area.readOnly=true",
    "-Dosgi.configuration.cascaded=true",
    "-Djava.import.generatesMetadataFilesAtProjectRoot=false",
    "-Djdk.xml.maxGeneralEntitySizeLimit=0",
    "-Djdk.xml.totalEntitySizeLimit=0",
    JDTLS_HEAP,
    "-XX:+UseSerialGC",
    "--add-modules=ALL-SYSTEM",
    "--add-opens",
    "java.base/java.util=ALL-UNNAMED",
    "--add-opens",
    "java.base/java.lang=ALL-UNNAMED",
)
"""What the milestone's own `bin/jdtls.py` passes on a JDK from 24 on, with the heap capped, the
serial collector, and the Eclipse files of each project (`.project`, `.classpath`, `.settings/`)
kept in the data directory instead of the project's folders: the property is read when the server
starts, so it cannot be a setting."""
JDTLS_CONFIGURATIONS: Mapping[str, str] = {
    "darwin": "config_mac",
    "linux": "config_linux",
    "win32": "config_win",
}
"""The archive's read-only configuration for each platform, as `bin/jdtls.py` picks it."""
JVM_WRAPPER_SHA256 = "3b8a25775a69158b5ad2b1d17a80a88dc7b40a352a73eb27d06c612a7ce68e98"
"""The Gradle wrapper that the workspace's `jvm/` ships (`gradle/wrapper/gradle-wrapper.jar`)."""
CACHE_DIRECTORY = "cache"
"""In a session's data directory: where JDT LS keeps what it would keep in `~/.cache`."""
GRADLE_VERSIONS = f"{CACHE_DIRECTORY}/tooling/gradle/versions.json"
"""The Gradle versions whose wrapper checksums JDT LS downloads to validate a root's wrapper."""


def _jdtls_command(server: LanguageServer, launch: Launch) -> tuple[str, ...]:
    lsp = launch.lsp_directory
    configuration = JDTLS_CONFIGURATIONS.get(launch.platform, JDTLS_CONFIGURATIONS["linux"])
    return (
        launch.java or "java",
        *JDTLS_JVM_OPTIONS,
        f"-Dosgi.sharedConfiguration.area={lsp}/{JDTLS_DIRECTORY}/{configuration}",
        "-jar",
        f"{lsp}/{JDTLS_LAUNCHER}",
        "-configuration",
        f"{launch.data_directory}/configuration",
        "-data",
        f"{launch.data_directory}/workspace",
    )


def _jdtls_environment(launch: Launch) -> dict[str, str]:
    """JDT LS keeps Gradle's wrapper checksums under `$XDG_CACHE_HOME`, or `~/.cache`: the
    session's data directory keeps them inside the workspace."""
    return {"XDG_CACHE_HOME": f"{launch.data_directory}/{CACHE_DIRECTORY}"}


_JDTLS_SETTINGS: dict[str, JsonValue] = {
    "java": {
        "import": {
            "gradle": {
                "enabled": True,
                "offline": {"enabled": True},
                "wrapper": {"enabled": True},
            },
            "maven": {"enabled": False},
            "generatesMetadataFilesAtProjectRoot": False,
        },
        "imports": {
            "gradle": {"wrapper": {"checksums": [{"sha256": JVM_WRAPPER_SHA256, "allowed": True}]}}
        },
        "configuration": {"updateBuildConfiguration": "automatic"},
        "autobuild": {"enabled": False},
        "maven": {"downloadSources": False},
        "eclipse": {"downloadSources": False},
        "signatureHelp": {"enabled": True},
        "format": {"enabled": False},
    }
}
"""Gradle offline over what `cstudy doctor --fix` warmed up, no Maven import, the workspace's own
wrapper trusted, and no build: the open documents are checked as they change, and no class file is
written into the projects' folders."""


def _jdtls_options(_workspace: str) -> dict[str, JsonValue]:
    """The settings, which JDT LS reads from here rather than asking for them, and `jdt://` URIs
    for the classes of the JDK and of the libraries, which a definition then names."""
    return {
        "settings": _JDTLS_SETTINGS,
        "extendedClientCapabilities": {"classFileContentsSupport": True},
        "bundles": [],
    }


JDTLS = LanguageServer(
    language=Language.JAVA,
    name="jdtls",
    version="1.63.0",
    script=f"{JDTLS_PLUGINS}/org.eclipse.jdt.ls.core_1.63.0.202610191322.jar",
    version_script=None,
    root_project=JVM_PROJECT,
    initialization_options=_jdtls_options,
    settings=_JDTLS_SETTINGS,
    capabilities=CLIENT_CAPABILITIES,
    idle_s=300,
    launcher=_jdtls_command,
    environment=_jdtls_environment,
    archive=Archive(
        url=(
            "https://download.eclipse.org/jdtls/milestones/1.63.0/"
            "jdt-language-server-1.63.0-202610191322.tar.gz"
        ),
        sha256="b1f2abe0b3cccb462cf64fb4a5587c7d09df60cf8be7748b152cbd89d018bdc4",
        directory=JDTLS_DIRECTORY,
    ),
    jdks=JdkRange(25, 26),
    data="jdtls-data",
    data_files={GRADLE_VERSIONS: "[]"},
)
"""Eclipse JDT LS, a milestone (ADR 0018, phase 2). An empty list of Gradle versions leaves JDT LS
the checksums it ships and the one the settings trust, so it downloads none."""

LANGUAGE_SERVERS = (BASEDPYRIGHT, TYPESCRIPT_LANGUAGE_SERVER, JDTLS)
"""The languages with a server in phase 2; Go, Rust and Kotlin have none yet. A tuple, not a table
keyed by `Language`, since a table must have a row for every language."""


def server_for(language: Language) -> LanguageServer | None:
    return next((server for server in LANGUAGE_SERVERS if server.language is language), None)


class NoCodeIntelligence(StrEnum):
    """Why an attempt has no code intelligence whatever its language's server."""

    SERVICE_PROJECT = "service_project"
    """Sandboxed code writes the folder, and a server on this machine would read it, until one runs
    in a container (docs/specs/service-projects.md#language-servers)."""


def no_code_intelligence(meta: ProblemMeta) -> NoCodeIntelligence | None:
    return NoCodeIntelligence.SERVICE_PROJECT if service_of(meta) is not None else None
