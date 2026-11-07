"""The software this install holds, for `cstudy about` and the About view: cstudy's own license,
the Python packages it needs and their licenses, from the metadata pip or uv wrote, and the notice
the web page's build wrote (docs/specs/cli.md#cstudy-about)."""

import re
from collections import deque
from collections.abc import Mapping, Sequence
from importlib import metadata
from importlib.metadata import Distribution
from pathlib import Path

from coding_study.domain.about import Credit

DISTRIBUTION = "coding-study"
NOTICE_FILE = "THIRD_PARTY_LICENSES.txt"
NO_OWN_LICENSE = "This copy of cstudy carries no license text; it is MIT licensed, see LICENSE."
LICENSE_CLASSIFIER_PREFIX = "License :: OSI Approved :: "
MAX_LICENSE_NAME = 60
"""A `License` field longer than this, or on more than one line, holds the text, not the name."""

_REQUIREMENT_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_EXTRA_MARKER = re.compile(r"extra\s*==")
_LICENSE_FILE = re.compile(r"(licen[cs]e|copying)", re.IGNORECASE)
_NAME_SEPARATORS = re.compile(r"[-_.]+")


class InstalledSoftware:
    """`InstalledPackages` over the running environment and a built web page's directory."""

    def __init__(self, static_directory: Path) -> None:
        self._static_directory = static_directory

    def own_license_text(self) -> str:
        return _license_text(_distribution(DISTRIBUTION)) or NO_OWN_LICENSE

    def python_packages(self) -> tuple[Credit, ...]:
        return tuple(
            Credit(name, dist.version, _declared(dist))
            for name, dist in sorted(_runtime_distributions().items())
        )

    def python_license_texts(self) -> Mapping[str, str]:
        texts = {name: _license_text(dist) for name, dist in _runtime_distributions().items()}
        return {name: text for name, text in texts.items() if text}

    def web_ui_notice(self) -> str | None:
        path = self._static_directory / NOTICE_FILE
        return path.read_text(encoding="utf-8") if path.is_file() else None


def requirement_name(requirement: str) -> str | None:
    """The package a `Requires-Dist` line names, in the form pip normalizes it to; None for one
    that is only needed with an extra, which cstudy does not install."""
    spec, _, marker = requirement.partition(";")
    found = _REQUIREMENT_NAME.match(spec.strip())
    if found is None or _EXTRA_MARKER.search(marker):
        return None
    return _NAME_SEPARATORS.sub("-", found.group()).lower()


def declared_license(expression: str | None, field: str | None, classifiers: Sequence[str]) -> str:
    """The license a package declares by its name: its SPDX expression, a short `License` field,
    or the first license classifier; empty when it declares none."""
    if expression:
        return expression
    name = (field or "").strip()
    if name and "\n" not in name and len(name) <= MAX_LICENSE_NAME:
        return name
    prefixed = (c for c in classifiers if c.startswith(LICENSE_CLASSIFIER_PREFIX))
    return next((c.removeprefix(LICENSE_CLASSIFIER_PREFIX) for c in prefixed), "")


def _declared(dist: Distribution) -> str:
    headers = dist.metadata
    return declared_license(
        headers.get("License-Expression"), headers.get("License"), headers.get_all("Classifier", [])
    )


def _distribution(name: str) -> Distribution | None:
    try:
        return metadata.distribution(name)
    except metadata.PackageNotFoundError:
        return None


def _runtime_distributions() -> dict[str, Distribution]:
    """Every installed package cstudy requires, and those they require in turn, by name. A
    requirement that is not installed, as one for another platform, is left out."""
    found: dict[str, Distribution] = {}
    pending = deque(_requirements(_distribution(DISTRIBUTION)))
    while pending:
        name = pending.popleft()
        dist = _distribution(name)
        if name in found or dist is None:
            continue
        found[name] = dist
        pending.extend(_requirements(dist))
    return found


def _requirements(dist: Distribution | None) -> list[str]:
    names = (requirement_name(line) for line in (dist.requires if dist else None) or ())
    return [name for name in names if name is not None]


def _license_text(dist: Distribution | None) -> str:
    """The license files in the package's `.dist-info`, each once, in the order it lists them."""
    if dist is None:
        return ""
    texts: list[str] = []
    for file in dist.files or ():
        if file.parts[0].endswith(".dist-info") and _LICENSE_FILE.match(file.name):
            path = Path(str(dist.locate_file(file)))
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text and text not in texts:
                texts.append(text)
    return "\n\n".join(texts)
