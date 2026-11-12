"""Small concept guides and paths written into a content root, for the tests of guides/
(docs/specs/guides.md)."""

import shutil
from pathlib import Path

from coding_study.domain.guide_markdown import (
    SVG_THEMES,
    GuideMarkdown,
    svg_file,
    svg_marker,
    text_marker,
)
from tests.helpers import CATALOG_PROBLEMS

DIAGRAM = "flowchart LR\n  accTitle: Buckets\n  accDescr: A key lands in a bucket.\n  k --> b\n"
SVG = '<svg width="40" height="20" xmlns="http://www.w3.org/2000/svg"><text>{theme}</text></svg>'
"""A small SVG drawing; its text names its theme."""
EXAMPLE = 'print("hi")\n'
LEDGER = "0311-tamper-evident-ledger"
"""A progressive catalog problem with four levels, for level targets."""


def guide_markdown(title: str, problems: tuple[str, ...] = (), example: bool = True) -> str:
    practice = "\n".join(f"- `cstudy start {slug}`" for slug in problems) or "- Nothing yet."
    embedded = (
        f"```python examples/hello.py\n{EXAMPLE}```\n\n```output examples/hello.py\nhi\n```\n\n"
        if example
        else ""
    )
    return (
        f"# {title}\n\n## The idea\n\nA table.\n\n```mermaid\n{DIAGRAM}```\n\n"
        f"{text_marker(DIAGRAM)}\n```text\n[k] --> [b]\n```\n\n"
        f"## A worked example\n\n{embedded}"
        "## When to use it\n\nOften.\n\n## Common traps\n\nMutable keys.\n\n"
        "## Complexity\n\nO(1) on average.\n\n## Expert notes\n\nDepth.\n\n"
        f"## Practice\n\n{practice}\n\n"
        "## Further reading\n\n- [Docs](https://docs.python.org/3/)\n"
    )


def write_guide(
    root: Path,
    slug: str,
    title: str,
    *,
    level: str = "intro",
    prerequisites: tuple[str, ...] = (),
    problems: tuple[str, ...] = (),
    markdown: str | None = None,
) -> Path:
    folder = root / "guides" / slug
    (folder / "examples").mkdir(parents=True, exist_ok=True)
    (folder / "examples" / "hello.py").write_text(EXAMPLE)
    lines = [f"title: {title}", "summary: A short summary.", f"level: {level}"]
    if prerequisites:
        lines.append(f"prerequisites: [{', '.join(prerequisites)}]")
    if problems:
        lines.append(f"problems: [{', '.join(problems)}]")
    (folder / "meta.yaml").write_text("\n".join(lines) + "\n")
    text = guide_markdown(title, problems) if markdown is None else markdown
    (folder / "guide.md").write_text(text)
    write_svg_drawings(folder, text)
    return folder


def write_svg_drawings(folder: Path, markdown: str) -> None:
    """A light and a dark SVG for each diagram of `markdown`, as `pnpm render` writes them."""
    for position, diagram in enumerate(GuideMarkdown(markdown).mermaid_fences(), start=1):
        for theme in SVG_THEMES:
            path = folder / "diagrams" / svg_file(position, theme)
            path.parent.mkdir(exist_ok=True)
            path.write_text(f"{svg_marker(diagram.content)}\n{SVG.format(theme=theme)}\n")


def write_path(root: Path, slug: str, steps: list[str], title: str = "Hashing") -> Path:
    folder = root / "guides" / "paths"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{slug}.yaml"
    body = "\n".join(f"  - {step}" for step in steps)
    path.write_text(f"title: {title}\nsummary: From hash functions on.\nsteps:\n{body}\n")
    return path


def add_ledger(root: Path) -> None:
    """Copies the catalog's tamper-evident-ledger, a progressive problem, into `root`."""
    shutil.copytree(CATALOG_PROBLEMS / LEDGER, root / "problems" / LEDGER)


def write_hashing(root: Path) -> None:
    """Two guides and a path over two-sum and the ledger's level 2."""
    add_ledger(root)
    write_guide(root, "hash-functions", "Hash functions")
    write_guide(
        root,
        "hash-maps",
        "Hash maps",
        prerequisites=("hash-functions",),
        problems=("two-sum",),
    )
    write_path(
        root,
        "hashing",
        [
            "guide: hash-functions",
            "guide: hash-maps",
            "problem: two-sum",
            "{problem: tamper-evident-ledger, level: 2}",
        ],
    )
