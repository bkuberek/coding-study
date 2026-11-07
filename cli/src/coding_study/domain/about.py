"""What `cstudy about` and the About view say of cstudy itself
(docs/specs/cli.md#cstudy-about): its license, where to find it, and whose software it uses."""

import re
from dataclasses import dataclass

LICENSE_NAME = "MIT"
WEBSITE = "https://coding-study.com"
SOURCE = "https://github.com/bkuberek/coding-study"


@dataclass(frozen=True, slots=True)
class Link:
    label: str
    url: str


WEBSITE_LINK = Link("Website", WEBSITE)
PROJECT_LINKS = (
    Link("Source", SOURCE),
    Link("Issues", f"{SOURCE}/issues"),
)
SPONSOR_LINKS = (
    Link("GitHub Sponsors", "https://github.com/sponsors/bkuberek"),
    Link("Ko-fi", "https://ko-fi.com/bkuberek"),
)
"""The targets of `.github/FUNDING.yml`; a test keeps the two the same."""

TOOLCHAINS = ("uv", "Node.js", "pnpm", "JDK", "Gradle", "Go", "Rust", "git")
"""What cstudy runs from the user's machine to build and run a solution
(docs/guides/toolchains.md); none of it ships with cstudy."""


@dataclass(frozen=True, slots=True)
class Credit:
    name: str
    version: str
    """Empty for what cstudy does not pin."""
    license: str
    """The license as the package declares it; empty when cstudy does not know it."""


@dataclass(frozen=True, slots=True)
class CreditSection:
    title: str
    credits: tuple[Credit, ...]


@dataclass(frozen=True, slots=True)
class About:
    version: str
    license: str
    website: Link
    links: tuple[Link, ...]
    sponsor: tuple[Link, ...]
    credits: tuple[CreditSection, ...]


NOTICE_RULE_WIDTH = 78
_NOTICE_HEADING = re.compile(
    rf"^-{{{NOTICE_RULE_WIDTH}}}\n(?P<name>\S+) (?P<version>\S+) \((?P<license>[^()\n]+)\)\n"
    rf"-{{{NOTICE_RULE_WIDTH}}}$",
    re.MULTILINE,
)


def web_ui_credits(notice: str) -> tuple[Credit, ...]:
    """The packages `THIRD_PARTY_LICENSES.txt` names, each under a heading of the form
    `name version (license)` between two rules, in the order the notice has them."""
    return tuple(
        Credit(found["name"], found["version"], found["license"])
        for found in _NOTICE_HEADING.finditer(notice)
    )
