from collections.abc import Mapping
from dataclasses import replace

import pytest

from coding_study.domain.concept_guides import GuideLevel, GuideMeta, LearningPath, PathStep
from coding_study.domain.guide_checks import (
    CatalogFacts,
    GuideContent,
    guide_static_checks,
    path_static_checks,
)
from coding_study.domain.guide_markdown import text_marker

DIRECTORY = "guides/hash-maps"
DIAGRAM = "flowchart LR\n  accTitle: Buckets\n  accDescr: Two buckets.\n  a --> b\n"
EXAMPLE = 'print("hi")\n'
META = GuideMeta(
    slug="hash-maps",
    title="Hash maps",
    summary="Lookups in constant time on average.",
    level=GuideLevel.INTRO,
    prerequisites=("hash-functions",),
    problems=("two-sum",),
)
FUNCTIONS = GuideMeta(
    slug="hash-functions", title="Hash functions", summary="s", level=GuideLevel.INTRO
)
CATALOG = CatalogFacts(
    guides={"hash-maps": META, "hash-functions": FUNCTIONS},
    problems={"two-sum": 0, "ledger": 4},
)


def guide_markdown(
    *,
    title: str = "Hash maps",
    diagram: str = DIAGRAM,
    marker: str | None = None,
    drawing: str = "[a] --> [b]",
    example: str = EXAMPLE,
    practice: str = "- `cstudy start two-sum`: pairs that add up.",
    reading: str = "- [Python dict](https://docs.python.org/3/library/stdtypes.html#dict)",
) -> str:
    marker = text_marker(diagram) if marker is None else marker
    return (
        f"# {title}\n\n## The idea\n\nA table.\n\n```mermaid\n{diagram}```\n\n{marker}\n"
        f"```text\n{drawing}\n```\n\n## A worked example\n\n"
        f"```python examples/hello.py\n{example}```\n\n```output examples/hello.py\nhi\n```\n\n"
        "## When to use it\n\nOften.\n\n## Common traps\n\nMutable keys.\n\n"
        "## Complexity\n\nO(1) on average.\n\n## Expert notes\n\nDepth.\n\n"
        f"## Practice\n\n{practice}\n\n## Further reading\n\n{reading}\n"
    )


def content(
    markdown: str | None = None,
    files: tuple[str, ...] = ("meta.yaml", "guide.md", "examples/hello.py"),
    examples: Mapping[str, str] | None = None,
    meta: GuideMeta = META,
) -> GuideContent:
    return GuideContent(
        directory=DIRECTORY,
        meta=meta,
        markdown=guide_markdown() if markdown is None else markdown,
        files=files,
        examples={"examples/hello.py": EXAMPLE} if examples is None else examples,
    )


def messages(found: object) -> list[str]:
    return [str(issue) for issue in found]  # type: ignore[attr-defined]


def test_a_complete_guide_passes():
    assert messages(guide_static_checks(content(), CATALOG)) == []


def test_g2_a_folder_holds_nothing_but_the_guide_files():
    found = guide_static_checks(content(files=("meta.yaml", "guide.md", "diagram.svg")), CATALOG)
    assert messages(found) == [
        'guides/hash-maps: "diagram.svg" does not belong in a guide: '
        "a guide holds meta.yaml, guide.md and examples/"
    ]


def test_g2_examples_hold_files_only():
    files = ("meta.yaml", "guide.md", "examples/hello.py", "examples/lib/x.py")
    examples = {"examples/hello.py": EXAMPLE, "examples/lib/x.py": ""}
    found = guide_static_checks(content(files=files, examples=examples), CATALOG)
    assert (
        'guides/hash-maps: "examples/lib/x.py" does not belong in a guide' in (messages(found)[0])
    )


def test_g2_a_guide_may_not_be_called_paths():
    found = guide_static_checks(content(meta=replace(META, slug="paths")), CATALOG)
    assert messages(found) == ['guides/hash-maps: "paths" is reserved for the paths folder']


def test_g3_a_missing_guide_md_fails():
    found = guide_static_checks(GuideContent(DIRECTORY, META, None, ("meta.yaml",), {}), CATALOG)
    assert messages(found) == ["guides/hash-maps/guide.md: missing"]


def test_g3_the_heading_repeats_the_title():
    found = guide_static_checks(content(guide_markdown(title="Hash tables")), CATALOG)
    assert messages(found) == ['guides/hash-maps/guide.md: title "Hash tables" must be "Hash maps"']


def test_g3_every_section_is_there_and_in_order():
    markdown = guide_markdown().replace("## Expert notes\n\nDepth.\n\n", "")
    markdown = markdown.replace("## Complexity", "## Expert notes\n\nDepth.\n\n## Complexity")
    markdown = markdown.replace("## Common traps\n\nMutable keys.\n\n", "")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        'guides/hash-maps/guide.md: missing "## Common traps"',
        'guides/hash-maps/guide.md: "## Complexity" must come before "## Expert notes"',
    ]


def test_g3_a_section_may_not_be_empty():
    markdown = guide_markdown().replace("## When to use it\n\nOften.\n", "## When to use it\n")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        'guides/hash-maps/guide.md: "## When to use it" is empty'
    ]


def test_g3_other_sections_may_come_between():
    markdown = guide_markdown().replace(
        "## When to use it", "## Open addressing\n\nProbe.\n\n## When to use it"
    )
    assert messages(guide_static_checks(content(markdown), CATALOG)) == []


def test_g3_no_todo():
    markdown = guide_markdown().replace("Often.", "TODO: say when.")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        "guides/hash-maps/guide.md: contains TODO"
    ]


def test_g4_links_name_guides_and_problems_that_exist():
    meta = replace(META, prerequisites=("hashing-101",), related=("hash-maps",), problems=("x",))
    markdown = guide_markdown(practice="- `cstudy start x`: something.")
    assert messages(guide_static_checks(content(markdown, meta=meta), CATALOG)) == [
        'guides/hash-maps/meta.yaml: prerequisites: "hashing-101" is not a guide',
        "guides/hash-maps/meta.yaml: related: a guide does not link to itself",
        'guides/hash-maps/meta.yaml: problems: "x" is not a problem',
    ]


def test_g4_every_problem_is_named_in_practice():
    meta = replace(META, problems=("two-sum", "ledger"))
    assert messages(guide_static_checks(content(meta=meta), CATALOG)) == [
        'guides/hash-maps/guide.md: "## Practice" does not name problem "ledger"'
    ]


def test_g4_a_slug_inside_a_longer_slug_does_not_count():
    meta = replace(META, problems=("two-sum",))
    markdown = guide_markdown(practice="- `cstudy start two-sum-ii`: sorted.")
    assert messages(guide_static_checks(content(markdown, meta=meta), CATALOG)) == [
        'guides/hash-maps/guide.md: "## Practice" does not name problem "two-sum"'
    ]


def test_g5_prerequisites_form_no_cycle():
    looping = replace(FUNCTIONS, prerequisites=("hash-maps",))
    catalog = replace(CATALOG, guides={"hash-maps": META, "hash-functions": looping})
    assert messages(guide_static_checks(content(), catalog)) == [
        "guides/hash-maps/meta.yaml: prerequisites: they form a cycle: "
        "hash-maps -> hash-functions -> hash-maps"
    ]


def test_g6_an_embedded_example_matches_its_file():
    found = guide_static_checks(content(examples={"examples/hello.py": 'print("bye")\n'}), CATALOG)
    assert messages(found) == [
        "guides/hash-maps/guide.md: line 21: the copy of examples/hello.py differs from the file"
    ]


def test_g6_an_example_names_a_file_that_exists():
    found = guide_static_checks(content(files=("meta.yaml", "guide.md"), examples={}), CATALOG)
    assert messages(found) == [
        "guides/hash-maps/guide.md: line 21: examples/hello.py does not exist"
    ]


def test_g6_every_example_file_is_embedded():
    files = ("meta.yaml", "guide.md", "examples/hello.py", "examples/extra.py")
    examples = {"examples/hello.py": EXAMPLE, "examples/extra.py": "print(2)\n"}
    found = guide_static_checks(content(files=files, examples=examples), CATALOG)
    assert messages(found) == ["guides/hash-maps/guide.md: examples/extra.py is never embedded"]


def test_g6_an_example_is_embedded_once():
    markdown = guide_markdown().replace(
        "## When to use it", f"```python examples/hello.py\n{EXAMPLE}```\n\n## When to use it"
    )
    assert (
        "examples/hello.py is embedded 2 times"
        in messages(guide_static_checks(content(markdown), CATALOG))[0]
    )


def test_g6_every_example_has_one_output_block():
    markdown = guide_markdown().replace("```output examples/hello.py\nhi\n```\n", "")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        "guides/hash-maps/guide.md: examples/hello.py needs one output block, not 0"
    ]


def test_g6_an_output_block_names_an_embedded_example():
    markdown = guide_markdown().replace(
        "## When to use it", "```output examples/other.py\nx\n```\n\n## When to use it"
    )
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        "guides/hash-maps/guide.md: line 29: output of examples/other.py, which is not embedded"
    ]


def test_g6_the_language_fits_the_extension():
    markdown = guide_markdown().replace("```python examples/hello.py", "```go examples/hello.py")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        'guides/hash-maps/guide.md: line 21: examples/hello.py is embedded as "go"; use "python"'
    ]


def test_g6_an_example_has_a_supported_extension():
    files = ("meta.yaml", "guide.md", "examples/hello.rb")
    markdown = guide_markdown().replace("python examples/hello.py", "ruby examples/hello.rb")
    markdown = markdown.replace("output examples/hello.py", "output examples/hello.rb")
    found = guide_static_checks(
        content(markdown, files=files, examples={"examples/hello.rb": EXAMPLE}), CATALOG
    )
    assert messages(found) == [
        "guides/hash-maps/guide.md: line 21: examples/hello.rb: an example is .go, .java, .js, "
        ".mjs or .py"
    ]


@pytest.mark.parametrize(
    ("diagram", "message"),
    [
        ("pie\n  accTitle: t\n  accDescr: d\n", 'starts with "pie", which is not a type'),
        (
            "flowchart\n  accTitle: t\n  accDescr: d\n",
            'starts with "flowchart", which is not a type',
        ),
        ("flowchart LR\n  accDescr: d\n  a --> b\n", "has no accTitle line"),
        ("sequenceDiagram\n  accTitle: t\n  A->>B: hi\n", "has no accDescr line"),
    ],
)
def test_g7_a_diagram_has_a_known_type_and_its_accessibility_lines(diagram: str, message: str):
    found = guide_static_checks(content(guide_markdown(diagram=diagram)), CATALOG)
    assert messages(found) == [f"guides/hash-maps/guide.md: line 7: the diagram {message}"]


@pytest.mark.parametrize(
    "first_line",
    ["graph TD", "flowchart RL", "stateDiagram-v2", "stateDiagram", "classDiagram", "erDiagram"],
)
def test_g7_every_supported_type_passes(first_line: str):
    diagram = f"{first_line}\n  accTitle: t\n  accDescr {{\n    long\n  }}\n"
    assert messages(guide_static_checks(content(guide_markdown(diagram=diagram)), CATALOG)) == []


def test_g8_a_stale_drawing_fails_and_says_how_to_redraw_it():
    stale = text_marker(DIAGRAM.replace("a --> b", "a --> c"))
    found = guide_static_checks(content(guide_markdown(marker=stale)), CATALOG)
    assert messages(found) == [
        "guides/hash-maps/guide.md: line 7: the text drawing is stale: "
        "run pnpm render in tools/guides/"
    ]


def test_g8_a_missing_drawing_fails():
    markdown = guide_markdown(marker="Prose instead.")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        "guides/hash-maps/guide.md: line 7: the diagram has no text drawing: "
        "run pnpm render in tools/guides/"
    ]


def test_g8_a_drawing_fits_100_columns():
    found = guide_static_checks(content(guide_markdown(drawing="x" * 101)), CATALOG)
    assert messages(found) == [
        "guides/hash-maps/guide.md: line 16: the text drawing is 101 characters wide; "
        "at most 100 fit: simplify the diagram"
    ]


def test_g8_a_marker_without_its_diagram_fails():
    markdown = guide_markdown().replace(
        "## When to use it", f"{text_marker(DIAGRAM)}\n```text\nx\n```\n\n## When to use it"
    )
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        "guides/hash-maps/guide.md: line 29: a text-drawing marker with no diagram before it"
    ]


def test_g9_further_reading_has_a_link():
    markdown = guide_markdown(reading="A good book.")
    assert messages(guide_static_checks(content(markdown), CATALOG)) == [
        'guides/hash-maps/guide.md: "## Further reading" has no https:// link'
    ]


PATH = LearningPath(
    slug="hashing",
    title="Hashing",
    summary="From hash functions to ledgers.",
    steps=(
        PathStep.guide("hash-functions"),
        PathStep.guide("hash-maps"),
        PathStep.problem("two-sum"),
        PathStep.problem("ledger", level=2),
    ),
)
PATH_FILE = "guides/paths/hashing.yaml"


def test_a_sound_path_passes():
    assert messages(path_static_checks(PATH_FILE, PATH, CATALOG)) == []


def test_p1_the_file_name_is_a_slug():
    path = replace(PATH, slug="Hashing_1")
    assert messages(path_static_checks("guides/paths/Hashing_1.yaml", path, CATALOG)) == [
        "guides/paths/Hashing_1.yaml: the name must be a kebab-case slug, such as hashing"
    ]


def test_p2_every_step_resolves():
    path = replace(PATH, steps=(*PATH.steps, PathStep.guide("nope"), PathStep.problem("gone")))
    assert messages(path_static_checks(PATH_FILE, path, CATALOG)) == [
        'guides/paths/hashing.yaml: steps[4]: "nope" is not a guide',
        'guides/paths/hashing.yaml: steps[5]: "gone" is not a problem',
    ]


def test_p3_a_level_fits_the_problem():
    path = replace(
        PATH, steps=(*PATH.steps[:3], PathStep.problem("two-sum", 1), PathStep.problem("ledger", 5))
    )
    assert messages(path_static_checks(PATH_FILE, path, CATALOG)) == [
        "guides/paths/hashing.yaml: steps[3]: two-sum has no levels; "
        "a level fits a progressive or project problem",
        "guides/paths/hashing.yaml: steps[4]: ledger has 4 levels, not 5",
    ]


def test_p4_no_step_comes_twice():
    path = replace(
        PATH, steps=(*PATH.steps, PathStep.problem("two-sum"), PathStep.problem("ledger", 4))
    )
    assert messages(path_static_checks(PATH_FILE, path, CATALOG)) == [
        "guides/paths/hashing.yaml: steps[4]: the same step as steps[2]"
    ]


def test_p5_a_guide_comes_after_its_prerequisites():
    path = replace(PATH, steps=(PATH.steps[1], PATH.steps[0], *PATH.steps[2:]))
    assert messages(path_static_checks(PATH_FILE, path, CATALOG)) == [
        "guides/paths/hashing.yaml: steps[0]: hash-maps needs hash-functions as an earlier step"
    ]
