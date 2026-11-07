"""`cstudy about` (docs/specs/cli.md#cstudy-about): the version, the license, where to find cstudy,
and whose software it uses. It needs no workspace and reads no configuration."""

from typing import Annotated

import typer
from rich.text import Text

from coding_study.adapters.installed_packages import InstalledSoftware
from coding_study.adapters.workspace_marker import tool_version
from coding_study.application.about import read_about, read_license_texts
from coding_study.domain.about import About, CreditSection
from coding_study.domain.errors import UsageError
from coding_study.entrypoints.commands.export import labelled
from coding_study.entrypoints.shared import add_command, console
from coding_study.entrypoints.web import STATIC_DIRECTORY

NAME = "about"
CHOOSE_ONE = "choose one of --credits and --licenses"
COLUMN_GAP = 2


def register(app: typer.Typer) -> None:
    add_command(app, about, NAME)


def about(
    context: typer.Context,
    credits: Annotated[
        bool, typer.Option("--credits", help="List the software cstudy uses, instead.")
    ] = False,
    licenses: Annotated[
        bool, typer.Option("--licenses", help="Print the full license texts, instead.")
    ] = False,
) -> None:
    """Show the version, the license, the links and the credits."""
    if credits and licenses:
        raise UsageError(CHOOSE_ONE)
    packages = InstalledSoftware(STATIC_DIRECTORY)
    output = console(context)
    if licenses:
        output.print(Text(read_license_texts(packages)))
        return
    found = read_about(tool_version(), packages)
    for line in _credit_lines(found.credits) if credits else _summary_lines(found):
        output.print(line)


def _summary_lines(found: About) -> list[Text]:
    return [
        Text(f"cstudy {found.version}"),
        labelled("license", found.license),
        labelled(found.website.label.lower(), found.website.url),
        *(labelled(link.label.lower(), link.url) for link in found.links),
        *(
            labelled("sponsor" if index == 0 else "", link.url)
            for index, link in enumerate(found.sponsor)
        ),
        Text(),
        labelled("credits", "cstudy about --credits"),
        labelled("licenses", "cstudy about --licenses"),
    ]


def _credit_lines(sections: tuple[CreditSection, ...]) -> list[Text]:
    lines: list[Text] = []
    for section in sections:
        lines.extend((Text(section.title, style="bold"), *_credit_rows(section), Text()))
    return lines[:-1]


def _credit_rows(section: CreditSection) -> list[Text]:
    name_width = max(len(credit.name) for credit in section.credits) + COLUMN_GAP
    version_width = max(len(credit.version) for credit in section.credits) + COLUMN_GAP
    rows = (
        f"  {credit.name:<{name_width}}{credit.version:<{version_width}}{credit.license}"
        for credit in section.credits
    )
    return [Text(row.rstrip()) for row in rows]
