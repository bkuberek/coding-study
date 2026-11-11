"""`.cs/lsp/`: the pnpm project of the web UI's language servers, and the servers downloaded as
archives beside it (docs/specs/installation-and-workspaces.md#layout,
docs/specs/web-ui.md#language-servers)."""

import hashlib
import json
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from datetime import date
from importlib import resources
from pathlib import Path
from typing import cast

from coding_study.adapters.workspace_marker import accepted_license, record_license
from coding_study.application.ports import (
    CommandRunner,
    Fetched,
    FileMissing,
    NewestBuild,
    NoBuild,
    NotInstalled,
    ProbeResult,
    ServerProbe,
    ToolProbe,
    Unpacked,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.code_intelligence import (
    GO_RELEASE_COMMAND,
    KOTLIN_LSP,
    LSP_DIRECTORY,
    LSP_INSTALL_COMMAND,
    SIDECAR_PLATFORM,
    Archive,
    GoInstall,
    LanguageServer,
    Launch,
    License,
    build_archive,
    build_place,
    go_release,
    machine_of,
    sidecar_machine,
)
from coding_study.domain.problem import Language
from coding_study.domain.project_manifest import MANIFESTS_DIRECTORY
from coding_study.domain.server_builds import (
    checksum_in,
    expired_already,
    last_day,
    license_of,
    newest_build,
)
from coding_study.domain.service_project import INSTALL_RECORD_LANGUAGE, INSTALL_RECORD_SUFFIX

GRADLE_BUILD_RECEIPT = "org/gradle/build-receipt.properties"
MANIFEST_PACKAGE = "coding_study.adapters.language_servers"
MANIFEST_FILES = ("package.json", "pnpm-lock.yaml")
LOCAL_TOOLCHAIN = {"GOTOOLCHAIN": "local"}
DOWNLOAD_TIMEOUT_S = 60
"""How long the download may wait for the server to answer or send more."""
CHUNK_BYTES = 1024 * 1024
UNIX_MODE_SHIFT = 16
"""A zip member made on Unix keeps its mode in the high half of its external attributes."""
EXECUTE_BITS = 0o111
EXECUTABLE_MODE = 0o755


class LspDirectory:
    """Locates the servers in a workspace's `.cs/lsp/` and installs them there."""

    def __init__(
        self,
        workspace: Path,
        tools: ToolProbe,
        commands: CommandRunner,
        today: Callable[[], date] = date.today,
        fetch: Callable[[str], bytes] | None = None,
    ) -> None:
        """`fetch` reads what an HTTPS URL holds, for the releases of a server whose newest build
        `--fix` fetches; urllib's by default."""
        self._workspace = workspace
        self._directory = workspace / LSP_DIRECTORY
        self._tools = tools
        self._commands = commands
        self._today = today
        self._fetch = fetch or _https

    def probe(self, server: LanguageServer) -> ServerProbe:
        """Not installed without the server's script or binary in `.cs/lsp/`, or, for a server
        on PATH, without one whose version command runs or with only a proxy of it; a file
        missing when its package is there but the workspace's TypeScript is not; unpacked for an
        archive whose pinned build is there, which has no version command; fetched, as its record
        says, for a server whose newest build `--fix` fetched; otherwise what its version command
        printed."""
        if server.releases is not None:
            return self._fetched(server)
        if server.script is not None and not (self._directory / server.script).is_file():
            return NotInstalled()
        requirement = server.requirement
        if requirement is not None and not (self._workspace / requirement.path).is_file():
            return FileMissing(requirement.path)
        if server.archive is not None:
            return Unpacked()
        return self._version(server)

    def today(self) -> date:
        return self._today()

    def newest_build(self, server: LanguageServer) -> NewestBuild | NoBuild:
        """Reads the server's releases list, the `.sha256` file of the newest build for this
        machine, or for a sidecar's Linux on this machine's processor, and the license at its
        release's tag; nothing is downloaded yet."""
        releases, known = server.releases, server.license
        if releases is None or known is None:
            return NoBuild(f"{server.name} publishes no builds of its own")
        machine = sidecar_machine(platform.machine()) if server.linux_build else self.machine
        try:
            listed = json.loads(self._fetch(releases.api_url))
            build = newest_build(listed, releases, machine)
            if build is None:
                reason = f"no release of {server.name} at {releases.api_url} has a build for"
                return NoBuild(f"{reason} {machine} with a published SHA-256")
            sha256 = checksum_in(self._fetch(build.checksum_url).decode(), build.file_name)
            if sha256 is None:
                return NoBuild(f"{build.checksum_url} holds no SHA-256 of {build.file_name}")
            license_url = releases.license_url.format(tag=build.tag)
            license = license_of(self._fetch(license_url).decode(), known)
        except (OSError, ValueError) as error:
            return NoBuild(f"cannot read the releases of {server.name}: {error}")
        if license is None:
            return NoBuild(f"cannot read the license of {build.tag} at {license_url}")
        archive = build_archive(build, sha256, machine, build_place(server))
        return NewestBuild(build, archive, license)

    def install_build(self, server: LanguageServer, newest: NewestBuild) -> ProbeResult:
        """Downloads and checks the build as `download` does, then asks it the last day it runs
        (`license status`, with its configuration in a scratch directory that is gone afterwards)
        and records it beside the build."""
        downloaded = self.download(newest.archive)
        if downloaded.exit_code != 0:
            return downloaded
        version = newest.build.version
        if server.linux_build:
            last = self._last_day_of_this_machines(version)
            build = self._directory / newest.archive.directory / newest.archive.into
            tooling = _gradle_tooling(build)
            self._record(server, newest, last, tooling)
        else:
            status = self._status(server)
            if expired_already(status):
                return ProbeResult(1, f"{server.name} {version}, JetBrains' newest, has expired\n")
            last = last_day(status)
            self._record(server, newest, last)
        until = "" if last is None else f", runs until {last.isoformat()}"
        return ProbeResult(
            0, f"{server.name} {version} in {LSP_DIRECTORY}/{newest.archive.directory}{until}\n"
        )

    def _status(self, server: LanguageServer) -> str:
        releases = server.releases
        with tempfile.TemporaryDirectory(prefix=".status-", dir=self._directory) as scratch:
            launch = Launch(str(self._directory), scratch, platform=sys.platform)
            command = (server.command(launch)[0], *(releases.status_arguments if releases else ()))
            result = self._commands.run(command, self._directory, server.environment(launch))
        return "" if result is None else result.output

    def _last_day_of_this_machines(self, version: str) -> date | None:
        """The last day of a Linux build, which cannot run here to say it: that of this machine's
        build of the same version, which `--fix` fetches first; None without one."""
        probe = self._fetched(KOTLIN_LSP)
        return probe.last_day if isinstance(probe, Fetched) and probe.version == version else None

    def _record(
        self,
        server: LanguageServer,
        newest: NewestBuild,
        last: date | None,
        gradle_tooling: str | None = None,
    ) -> None:
        record: dict[str, object] = {
            "version": newest.build.version,
            "last_day": None if last is None else last.isoformat(),
            "license": {"name": newest.license.name, "url": newest.license.url},
            "url": newest.archive.url,
            "sha256": newest.archive.sha256,
        }
        if gradle_tooling is not None:
            record["gradle_tooling"] = gradle_tooling
        (self._directory / str(server.script)).write_text(json.dumps(record, indent=2) + "\n")

    def _fetched(self, server: LanguageServer) -> ServerProbe:
        """Not installed without a readable record or the build it names."""
        known = server.license
        try:
            record = json.loads((self._directory / str(server.script)).read_text())
            version, last = record["version"], record["last_day"]
            license = License(
                known.key if known else "",
                record["license"]["name"],
                record["license"]["url"],
                known.summary if known else "",
            )
            ends = None if last is None else date.fromisoformat(last)
            tooling = record.get("gradle_tooling")
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return NotInstalled()
        on = SIDECAR_PLATFORM if server.linux_build else sys.platform
        launcher = server.command(Launch(str(self._directory), platform=on))[0]
        if not isinstance(version, str) or not Path(launcher).is_file():
            return NotInstalled()
        return Fetched(version, ends, license, tooling if isinstance(tooling, str) else None)

    @property
    def machine(self) -> str:
        return machine_of(sys.platform, platform.machine())

    def installed_service_languages(self) -> frozenset[Language]:
        """The languages of the service projects whose dependencies are installed here, as their
        install records name them (`.cs/projects/<slug>.install.json`)."""
        languages: set[Language] = set()
        for path in (self._workspace / MANIFESTS_DIRECTORY).glob(f"*{INSTALL_RECORD_SUFFIX}"):
            try:
                record: object = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            fields = cast(dict[str, object], record) if isinstance(record, dict) else {}
            named = fields.get(INSTALL_RECORD_LANGUAGE)
            if isinstance(named, str) and named in tuple(Language):
                languages.add(Language(named))
        return frozenset(languages)

    def license_accepted(self, license: License) -> bool:
        return accepted_license(self._workspace, license.key) == (license.name, license.url)

    def accept_license(self, license: License) -> None:
        record_license(self._workspace, license.key, license.name, license.url)

    def warm_up(self, server: LanguageServer, root: str, java_home: Path) -> ProbeResult | None:
        """Runs the server's warm-up in `root` under this Python, isolated from the directory it
        reads, with an index, configuration and logs in a scratch directory of `.cs/lsp/` that is
        gone afterwards; None for a server without one."""
        if server.warmup is None:
            return None
        self._directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".warm-up-", dir=self._directory) as scratch:
            launch = Launch(
                str(self._directory), scratch, platform=sys.platform, java_home=str(java_home)
            )
            directory = self._workspace / root
            command = server.warm_up_command(launch, sys.executable, str(directory))
            return self._commands.run(command, directory, server.environment(launch))

    def go_release(self) -> str | None:
        """What `go env GOVERSION` prints with the local toolchain, which never downloads
        another: `1.27.3`; None without a Go that runs."""
        result = self._commands.run(GO_RELEASE_COMMAND, self._workspace, LOCAL_TOOLCHAIN)
        if result is None or result.exit_code != 0:
            return None
        return go_release(result.output)

    def go_install(self, install: GoInstall, version: str) -> ProbeResult | None:
        """`go install` of `version` into `.cs/lsp/bin/`, run in `.cs/lsp/`; None without `go`."""
        self._directory.mkdir(parents=True, exist_ok=True)
        environment = install.environment(str(self._directory))
        return self._commands.run(install.command(version), self._directory, environment)

    def download(self, archive: Archive) -> ProbeResult:
        """Fetch the archive, a gzipped tar or a zip, into a scratch directory of `.cs/lsp/`,
        check its SHA-256, unpack it there refusing any member that would land outside, and only
        then put it in place of its
        directory; whatever fails leaves the earlier build as it was and no scratch behind."""
        self._directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".download-", dir=self._directory) as scratch:
            try:
                return _unpacked(archive, Path(scratch), self._directory / archive.directory)
            except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
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
        """A server on PATH that is not there is not installed; a Node server whose `node` is
        not there cannot say its version."""
        command = server.version_command(str(self._directory))
        result = self._tools.run(command)
        if result is None:
            return NotInstalled() if server.script is None else VersionFailed(_not_found(command))
        if result.exit_code != 0:
            if server.says_missing(result.output):
                return NotInstalled()
            return VersionFailed(_first_line(result.output) or f"exited with {result.exit_code}")
        return VersionPrinted(result.output)


def _unpacked(archive: Archive, scratch: Path, target: Path) -> ProbeResult:
    downloaded = scratch / "archive"
    digest = _fetched(archive.url, downloaded)
    if digest != archive.sha256:
        return ProbeResult(1, f"SHA-256 mismatch: expected {archive.sha256}, got {digest}\n")
    extracted = scratch / "extracted"
    if zipfile.is_zipfile(downloaded):
        _unzip(downloaded, extracted)
    else:
        with tarfile.open(downloaded) as tar:
            tar.extractall(extracted, filter="data")
    build = extracted / archive.strip if archive.strip else extracted
    if not build.is_dir():
        return ProbeResult(1, f"the archive holds no {archive.strip}/\n")
    if archive.into:
        _replace(build, target / archive.into, scratch / "earlier")
    else:
        _replace(build, target, scratch / "earlier")
    return ProbeResult(0, f"unpacked into {LSP_DIRECTORY}/{archive.directory}\n")


def _replace(build: Path, place: Path, earlier: Path) -> None:
    """`build` in place of whatever `place` held, which goes to `earlier`; what is beside `place`
    stays, such as another build of the same server and its record."""
    place.parent.mkdir(parents=True, exist_ok=True)
    if place.exists():
        place.rename(earlier)
    build.rename(place)


def _gradle_tooling(directory: Path) -> str | None:
    """The version of the Gradle tooling API a build bundles, as the build receipt in one of its
    jars says; None when none says it."""
    for jar in sorted(directory.rglob("*gradle*tooling*.jar")):
        try:
            with zipfile.ZipFile(jar) as archive:
                receipt = archive.read(GRADLE_BUILD_RECEIPT).decode()
        except (OSError, KeyError, zipfile.BadZipFile):
            continue
        for line in receipt.splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "versionNumber" and value.strip():
                return value.strip()
    return None


def _unzip(archive: Path, directory: Path) -> None:
    """Unpacks a zip as `tarfile`'s `data` filter unpacks a tar: every member and every symbolic
    link's target stays inside `directory`. Unlike `ZipFile.extractall`, it keeps the Unix modes
    the archive records, so a launcher stays executable, and its symbolic links, which a bundled
    JDK holds. Raises OSError for a member that would leave."""
    directory.mkdir(parents=True)
    with zipfile.ZipFile(archive) as opened:
        for member in opened.infolist():
            _unzip_member(opened, member, directory)


def _unzip_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo, directory: Path) -> None:
    path = _inside(directory, directory / member.filename)
    mode = member.external_attr >> UNIX_MODE_SHIFT
    if member.is_dir():
        path.mkdir(parents=True, exist_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if stat.S_ISLNK(mode):
        target = archive.read(member).decode()
        _inside(directory, path.parent / target)
        path.symlink_to(target)
        return
    with archive.open(member) as source, path.open("wb") as out:
        shutil.copyfileobj(source, out, CHUNK_BYTES)
    if mode & EXECUTE_BITS:
        path.chmod(EXECUTABLE_MODE)


def _inside(directory: Path, path: Path) -> Path:
    """`path`, unless it resolves outside `directory`; raises OSError then."""
    if not path.resolve().is_relative_to(directory.resolve()):
        raise OSError(f"archive member leaves its directory: {path}")
    return path


def _https(url: str) -> bytes:
    """What `url` holds, as GitHub's API asks a client to fetch it."""
    request = urllib.request.Request(
        url, headers={"User-Agent": "cstudy", "Accept": "application/vnd.github+json"}
    )
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_S) as response:
        return response.read()


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


def _not_found(command: tuple[str, ...]) -> str:
    """`node not found on PATH`, naming the program the version command runs."""
    return f"{Path(command[0]).name} not found on PATH"


def _first_line(output: str) -> str:
    return next((line.strip() for line in output.splitlines() if line.strip()), "")


def _write_if_different(path: Path, content: bytes) -> None:
    if path.is_file() and path.read_bytes() == content:
        return
    path.write_bytes(content)
