"""Builds of a language server that its vendor publishes on its own schedule, which `cstudy doctor
--fix` fetches at their newest instead of pinning one (ADR 0018, Kotlin revisited): JetBrains'
Kotlin LSP ships early-access builds that stop working a few weeks after their release.

The releases are GitHub's list of the vendor's repository (`GET /repos/{owner}/{repo}/releases`),
newest first. A release's notes link each standalone archive and, beside it, the `.sha256` file the
vendor publishes for it; a build is used only with that checksum. The license of a release is the
agreement its repository holds at the release's tag.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import cast

_SHA256 = re.compile(r"^([0-9a-fA-F]{64})(?:\s+\*?(\S+))?\s*$")
_LAST_DAY = re.compile(r"valid through (\d{4})-(\d{2})-(\d{2})")
_AGREEMENT_VERSION = re.compile(r"^Version (\d+(?:\.\d+)*)\b")
EXPIRED_WORDS = "has expired"
"""What a build past its last day prints, at start and for `license status`."""
_SMALL_WORDS = frozenset({"of", "and", "the", "for"})


@dataclass(frozen=True, slots=True)
class License:
    """Terms the vendor of a server asks you to accept: `cstudy doctor --fix` downloads the server
    only after you accept them, when it asks or with `--accept-license <key>`."""

    key: str
    """What `--accept-license` takes and the workspace's marker records."""
    name: str
    url: str
    summary: str
    """What the server is, as `--fix` says it before it asks: `partly closed source, from
    JetBrains`."""


@dataclass(frozen=True, slots=True)
class Releases:
    """Where a server's builds are listed, and how its notes name the archive of each machine."""

    api_url: str
    """GitHub's REST list of the repository's releases."""
    asset: str
    """A pattern of an archive's URL, with `{suffix}` for the machine's; its group `version` is
    the build's version."""
    suffixes: Mapping[str, str]
    """The end of the archive's name on each machine (`machine_of`)."""
    license_url: str
    """The agreement at a release's tag, with `{tag}`: a raw file, read once per fetch."""
    top_directory: str
    """The directory the archives hold the build in, with `{version}`; Windows' hold none."""
    checksum_suffix: str = ".sha256"
    status_arguments: tuple[str, ...] = ("license", "status")
    """What the build's launcher takes to print the last day it runs, without starting a
    server."""


@dataclass(frozen=True, slots=True)
class Build:
    """A release's standalone archive for one machine, with the URL of its published checksum."""

    version: str
    tag: str
    url: str
    checksum_url: str

    @property
    def file_name(self) -> str:
        return self.url.rsplit("/", 1)[1]


def newest_build(document: object, releases: Releases, machine: str) -> Build | None:
    """The newest release that is no draft and links the archive of `machine` and its checksum;
    None when none does, or `document` is no list of releases (an API error, say)."""
    suffix = releases.suffixes.get(machine)
    if suffix is None or not isinstance(document, list):
        return None
    pattern = re.compile(releases.asset.format(suffix=re.escape(suffix)))
    for release in map(_fields, cast(list[object], document)):
        found = _build(release, pattern, releases.checksum_suffix)
        if found is not None and release.get("draft") is not True:
            return found
    return None


def checksum_in(text: str, file_name: str) -> str | None:
    """The SHA-256 a `.sha256` file holds, lowercase: `<hex> *<file>`, `<hex>  <file>` or the
    digest alone; None for anything else, or a digest that names another file."""
    found = _SHA256.match(text.strip())
    if found is None or (found[2] is not None and found[2] != file_name):
        return None
    return found[1].lower()


def license_of(text: str, known: License) -> License | None:
    """The license an agreement's text states by its title and version: `known` when they are
    its name, another license of the same key otherwise; None for a text that is no agreement."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < 2 or not lines[0].isupper():
        return None
    version = _AGREEMENT_VERSION.match(lines[1])
    if version is None:
        return None
    name = f"{_titled(lines[0])} {version[1]}"
    if name.casefold() == known.name.casefold():
        return known
    return License(known.key, name, known.url, known.summary)


def last_day(status: str) -> date | None:
    """The last day an early-access build runs, as `license status` names it ("valid through
    2026-11-12"); None when it names none."""
    found = _LAST_DAY.search(status)
    return None if found is None else date(int(found[1]), int(found[2]), int(found[3]))


def expired_already(output: str) -> bool:
    return EXPIRED_WORDS in output


def _build(release: dict[str, object], pattern: re.Pattern[str], checksum: str) -> Build | None:
    body, tag = release.get("body"), release.get("tag_name")
    if not isinstance(body, str) or not isinstance(tag, str):
        return None
    for found in pattern.finditer(body):
        url = found[0]
        if f"({url}{checksum})" in body:
            return Build(found["version"], tag, url, url + checksum)
    return None


def _titled(upper: str) -> str:
    """`JETBRAINS FREE PLUGIN LICENSE AGREEMENT` as JetBrains writes its name elsewhere."""
    words = [
        word.lower() if word.lower() in _SMALL_WORDS else word.capitalize()
        for word in upper.split()
    ]
    return " ".join(words).replace("Jetbrains", "JetBrains")


def _fields(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}
