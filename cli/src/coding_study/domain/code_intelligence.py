"""The catalog of language servers behind the web UI's code intelligence
(docs/specs/web-ui.md#language-servers, ADR 0018).

Paths are POSIX strings: relative to the workspace root, or to `.cs/lsp/` where the field says so.
Commands take the absolute directories they run with (`Launch`), so no path type is needed here.
"""

import hashlib
import re
import shlex
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from functools import partial

from coding_study.domain.cases import JsonValue
from coding_study.domain.jdk import SUPPORTED_JDKS, JdkRange
from coding_study.domain.layout import (
    GO_PROJECT,
    JVM_PROJECT,
    PYTHON_PROJECT,
    RUST_PROJECT,
    TYPESCRIPT_PROJECT,
)
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta, Track
from coding_study.domain.sandbox import (
    CACHE_DIRECTORY as INSTALL_CACHE,
)
from coding_study.domain.sandbox import (
    GRADLE_GLIBC_IMAGE,
    IMAGE_GRADLE_HOME,
    JVM_SIDECAR_MEMORY,
    JVM_SIDECAR_PIDS,
    NODE_IMAGE,
    SidecarToolchain,
)
from coding_study.domain.server_builds import Build, License, Releases
from coding_study.domain.service_project import ServiceProject, service_of

LSP_DIRECTORY = ".cs/lsp"
"""The pnpm project that cstudy owns in the workspace, ignored by git, with the servers that are
downloaded as archives beside it."""
LSP_INSTALL_COMMAND = ("pnpm", "install", "--frozen-lockfile", "--ignore-scripts")
"""Run in `LSP_DIRECTORY`: the lock pins every version with its integrity hash, and no package
script runs."""
NOT_AVAILABLE_YET = "not available yet"
NODE = "node"
NO_ADDONS = "--no-addons"
"""Node refuses native addons. A version check needs none, and basedpyright's file watcher loads
`fsevents.node` on macOS, a binary each install of `LSP_DIRECTORY` writes anew: macOS scans it on
its first load and the load waits, for seconds, or for minutes on a busy machine."""
IDLE_SECONDS = 60
"""How long the page keeps a session whose files are all closed."""
SIDECAR_PLATFORM = "linux"
"""What a sidecar runs on, whatever this machine is: JDT LS takes the archive's `config_linux`,
and the Kotlin LSP's sidecar runs its Linux build."""
WARM_IDLE_S = 600
"""How long a server that `cstudy serve` started ahead of time waits for an editor to take it over
before it stops: about ten minutes (docs/specs/web-ui.md#warm-up)."""

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
    into: str = ""
    """A directory of `directory` the build goes into."""
    strip: str = ""
    """The archive's top directory, which holds the build; empty for one that holds it at its
    top."""


@dataclass(frozen=True, slots=True)
class Warmup:
    """A run of the server that `cstudy doctor --fix` makes on each of `roots`, online, after the
    JVM warm-up: its import fills Gradle's cache with what the server reads later, offline, such
    as the sources of the build's libraries."""

    script: str
    """The vendor's script that runs the server until its index is built, relative to
    `.cs/lsp/`; it takes the root, an index directory and the server's launcher."""
    roots: tuple[str, ...]
    """Relative to the workspace root."""
    timeout_s: int = 900


_PROCESSORS: Mapping[str, str] = {
    "arm64": "arm64",
    "aarch64": "arm64",
    "x86_64": "x64",
    "amd64": "x64",
}


def machine_of(platform: str, processor: str) -> str:
    """`darwin-arm64`, `linux-x64`, `win32-x64`: the platform as `sys.platform` spells it and the
    processor as `platform.machine()` does, which says `aarch64` on Linux and `AMD64` on
    Windows."""
    return f"{platform}-{_PROCESSORS.get(processor.lower(), processor.lower())}"


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
    java_home: str | None = None
    """The selected JDK's home, for a server that builds with a JDK (`jdks`)."""


LSP_BIN = "bin"
"""Where `go install` puts the servers that Go builds, relative to `.cs/lsp/`."""
_GO_RELEASE = re.compile(r"go(\d+\.\d+(?:\.\d+)?)")


@dataclass(frozen=True, slots=True)
class GoInstall:
    """A server that `cstudy doctor --fix` builds with `go install` into `.cs/lsp/bin/`, at the
    version the selected Go pins: each release of it builds only with Go from some release on."""

    module: str
    versions: Mapping[int, str]
    """The version for each minor release of Go 1."""

    def version_for(self, go: str | None) -> str:
        """The version pinned for the Go whose release is `go` (`1.27.3`): its minor release's;
        the newest for a Go newer than the table, or for none; the oldest for an older one."""
        newest = max(self.versions)
        minor = None if go is None else int(go.split(".")[1])
        if minor is None or minor > newest:
            return self.versions[newest]
        return self.versions[max(minor, min(self.versions))]

    def command(self, version: str) -> tuple[str, ...]:
        return ("go", "install", f"{self.module}@v{version}")

    def environment(self, lsp_directory: str) -> dict[str, str]:
        """The binary goes to `.cs/lsp/bin/`; the selected Go builds it and never downloads
        another (`GOTOOLCHAIN=local`), and the workspace's `go.work` stays out of the build."""
        return {
            "GOBIN": f"{lsp_directory}/{LSP_BIN}",
            "GOTOOLCHAIN": "local",
            "GOWORK": "off",
        }


@dataclass(frozen=True, slots=True)
class StandardLibrary:
    """A standard library a server reads from links cstudy makes, in `.cs/lsp/<links>/<root>/`:
    one to each entry of the toolchain's library sources but its Cargo manifest and lock.
    rust-analyzer runs `cargo metadata` on the library's own Cargo workspace when it has a
    manifest, and cargo applies the workspace's `.cargo/config.toml` to that query too: the
    vendored crates.io holds none of `std`'s dependencies, so the query fails and `Vec` or `len`
    resolve to nothing. Without a manifest, rust-analyzer reads the library's crates directly."""

    section: str
    """The settings section where the links go, as `cargo.sysrootSrc`."""
    links: str = "rust-library"
    """Under `.cs/lsp/`, then the session's root."""
    sysroot_command: tuple[str, ...] = ("rustc", "--print", "sysroot")
    """Prints the sysroot of the toolchain the root selects, run in the root."""
    library: str = "lib/rustlib/src/rust/library"
    """The library sources, relative to the sysroot: rustup's `rust-src` component."""
    left_out: frozenset[str] = frozenset({"Cargo.toml", "Cargo.lock"})

    def settings(self, settings: Mapping[str, JsonValue], directory: str) -> dict[str, JsonValue]:
        """`settings` with the links in `directory` as `cargo.sysrootSrc` of the section."""
        section = _fields(settings.get(self.section))
        cargo = {**_fields(section.get("cargo")), "sysrootSrc": directory}
        return {**settings, self.section: {**section, "cargo": cargo}}


def _fields(value: JsonValue | None) -> dict[str, JsonValue]:
    return dict(value) if isinstance(value, dict) else {}


GO_RELEASE_COMMAND = ("go", "env", "GOVERSION")
"""Prints the selected Go's release, `go1.27.3`."""


def go_release(printed: str) -> str | None:
    """The release of Go in what `go env GOVERSION` or `go version` printed; None if none."""
    found = _GO_RELEASE.search(printed)
    return found[1] if found else None


def node_command(server: "LanguageServer", launch: Launch) -> tuple[str, ...]:
    return (NODE, f"{launch.lsp_directory}/{server.script}", "--stdio")


def node_version_command(server: "LanguageServer", lsp_directory: str) -> tuple[str, ...]:
    return (NODE, NO_ADDONS, f"{lsp_directory}/{server.version_script}", "--version")


def _no_environment(_launch: Launch) -> dict[str, str]:
    return {}


@dataclass(frozen=True, slots=True)
class LanguageServer:
    language: Language
    name: str
    version: str | None
    """The pinned version: `package.json` and `pnpm-lock.yaml` name the same one, or the archive;
    for a server that Go builds, the newest its table pins. None for a server cstudy does not
    install, which is whichever version runs."""
    script: str | None
    """What counts as the server being installed, relative to `.cs/lsp/`: the `bin` script the
    package's `package.json` names for the server, never a `.bin/` shim; for an archive, a file
    whose name holds the pinned build; for a server that Go builds, its binary. None for a server
    found on PATH, which its version command alone finds."""
    version_script: str | None
    """The script whose `--version` prints the version, relative to `.cs/lsp/`, for a Node
    server; None otherwise."""
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
    """The JDKs it needs, for a server that is a Java program or imports a Gradle build: JDT LS
    runs on the selected one, the Kotlin LSP imports with it."""
    data: str | None = None
    """The directory under `.cs/lsp/` that keeps a data directory per root and session."""
    data_files: Mapping[str, str] = field(default_factory=dict[str, str])
    """Files written into a session's data directory before the server starts, by their path in
    it."""
    versioner: Callable[["LanguageServer", str], tuple[str, ...]] = node_version_command
    """The command that prints the version, given the absolute `.cs/lsp/`; not run for an
    archive, whose `script` already pins the version."""
    go_install: GoInstall | None = None
    """Set for a server that `go install` builds at the version the selected Go pins."""
    fix: str | None = None
    """What installs a server that cstudy does not install, as the doctor row names it; None for
    one that `cstudy doctor --fix` installs."""
    missing_words: str | None = None
    """Words a failing version command prints when only a proxy of the server is there, such as
    the rustup proxy of a component that is not installed."""
    standard_library: StandardLibrary | None = None
    """Set for a server that reads the standard library from links cstudy makes."""
    license: License | None = None
    """Set for a server whose vendor asks you to accept a license before it is downloaded."""
    warmup: Warmup | None = None
    """Set for a server whose sessions read what an online import fetches."""
    linux_build: bool = False
    """Set for a build that `cstudy doctor --fix` fetches for Linux on this machine's processor,
    which a sidecar runs, rather than for this machine; it never runs on this machine."""
    releases: Releases | None = None
    """Set for a server whose newest build `cstudy doctor --fix` fetches rather than pins."""

    def command(self, launch: Launch) -> tuple[str, ...]:
        return self.launcher(self, launch)

    def warm_up_command(self, launch: Launch, python: str, root: str) -> tuple[str, ...]:
        """The command that warms the server up on the absolute `root`, with its index in
        `launch`'s data directory, under the Python at `python`; empty without a warm-up."""
        warmup = self.warmup
        if warmup is None:
            return ()
        return (
            python,
            "-I",
            f"{launch.lsp_directory}/{warmup.script}",
            root,
            f"{launch.data_directory}/system",
            "--server",
            self.command(launch)[0],
            "--build-tool",
            "gradle",
            "--timeout",
            str(warmup.timeout_s),
        )

    def version_command(self, lsp_directory: str) -> tuple[str, ...]:
        return self.versioner(self, lsp_directory)

    def says_missing(self, output: str) -> bool:
        """Whether a failing version command's output means the server is not installed."""
        return self.missing_words is not None and self.missing_words in output

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
        "diagnostic": {"dynamicRegistration": False, "relatedDocumentSupport": False},
    },
    "workspace": {
        "configuration": True,
        "workspaceFolders": True,
        "didChangeWatchedFiles": {"dynamicRegistration": True},
        "diagnostics": {"refreshSupport": True},
    },
    "window": {"workDoneProgress": False},
}
"""What the broker implements (docs/specs/web-ui.md#the-broker): the same for every server. Every
session declares completion and signature help, whatever the `autocomplete` preference says, and
no snippet support, so an item never leaves placeholders to step through. Pull diagnostics are
declared without dynamic registration: basedpyright pulls only for a client that registers them
dynamically, so it keeps publishing, while a server that answers `textDocument/diagnostic`
(rust-analyzer for its own diagnostics) is asked, and tells the page to ask again through
`workspace/diagnostic/refresh`."""


def _no_options(_workspace: str) -> dict[str, JsonValue]:
    return {}


def _typescript_options(workspace: str) -> dict[str, JsonValue]:
    """The compiler that `--typecheck` runs, no typings fetched from npm (NFR-6), and no
    completion that adds an import: adding one is a quick fix, which is out of scope."""
    return _compiler_options(f"{workspace}/{TYPESCRIPT_PROJECT}", workspace)


def _compiler_options(project: str, _workspace: str) -> dict[str, JsonValue]:
    """The options of a session whose compiler is the one installed in `project`."""
    return {
        "tsserver": {"path": f"{project}/node_modules/typescript/lib"},
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

KOTLIN_LSP_DIRECTORY = "kotlin-lsp"
KOTLIN_LSP_HOME = f"{KOTLIN_LSP_DIRECTORY}/server"
"""Where the build `cstudy doctor --fix` fetched lives, whatever its version, so a newer one takes
its place."""
KOTLIN_LSP_RECORD = f"{KOTLIN_LSP_DIRECTORY}/installed.json"
"""What `--fix` writes once the build is in place: its version, the last day it runs, the license
it came under and where it came from (`InstalledBuild`)."""
KOTLIN_LSP_BUILD = "server"
"""This machine's build, in `kotlin-lsp/`."""
KOTLIN_LSP_LINUX_BUILD = "linux"
"""The Linux build for this machine's processor, beside it, which Kotlin service projects' sidecars
run: this machine's build cannot run in a Linux container."""
KOTLIN_LSP_LINUX_HOME = f"{KOTLIN_LSP_DIRECTORY}/{KOTLIN_LSP_LINUX_BUILD}"
KOTLIN_LSP_LINUX_RECORD = f"{KOTLIN_LSP_DIRECTORY}/{KOTLIN_LSP_LINUX_BUILD}.json"
KOTLIN_LSP_LICENSE = License(
    key="kotlin-lsp",
    name="JetBrains Free Plugin License Agreement 1.0",
    url="https://github.com/Kotlin/kotlin-lsp/blob/main/kotlin-vscode/LICENSE.txt",
    summary="partly closed source, from JetBrains",
)
"""The Kotlin LSP is partly closed source: JetBrains ships it with VS Code under this agreement,
and its standalone archive carries no license of its own (ADR 0018, Kotlin revisited). `--fix`
reads the agreement at each release's tag: another title or version is another license, which
you accept again."""
KOTLIN_LSP_RELEASES = Releases(
    api_url="https://api.github.com/repos/Kotlin/kotlin-lsp/releases",
    asset=(
        r"https://download\.jetbrains\.com/language-server/kotlin-server/"
        r"(?P<version>\d+(?:\.\d+)+)/kotlin-server-(?P=version){suffix}"
    ),
    suffixes={
        "darwin-arm64": "-aarch64.sit",
        "darwin-x64": ".sit",
        "linux-x64": ".tar.gz",
        "linux-arm64": "-aarch64.tar.gz",
        "win32-x64": ".win.zip",
        "win32-arm64": "-aarch64.win.zip",
    },
    license_url="https://raw.githubusercontent.com/Kotlin/kotlin-lsp/{tag}/kotlin-vscode/LICENSE.txt",
    top_directory="kotlin-server-{version}",
)
"""JetBrains' releases of the Kotlin LSP on GitHub, whose notes link a standalone archive per
machine on `download.jetbrains.com` and its `.sha256` file beside it. The macOS archives are zips
despite their `.sit` name; the Windows ones hold no top directory."""
KOTLIN_LSP_JVM_OPTIONS = ("-Xmx1g", "-XX:+UseSerialGC", "-XX:ReservedCodeCacheSize=240m")
"""Its launcher reads `bin/intellij-server.vmoptions` (2 GB of heap, 512 MB of code cache) and then
`IJ_JAVA_OPTIONS`, so these win: the spike measured MaxHeapSize at 1 GB with them."""
EXPIRY_WARNING_DAYS = 7
"""How many days before an early-access build stops the doctor row warns."""


def build_archive(build: Build, sha256: str, machine: str, into: str = KOTLIN_LSP_BUILD) -> Archive:
    """The archive of a fetched build, unpacked into `kotlin-lsp/<into>/`, `server/` for this
    machine's: the Windows archives hold the build at their top, the others in
    `kotlin-server-<version>/`."""
    releases = KOTLIN_LSP_RELEASES
    flat = machine.startswith("win32")
    top = "" if flat else releases.top_directory.format(version=build.version)
    return Archive(build.url, sha256, KOTLIN_LSP_DIRECTORY, into=into, strip=top)


def build_place(server: "LanguageServer") -> str:
    """Where in `kotlin-lsp/` a fetched build of `server` goes."""
    return KOTLIN_LSP_LINUX_BUILD if server.linux_build else KOTLIN_LSP_BUILD


def sidecar_machine(processor: str) -> str:
    """The machine a sidecar runs on: Linux on this machine's processor, as Docker runs images."""
    return machine_of(SIDECAR_PLATFORM, processor)


def _kotlin_lsp_launcher(platform: str) -> str:
    executable = "intellij-server.exe" if platform == "win32" else "intellij-server"
    return f"{KOTLIN_LSP_HOME}/bin/{executable}"


def _kotlin_lsp_command(server: LanguageServer, launch: Launch) -> tuple[str, ...]:
    return (
        f"{launch.lsp_directory}/{_kotlin_lsp_launcher(launch.platform)}",
        "--stdio",
        f"--system-path={launch.data_directory}/system",
    )


def _kotlin_lsp_linux_command(_server: LanguageServer, launch: Launch) -> tuple[str, ...]:
    return (
        f"{launch.lsp_directory}/{KOTLIN_LSP_LINUX_HOME}/bin/intellij-server",
        "--stdio",
        f"--system-path={launch.data_directory}/system",
    )


def _kotlin_lsp_linux_environment(launch: Launch) -> dict[str, str]:
    """As this machine's build, with Gradle's user home in the sidecar's data folder, where the
    import finds the image's Gradle as its tooling API's own distribution, and the build's other
    homes there too: the shared data folder it creates at startup (`$XDG_DATA_HOME/JetBrains`), its
    license store (`$XDG_CONFIG_HOME/JetBrains/IntelliJServer`) and its index databases, which go
    under `$XDG_CACHE_HOME/JetBrains/IntelliJServer/workspaces/` rather than the system path. The
    image's `~/.local`, `~/.config` and `~/.cache`, which it uses otherwise, are read-only in a
    sidecar."""
    data = launch.data_directory
    options = _kotlin_lsp_environment(launch)["IJ_JAVA_OPTIONS"]
    home = f"-Dcom.jetbrains.ls.imports.gradle.gradleUserHome={data}/gradle"
    return {
        "IJ_JAVA_OPTIONS": f"{options} {home}",
        "XDG_DATA_HOME": f"{data}/share",
        "XDG_CONFIG_HOME": f"{data}/config",
        "XDG_CACHE_HOME": f"{data}/cache",
    }


def _kotlin_lsp_environment(launch: Launch) -> dict[str, str]:
    """Its configuration, logs and plugins in the session's data directory beside its index, no
    update check (which would reach JetBrains), and the Gradle import on the selected JDK, as every
    Gradle call of cstudy runs. The launcher splits the variable as a shell does."""
    data = launch.data_directory
    options = [
        *KOTLIN_LSP_JVM_OPTIONS,
        f"-Didea.config.path={data}/config",
        f"-Didea.log.path={data}/log",
        f"-Didea.plugins.path={data}/plugins",
        "-Dintellij.updates.enabled=false",
    ]
    if launch.java_home is not None:
        options.append(f"-Dcom.jetbrains.ls.imports.gradle.java.home={launch.java_home}")
    return {"IJ_JAVA_OPTIONS": shlex.join(options)}


KOTLIN_LSP = LanguageServer(
    language=Language.KOTLIN,
    name="kotlin-lsp",
    version=None,
    script=KOTLIN_LSP_RECORD,
    version_script=None,
    root_project=JVM_PROJECT,
    initialization_options=_no_options,
    settings={},
    capabilities=CLIENT_CAPABILITIES,
    idle_s=300,
    launcher=_kotlin_lsp_command,
    environment=_kotlin_lsp_environment,
    jdks=SUPPORTED_JDKS,
    data="kotlin-lsp-data",
    license=KOTLIN_LSP_LICENSE,
    warmup=Warmup(script=f"{KOTLIN_LSP_HOME}/bin/warmup.py", roots=(JVM_PROJECT,)),
    releases=KOTLIN_LSP_RELEASES,
)
"""JetBrains' Kotlin LSP (ADR 0018, Kotlin revisited): IntelliJ IDEA's analysis behind LSP, with
its own runtime. It answers diagnostics only when asked (`textDocument/diagnostic`) and asks for
a refresh as its import and index progress. It reads the sources of the build's libraries from
Gradle's cache, which `cstudy doctor --fix` fills by warming it up once online. cstudy pins no
build: `--fix` fetches JetBrains' newest, checked by the SHA-256 JetBrains publishes beside it,
since each early-access build stops about a month after its release."""

KOTLIN_LSP_LINUX = replace(
    KOTLIN_LSP,
    name="kotlin-lsp-linux",
    script=KOTLIN_LSP_LINUX_RECORD,
    launcher=_kotlin_lsp_linux_command,
    environment=_kotlin_lsp_linux_environment,
    jdks=None,
    data=None,
    warmup=None,
    linux_build=True,
)
"""The Kotlin LSP as a Kotlin service project's sidecar runs it: JetBrains' Linux build for this
machine's processor, which `cstudy doctor --fix` fetches beside this machine's once a Kotlin service
project is installed, with its own runtime, on `GRADLE_GLIBC_IMAGE`, importing with the image's JDK.
Never run on this machine, nor warmed up: the import reads the install cache."""

SIDECAR_BUILDS = (KOTLIN_LSP_LINUX,)
"""The builds that `cstudy doctor --fix` fetches for a sidecar beside this machine's, once a
service project of their language is installed."""

GOPLS_SETTINGS: dict[str, JsonValue] = {"linksInHover": False, "completeUnimported": False}
"""No web links on hover, and no completion of a package that is not imported, which adds its
import: a quick fix, out of scope. The links inside the documentation are `file:` links into
GOROOT, which the page opens as library files."""


def _gopls_command(server: LanguageServer, launch: Launch) -> tuple[str, ...]:
    return (f"{launch.lsp_directory}/{server.script}",)


def _gopls_version_command(server: LanguageServer, lsp_directory: str) -> tuple[str, ...]:
    return (f"{lsp_directory}/{server.script}", "version")


def _gopls_options(_workspace: str) -> dict[str, JsonValue]:
    return dict(GOPLS_SETTINGS)


def _gopls_environment(_launch: Launch) -> dict[str, str]:
    """The `go` commands gopls runs load packages as cstudy's builds do: with the selected Go,
    no module or toolchain downloaded, the module files left as they are and no cgo."""
    return {
        "GOTOOLCHAIN": "local",
        "GOPROXY": "off",
        "GOFLAGS": "-mod=readonly",
        "CGO_ENABLED": "0",
    }


GOPLS = LanguageServer(
    language=Language.GO,
    name="gopls",
    version="0.24.0",
    script=f"{LSP_BIN}/gopls",
    version_script=None,
    root_project=GO_PROJECT,
    initialization_options=_gopls_options,
    settings={"gopls": GOPLS_SETTINGS},
    capabilities=CLIENT_CAPABILITIES,
    launcher=_gopls_command,
    environment=_gopls_environment,
    versioner=_gopls_version_command,
    go_install=GoInstall(
        module="golang.org/x/tools/gopls",
        versions={25: "0.21.1", 26: "0.23.0", 27: "0.24.0"},
    ),
)
"""gopls (ADR 0018, phase 3): `go install` builds the version the selected Go pins into
`.cs/lsp/bin/`, online once. Its root is `go/`, which it finds through the workspace's `go.work`,
or a project folder, through the folder's own."""

RUST_ANALYZER_SETTINGS: dict[str, JsonValue] = {
    "cargo": {"targetDir": True},
    "check": {"allTargets": True},
    "completion": {"autoimport": {"enable": False}},
}
"""`cargo check` over every target into `target/rust-analyzer/`, a target directory of its own,
so it never waits for an IDE's `cargo check`; no `--keep-going` of cstudy's, since rust-analyzer
passes it itself; and no completion that adds an import, a quick fix, out of scope."""


def _rust_analyzer_command(_server: LanguageServer, _launch: Launch) -> tuple[str, ...]:
    return (RUST_ANALYZER_NAME,)


def _rust_analyzer_version_command(_server: LanguageServer, _lsp: str) -> tuple[str, ...]:
    return (RUST_ANALYZER_NAME, "--version")


def _rust_analyzer_options(_workspace: str) -> dict[str, JsonValue]:
    return dict(RUST_ANALYZER_SETTINGS)


def _rust_analyzer_environment(_launch: Launch) -> dict[str, str]:
    """`cargo metadata` and `cargo check` run offline, over the vendored crates."""
    return {"CARGO_NET_OFFLINE": "true"}


RUST_ANALYZER_NAME = "rust-analyzer"
RUST_ANALYZER = LanguageServer(
    language=Language.RUST,
    name=RUST_ANALYZER_NAME,
    version=None,
    script=None,
    version_script=None,
    root_project=RUST_PROJECT,
    initialization_options=_rust_analyzer_options,
    settings={RUST_ANALYZER_NAME: RUST_ANALYZER_SETTINGS},
    capabilities=CLIENT_CAPABILITIES,
    launcher=_rust_analyzer_command,
    environment=_rust_analyzer_environment,
    versioner=_rust_analyzer_version_command,
    fix=f"rustup component add {RUST_ANALYZER_NAME}",
    missing_words="Unknown binary",
    standard_library=StandardLibrary(section=RUST_ANALYZER_NAME),
)
"""rust-analyzer (ADR 0018, phase 3): the one rustup installs, or any on PATH whose `--version`
runs. cstudy never changes the Rust toolchain. While the component is missing, rustup's proxy on
PATH answers `error: Unknown binary 'rust-analyzer' in official toolchain …`, which counts as not
installed. It runs build scripts and procedural macros, as `cargo test` does."""

LANGUAGE_SERVERS = (
    BASEDPYRIGHT,
    TYPESCRIPT_LANGUAGE_SERVER,
    JDTLS,
    KOTLIN_LSP,
    GOPLS,
    RUST_ANALYZER,
)
"""Every language has a server since Kotlin's. A tuple, not a table keyed by `Language`, since a
table must have a row for every language."""


def server_for(language: Language) -> LanguageServer | None:
    return next((server for server in LANGUAGE_SERVERS if server.language is language), None)


SIDECAR_SERVERS = (BASEDPYRIGHT, TYPESCRIPT_LANGUAGE_SERVER, JDTLS, GOPLS, KOTLIN_LSP)
"""The servers that run in a service project's sidecar (docs/specs/service-projects.md#language-
servers): the Node programs on the sidecar's Node image, for both of their languages; JDT LS on the
project's own image, whose JDK and Gradle build the project; gopls on the project's own image,
whose Go loads the project, built into the project's install cache by its install; and the Kotlin
LSP's Linux build on the glibc variant of the project's image."""
KOTLIN_SIDECAR_MEMORY = "3g"
"""The Kotlin LSP and the Gradle daemon of its import took 1.88 GiB together on the catalog's
Kotlin service project, under the server's 1 GB heap."""
GO_BUILD_IN_SIDECAR = "go-build"
"""Go's build cache in a sidecar's data folder, which the install cache, read-only there, cannot
hold."""
SIDECAR_PIDS_FOR_GO = 256
"""gopls and the `go list` processes it starts took 93 processes, threads included."""
GO_VARIABLES_LEFT_OUT = frozenset({"GOCACHE", "GOTMPDIR"})
"""The project's Go variables that name places to write, which the read-only install cache is
not in a sidecar."""
GRADLE_HOME_IN_SIDECAR = "gradle"
"""Gradle's user home in a sidecar's data folder: its daemon, its scripts' compiled classes, and
what it would otherwise lock in the install cache."""
PROJECT_CACHE_IN_SIDECAR = "project-cache"
"""Gradle's project cache in a sidecar's data folder, in place of the project's own `.gradle/`,
whose locks the app's builds take: a lock cannot be handed over across containers."""


GRADLE_USER_HOME = "GRADLE_USER_HOME"
GRADLE_READ_ONLY_CACHE = "GRADLE_RO_DEP_CACHE"


def runs_on_a_jdk(server: LanguageServer) -> bool:
    """Whether `server` needs a JDK, to run on or to import a Gradle build with."""
    return server.jdks is not None


def is_built_by_go(server: LanguageServer) -> bool:
    return server.go_install is not None


def sidecar_image(server: LanguageServer, project_image: str) -> str:
    """Where `server` runs in a service project's sidecar: a Node server on the pinned Node image,
    whatever the project's; the Kotlin LSP on the pinned glibc Gradle image, which its Linux build
    and runtime need; another server that needs a JDK, or Go, on the project's own image, which
    holds the toolchain the project builds with, and which `cstudy start` pulled."""
    if server.language is Language.KOTLIN:
        return GRADLE_GLIBC_IMAGE
    if runs_on_a_jdk(server) or is_built_by_go(server):
        return project_image
    return NODE_IMAGE


def tooling_distribution(version: str) -> tuple[str, str]:
    """Where a Gradle tooling API of `version` looks for its own distribution in Gradle's user
    home, for a build that names no wrapper, as Gradle's wrapper lays it out: the marker that says
    it is unpacked, and the folder of the distribution. The Kotlin LSP's import finds the image's
    Gradle there, linked, rather than downloading its tooling API's version."""
    name = f"gradle-{version}-bin"
    url = f"https://services.gradle.org/distributions/{name}.zip"
    folder = f"wrapper/dists/{name}/{_base36(hashlib.md5(url.encode()).digest())}"
    return f"{folder}/{name}.zip.ok", f"{folder}/gradle-{version}"


def _base36(digest: bytes) -> str:
    """As Java's `new BigInteger(1, digest).toString(36)` writes it."""
    number, digits = int.from_bytes(digest, "big"), ""
    while number:
        number, remainder = divmod(number, 36)
        digits = "0123456789abcdefghijklmnopqrstuvwxyz"[remainder] + digits
    return digits or "0"


@dataclass(frozen=True, slots=True)
class CacheInstall:
    """A server that a service project's install builds into the project's install cache, online,
    while `code_intelligence` is on: the one `cstudy doctor --fix` builds into `.cs/lsp/` is built
    for this machine, and a sidecar runs Linux. Its modules and its build go to a scratch folder of
    the cache that `go clean` empties, so only the binary stays."""

    name: str
    version: str
    command: tuple[str, ...]
    environment: Mapping[str, str]
    executable: str
    """Its absolute path in the sidecar, which mounts the install cache at `INSTALL_CACHE`."""


def cache_install(server: LanguageServer) -> CacheInstall | None:
    """For a server that Go builds: the newest version its table pins, which builds with the Go of
    every service project's image (1.27). None for any other server."""
    install = server.go_install
    if install is None:
        return None
    version = install.version_for(None)
    directory = f"{INSTALL_CACHE}/{server.name}/{version}"
    scratch = f"{INSTALL_CACHE}/{server.name}/scratch"
    script = 'mkdir -p "$GOTMPDIR" && go install "$1" && go clean -cache -modcache'
    return CacheInstall(
        name=server.name,
        version=version,
        command=("sh", "-c", script, "sh", f"{install.module}@v{version}"),
        environment={
            "GOBIN": directory,
            "GOMODCACHE": f"{scratch}/mod",
            "GOCACHE": f"{scratch}/build",
            "GOPATH": f"{scratch}/path",
            "GOTMPDIR": f"{scratch}/tmp",
            "CGO_ENABLED": "0",
        },
        executable=f"{directory}/{server.name}",
    )


def cache_install_of(meta: ProblemMeta) -> CacheInstall | None:
    """The server a service project's install builds into its cache: its language's, when that
    server is one Go builds. None for every other problem."""
    if service_of(meta) is None or not meta.languages:
        return None
    server = server_for(meta.languages[0])
    return None if server is None else cache_install(server)


def _from_the_install_cache(server: LanguageServer, _launch: Launch) -> tuple[str, ...]:
    install = cache_install(server)
    if install is None:
        raise ValueError(f"{server.name} is not built into an install cache")
    return (install.executable,)


def sidecar_toolchain(
    server: LanguageServer,
    service: ServiceProject,
    data: str,
    cache_volume: str | None,
    gradle_tooling: str | None = None,
) -> SidecarToolchain | None:
    """What `server` needs of the project's toolchain in its sidecar, whose data folder is the
    absolute `data`: for JDT LS, the image's Gradle (which it finds through the image's
    `GRADLE_HOME`) with its user home and project cache in `data`, and the dependencies of the
    install cache as Gradle's read-only cache, which Gradle neither locks nor writes; for gopls,
    the project's own Go variables, with the build cache and gopls's file cache in `data`, since
    the install cache is read-only there; for the Kotlin LSP, JDT LS's, with the image's Gradle
    where its tooling API of version `gradle_tooling` looks for its own distribution, since the
    project names no wrapper and the sidecar reaches no network. None for a Node server."""
    if is_built_by_go(server):
        return _go_toolchain(service, data, cache_volume)
    if not runs_on_a_jdk(server) and not server.linux_build:
        return None
    environment = {"GRADLE_USER_HOME": f"{data}/{GRADLE_HOME_IN_SIDECAR}"}
    installed = service.env.get(GRADLE_USER_HOME)
    if cache_volume is not None and installed is not None:
        environment[GRADLE_READ_ONLY_CACHE] = f"{installed}/caches"
    properties = f"org.gradle.projectcachedir={data}/{PROJECT_CACHE_IN_SIDECAR}\n"
    files = {f"{GRADLE_HOME_IN_SIDECAR}/gradle.properties": properties}
    links: dict[str, str] = {}
    kotlin = server.language is Language.KOTLIN
    if kotlin and gradle_tooling is not None:
        marker, distribution = tooling_distribution(gradle_tooling)
        files[f"{GRADLE_HOME_IN_SIDECAR}/{marker}"] = ""
        links[f"{GRADLE_HOME_IN_SIDECAR}/{distribution}"] = IMAGE_GRADLE_HOME
    return SidecarToolchain(
        cache_volume=cache_volume,
        environment=environment,
        files=files,
        writable_project=True,
        memory=KOTLIN_SIDECAR_MEMORY if kotlin else JVM_SIDECAR_MEMORY,
        pids=JVM_SIDECAR_PIDS,
        links=links,
    )


def _go_toolchain(service: ServiceProject, data: str, cache_volume: str | None) -> SidecarToolchain:
    kept = {
        name: value
        for name, value in service.env.items()
        if (name.startswith("GO") or name == "CGO_ENABLED") and name not in GO_VARIABLES_LEFT_OUT
    }
    environment = {
        **kept,
        "GOCACHE": f"{data}/{GO_BUILD_IN_SIDECAR}",
        "XDG_CACHE_HOME": f"{data}/{CACHE_DIRECTORY}",
    }
    return SidecarToolchain(cache_volume, environment, pids=SIDECAR_PIDS_FOR_GO)


def sidecar_server(server: LanguageServer, folder: str) -> LanguageServer:
    """`server` as it runs in a service project's sidecar, on the dependencies installed in the
    absolute `folder`. TypeScript's compiler is the folder's own, so the workspace's `typescript/`
    is not needed; basedpyright is the catalog's, since it reads the folder's `[tool.pyright]`,
    whose `venv` it finds without asking Python; JDT LS runs on the image's JDK, so the JDK this
    machine selects does not matter; gopls is the one the install built into the project's install
    cache; the Kotlin LSP is its Linux build. Raises ValueError for a server of no sidecar."""
    if server not in SIDECAR_SERVERS:
        raise ValueError(f"{server.name} runs in no sidecar")
    if server is KOTLIN_LSP:
        return KOTLIN_LSP_LINUX
    if runs_on_a_jdk(server):
        return replace(server, jdks=None)
    if is_built_by_go(server):
        return replace(server, launcher=_from_the_install_cache)
    if server is not TYPESCRIPT_LANGUAGE_SERVER:
        return server
    options = partial(_compiler_options, folder)
    return replace(server, initialization_options=options, requirement=None)


class RouteKind(StrEnum):
    """The kinds of problem that the route table tells apart (docs/specs/web-ui.md#where-each-
    server-runs): each `ProblemKind`, a debugging problem, and a project that is a service
    project."""

    FUNCTION = "function"
    PROGRESSIVE = "progressive"
    DESIGN = "design"
    CONCURRENT = "concurrent"
    DEBUGGING = "debugging"
    PROJECT = "project"
    SERVICE_PROJECT = "service_project"


_ROUTE_KINDS: Mapping[ProblemKind, RouteKind] = {
    ProblemKind.FUNCTION: RouteKind.FUNCTION,
    ProblemKind.PROGRESSIVE: RouteKind.PROGRESSIVE,
    ProblemKind.DESIGN: RouteKind.DESIGN,
    ProblemKind.CONCURRENT: RouteKind.CONCURRENT,
    ProblemKind.PROJECT: RouteKind.PROJECT,
}
"""A new `ProblemKind` has no route until it is named here."""


def route_kind(meta: ProblemMeta) -> RouteKind | None:
    """A service project first, then a problem of the debugging track, then the problem's kind;
    None for a kind the table does not know."""
    if service_of(meta) is not None:
        return RouteKind.SERVICE_PROJECT
    if meta.track is Track.DEBUGGING:
        return RouteKind.DEBUGGING
    return _ROUTE_KINDS.get(meta.kind)


class Placement(StrEnum):
    NATIVE = "native"
    """The server runs on this machine, from `.cs/lsp/` or `PATH`."""
    SIDECAR = "sidecar"
    """The server runs in a container of its own, through `docker exec`: sandboxed code writes the
    folder, and a server on this machine would run what it names."""
    PENDING = "pending"
    """No server yet; the reason names the work it waits for."""
    NOT_APPLICABLE = "not_applicable"
    """The catalog has no problem of this kind in this language."""


@dataclass(frozen=True, slots=True)
class Route:
    placement: Placement
    reason: str = ""
    """Why there is no server, for a route that runs none."""

    @property
    def runs(self) -> bool:
        return self.placement in (Placement.NATIVE, Placement.SIDECAR)


NATIVE = Route(Placement.NATIVE)
IN_SIDECAR = Route(Placement.SIDECAR)
SERVICE_PROJECT_ROUTES: Mapping[Language, Route] = {
    Language.PYTHON: IN_SIDECAR,
    Language.TYPESCRIPT: IN_SIDECAR,
    Language.JAVA: IN_SIDECAR,
    Language.KOTLIN: IN_SIDECAR,
    Language.GO: IN_SIDECAR,
    Language.RUST: Route(Placement.NOT_APPLICABLE, "the catalog has no Rust service project"),
}
"""Where a service project's server runs, by language: a key for every language, so a new one
says where it stands. Every other kind runs its language's server on this machine."""


def route_for(kind: RouteKind, language: Language) -> Route | None:
    """None where nothing says how the combination gets code intelligence: a gap."""
    if kind is RouteKind.SERVICE_PROJECT:
        return SERVICE_PROJECT_ROUTES.get(language)
    return NATIVE if server_for(language) is not None else None


def route_of(meta: ProblemMeta, language: Language) -> Route | None:
    kind = route_kind(meta)
    return None if kind is None else route_for(kind, language)


class NoCodeIntelligence(StrEnum):
    """Why an attempt has no code intelligence whatever its language's server."""

    SERVICE_PROJECT = "service_project"
    """Sandboxed code writes the folder, and a server on this machine would read it, until one runs
    in a sidecar for the language (docs/specs/service-projects.md#language-servers)."""


def no_code_intelligence(meta: ProblemMeta, language: Language | None) -> NoCodeIntelligence | None:
    """A service project in a language whose server runs in no sidecar yet has none."""
    if service_of(meta) is None:
        return None
    route = None if language is None else route_of(meta, language)
    return None if route is not None and route.runs else NoCodeIntelligence.SERVICE_PROJECT
