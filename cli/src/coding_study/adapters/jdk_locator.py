"""The JDK the shell selects (docs/specs/cli.md#the-selected-jdk, ADR 0016).

`JAVA_HOME` when it is set, else the JDK of the first `java` on `PATH`, with every symbolic link
resolved: the Gradle wrapper's own rule, which version managers set per shell and per directory. The
version comes from the `release` file in the JDK's home, so listing problems starts no JVM. Only a
`java` whose home has no such file, such as a launcher stub, is run, once per selector, to ask for
its home and version.
"""

import os
import re
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from coding_study.domain.errors import RunnerStartError
from coding_study.domain.jdk import JDK_FIX, JdkSource, SelectedJdk, no_jdk_sentence

JAVA_HOME = "JAVA_HOME"
JAVA = "java"
JAVA_LAUNCHER = Path("bin") / JAVA
RELEASE_FILE = "release"
RELEASE_VERSION_KEY = "JAVA_VERSION"
PROBE_ARGUMENTS = ("-XshowSettings:properties", "-version")
PROBE_TIMEOUT_SECONDS = 30.0
"""A JVM start, on a loaded machine."""
LEGACY_VERSION_PREFIX = 1
"""Releases before 9 spell their feature release second: `1.8.0_392`."""
_VERSION = re.compile(r"(\d+)(?:\.(\d+))?")
_PROPERTY = re.compile(r"^\s*(java\.home|java\.version)\s*=\s*(.*?)\s*$", re.MULTILINE)


class JdkHome(Protocol):
    """What the JVM adapter builds and launches with."""

    def home(self) -> Path:
        """The selected JDK's home; raises RunnerStartError when nothing is selected."""
        ...


@dataclass(frozen=True, slots=True)
class LocatedJdk:
    home: Path
    """With every symbolic link resolved."""
    jdk: SelectedJdk


@dataclass(frozen=True, slots=True)
class _Selection:
    located: LocatedJdk | None
    unusable_java_home: str | None = None


@dataclass(frozen=True, slots=True)
class _Probed:
    home: Path
    version: str


class EnvJdkSelector:
    """`JdkSelector`, and the `JdkHome` of the JVM adapter, for one environment. Selects once and
    keeps the answer, so a command asks a `java` at most once."""

    def __init__(
        self, environ: Mapping[str, str], probe_timeout_seconds: float = PROBE_TIMEOUT_SECONDS
    ) -> None:
        self._environ = environ
        self._probe_timeout_seconds = probe_timeout_seconds
        self._selection: _Selection | None = None

    def selected(self) -> SelectedJdk | None:
        located = self.located()
        return None if located is None else located.jdk

    def unusable_java_home(self) -> str | None:
        return self._selected().unusable_java_home

    def located(self) -> LocatedJdk | None:
        return self._selected().located

    def home(self) -> Path:
        located = self.located()
        if located is None:
            raise RunnerStartError(f"{no_jdk_sentence(self.unusable_java_home())}; {JDK_FIX}")
        return located.home

    def _selected(self) -> _Selection:
        if self._selection is None:
            self._selection = self._select()
        return self._selection

    def _select(self) -> _Selection:
        java_home = self._environ.get(JAVA_HOME)
        if java_home:
            located = self._in_home(Path(java_home))
            return _Selection(located, None if located else java_home)
        return _Selection(self._on_path())

    def _in_home(self, home: Path) -> LocatedJdk | None:
        launcher = home / JAVA_LAUNCHER
        if not _is_executable(launcher):
            return None
        resolved = home.resolve()
        located = _located(resolved, _release_version(resolved), JdkSource.JAVA_HOME)
        if located is not None:
            return located
        probed = self._probe(launcher)
        return None if probed is None else _located(resolved, probed.version, JdkSource.JAVA_HOME)

    def _on_path(self) -> LocatedJdk | None:
        java = shutil.which(JAVA, path=self._environ.get("PATH", os.defpath))
        if java is None:
            return None
        home = Path(java).resolve().parent.parent
        if _is_executable(home / JAVA_LAUNCHER):
            located = _located(home, _release_version(home), JdkSource.PATH)
            if located is not None:
                return located
        probed = self._probe(Path(java))
        if probed is None:
            return None
        home = probed.home.resolve()
        version = _release_version(home) or probed.version
        return _located(home, version, JdkSource.PATH)

    def _probe(self, java: Path) -> _Probed | None:
        """Asks `java` for its home and version; None when it does not run or does not say."""
        try:
            completed = subprocess.run(
                (str(java), *PROBE_ARGUMENTS),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self._probe_timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        properties = dict(_PROPERTY.findall(completed.stderr + completed.stdout))
        home = properties.get("java.home")
        version = properties.get("java.version")
        if completed.returncode != 0 or not home or not version:
            return None
        return _Probed(Path(home), version)


def shell_jdk() -> EnvJdkSelector:
    """The JDK this process's environment selects."""
    return EnvJdkSelector(os.environ)


def _located(home: Path, version: str | None, source: JdkSource) -> LocatedJdk | None:
    feature = None if version is None else _feature_release(version)
    if version is None or feature is None:
        return None
    return LocatedJdk(home, SelectedJdk(version, feature, source))


def _release_version(home: Path) -> str | None:
    """`JAVA_VERSION` of the home's `release` file, such as `26.0.1`, without its quotes."""
    try:
        text = (home / RELEASE_FILE).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and key.strip() == RELEASE_VERSION_KEY:
            return value.strip().strip('"') or None
    return None


def _feature_release(version: str) -> int | None:
    match = _VERSION.match(version)
    if match is None:
        return None
    first = int(match.group(1))
    if first == LEGACY_VERSION_PREFIX and match.group(2):
        return int(match.group(2))
    return first


def _is_executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)
