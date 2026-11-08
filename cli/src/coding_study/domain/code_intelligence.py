"""The catalog of language servers behind the web UI's code intelligence
(docs/specs/web-ui.md#language-servers, ADR 0018).

Paths are POSIX strings: relative to the workspace root, or to `.cs/lsp/` where the field says so.
Commands take the absolute directories they run with (`Launch`), so no path type is needed here.
"""

import re
import shlex
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum

from coding_study.domain.cases import JsonValue
from coding_study.domain.jdk import SUPPORTED_JDKS, JdkRange
from coding_study.domain.layout import (
    GO_PROJECT,
    JVM_PROJECT,
    PYTHON_PROJECT,
    RUST_PROJECT,
    TYPESCRIPT_PROJECT,
)
from coding_study.domain.problem import Language, ProblemMeta
from coding_study.domain.server_builds import Build, License, Releases
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
    return (NODE, f"{lsp_directory}/{server.version_script}", "--version")


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

KOTLIN_LSP_DIRECTORY = "kotlin-lsp"
KOTLIN_LSP_HOME = f"{KOTLIN_LSP_DIRECTORY}/server"
"""Where the build `cstudy doctor --fix` fetched lives, whatever its version, so a newer one takes
its place."""
KOTLIN_LSP_RECORD = f"{KOTLIN_LSP_DIRECTORY}/installed.json"
"""What `--fix` writes once the build is in place: its version, the last day it runs, the license
it came under and where it came from (`InstalledBuild`)."""
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


def build_archive(build: Build, sha256: str, machine: str) -> Archive:
    """The archive of a fetched build, unpacked into `kotlin-lsp/server/`: the Windows archives
    hold the build at their top, the others in `kotlin-server-<version>/`."""
    releases = KOTLIN_LSP_RELEASES
    flat = machine.startswith("win32")
    top = "" if flat else releases.top_directory.format(version=build.version)
    return Archive(build.url, sha256, KOTLIN_LSP_DIRECTORY, into="server", strip=top)


def _kotlin_lsp_launcher(platform: str) -> str:
    executable = "intellij-server.exe" if platform == "win32" else "intellij-server"
    return f"{KOTLIN_LSP_HOME}/bin/{executable}"


def _kotlin_lsp_command(server: LanguageServer, launch: Launch) -> tuple[str, ...]:
    return (
        f"{launch.lsp_directory}/{_kotlin_lsp_launcher(launch.platform)}",
        "--stdio",
        f"--system-path={launch.data_directory}/system",
    )


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


class NoCodeIntelligence(StrEnum):
    """Why an attempt has no code intelligence whatever its language's server."""

    SERVICE_PROJECT = "service_project"
    """Sandboxed code writes the folder, and a server on this machine would read it, until one runs
    in a container (docs/specs/service-projects.md#language-servers)."""


def no_code_intelligence(meta: ProblemMeta) -> NoCodeIntelligence | None:
    return NoCodeIntelligence.SERVICE_PROJECT if service_of(meta) is not None else None
