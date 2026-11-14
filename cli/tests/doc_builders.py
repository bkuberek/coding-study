"""Small user pages written into a content root, for the tests of user-docs/
(docs/specs/user-docs.md)."""

from pathlib import Path

from coding_study.domain.doc_checks import CommandSpec

START = "Start here"
PRACTISE = "Practise"
ROOT_COMMANDS = CommandSpec(
    options={"--help": False, "--no-color": False, "--workspace": True},
    subcommands={
        "doctor": CommandSpec(options={"--help": False, "--fix": False, "--json": False}),
        "start": CommandSpec(options={"--help": False, "--lang": True}),
        "set": CommandSpec(
            options={"--help": False},
            subcommands={"add": CommandSpec(options={"--help": False, "--level": True})},
        ),
    },
)
"""A small command line: `cstudy doctor`, `cstudy start` and `cstudy set add`."""


def page_text(
    title: str,
    body: str = "Some words.\n",
    *,
    summary: str = "A short summary.",
    section: str = START,
    order: int = 10,
) -> str:
    return (
        f"---\ntitle: {title}\nsummary: {summary}\nsection: {section}\norder: {order}\n---\n\n"
        f"# {title}\n\n{body}"
    )


def write_page(root: Path, slug: str, text: str) -> Path:
    folder = root / "user-docs"
    folder.mkdir(exist_ok=True)
    path = folder / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return path


def write_docs(root: Path) -> None:
    """Three pages in two sections, linking each other."""
    write_page(
        root,
        "getting-started",
        page_text(
            "Getting started",
            "Install it, then run `cstudy doctor`.\n\n## Install\n\n"
            "```bash\ncstudy doctor --fix\n```\n\n"
            "Read [the checks](doctor.md#the-rows) next.\n",
            summary="Install cstudy and solve a first problem.",
            order=10,
        ),
    )
    write_page(
        root,
        "doctor",
        page_text(
            "Check your setup",
            "It checks each tool.\n\n## The rows\n\nOne per tool.\n\n### `--fix`\n\n"
            "It sets up the workspace.\n",
            summary="What cstudy doctor checks.",
            order=20,
        ),
    )
    write_page(
        root,
        "practice",
        page_text(
            "Work on a problem",
            "Start one with `cstudy start two-sum --lang go`.\n\n## Hints\n\nAsk for one.\n",
            summary="Start, test, hints and done.",
            section=PRACTISE,
            order=30,
        ),
    )
