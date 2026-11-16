"""The static checks of the user docs, D2 to D6 (docs/specs/user-docs.md#static-checks), and the
commands a page names (docs/specs/user-docs.md#accuracy)."""

import pytest

from coding_study.domain.doc_checks import (
    command_issues,
    command_mentions,
    folder_issues,
    order_issues,
    page_static_checks,
)
from coding_study.domain.user_docs import DocPage
from tests.doc_builders import ROOT_COMMANDS

FILE = "user-docs/doctor.md"


def doc(slug: str, markdown: str, *, section: str = "Start", order: int = 10) -> DocPage:
    return DocPage(slug, "Doctor", "A summary.", section, order, markdown, first_line=6)


DOCTOR = doc("doctor", "# Doctor\n\n## The rows\n\nOne per tool.\n")
OTHER = doc("other", "# Other\n\n## Install\n\nSteps.\n", order=20)
PAGES = {"doctor": DOCTOR, "other": OTHER}


def issues_of(markdown: str) -> list[str]:
    page = doc("doctor", markdown)
    return [str(issue) for issue in page_static_checks(FILE, page, {**PAGES, "doctor": page})]


def commands_in(markdown: str) -> list[str]:
    return [str(issue) for issue in command_issues(FILE, doc("doctor", markdown), ROOT_COMMANDS)]


def test_a_sound_page_passes():
    assert issues_of("# Doctor\n\n## The rows\n\nSee [install](other.md#install).\n") == []


@pytest.mark.parametrize(
    ("markdown", "expected"),
    [
        ("Intro.\n", "user-docs/doctor.md: line 7: starts with # Doctor"),
        ("# Doctors\n", "user-docs/doctor.md: line 7: starts with # Doctor"),
        ("# Doctor\n\nTODO: write it\n", "user-docs/doctor.md: line 9: holds TODO"),
        ("# Doctor\n\nPress <kbd>S</kbd>.\n", "user-docs/doctor.md: line 9: holds HTML: <kbd>"),
        (
            "# Doctor\n\n![A screen](screen.png)\n",
            "user-docs/doctor.md: line 9: holds an image, which does not ship",
        ),
    ],
)
def test_d3_the_title_no_todo_no_html_and_no_image(markdown: str, expected: str):
    assert issues_of(markdown) == [expected]


def test_d3_html_and_images_in_code_are_text():
    assert issues_of("# Doctor\n\nType `<slug>` or `![x](y)`.\n\n```text\n<kbd>\n```\n") == []


@pytest.mark.parametrize(
    ("link", "message"),
    [
        ("missing.md", 'links to missing.md: there is no page "missing"'),
        ("other.md#nowhere", 'links to other.md#nowhere: other.md has no heading "nowhere"'),
        ("#nowhere", 'links to #nowhere: doctor.md has no heading "nowhere"'),
        (
            "../docs/specs/cli.md",
            "links to ../docs/specs/cli.md: link to a page (<slug>.md), a heading (#<id>) "
            "or an https:// address",
        ),
        (
            "http://example.org",
            "links to http://example.org: link to a page (<slug>.md), a heading (#<id>) "
            "or an https:// address",
        ),
    ],
)
def test_d5_every_link_names_a_page_and_heading_that_exist_or_the_web(link: str, message: str):
    assert issues_of(f"# Doctor\n\n## The rows\n\n[x]({link})\n") == [
        f"user-docs/doctor.md: line 11: {message}"
    ]


def test_d5_links_to_the_same_page_another_page_and_the_web_pass():
    markdown = (
        "# Doctor\n\n## The rows\n\n[a](#the-rows), [b](other.md), [c](other.md#install), "
        "[d](https://example.org/x#y)\n\n`[e](nowhere.md)`\n"
    )
    assert issues_of(markdown) == []


def test_d2_only_slug_named_markdown_files():
    assert [str(issue) for issue in folder_issues(("doctor.md", "Notes.md", "a.txt", "img/"))] == [
        "user-docs/Notes.md: not a page: a file named <slug>.md",
        "user-docs/a.txt: not a page: a file named <slug>.md",
        "user-docs/img/: not a page: a file named <slug>.md",
    ]


def test_d4_orders_are_unique_and_sections_follow_one_another():
    pages = (
        doc("a", "", section="Start", order=10),
        doc("b", "", section="Practice", order=20),
        doc("c", "", section="Start", order=30),
        doc("d", "", section="Practice", order=30),
    )
    found = order_issues(pages)
    assert {slug: [str(issue) for issue in issues] for slug, issues in found.items()} == {
        "c": [
            'user-docs/c.md: section: comes after a page of "Practice", apart from the other '
            'pages of "Start"'
        ],
        "d": [
            "user-docs/d.md: order: 30 is also the order of c",
            'user-docs/d.md: section: comes after a page of "Start", apart from the other '
            'pages of "Practice"',
        ],
    }


def test_commands_are_found_in_shell_blocks_and_inline_code_only():
    markdown = (
        "# Doctor\n\nRun `cstudy doctor --fix`.\n\n```bash\n$ cstudy start two-sum  # go\n```\n\n"
        "```python\nprint('cstudy start --nope')\n```\n\n"
        "| Command | Does |\n|--|--|\n| `cstudy done --rating easy\\|ok\\|hard` | x |\n"
    )
    assert [(mention.line, mention.text) for mention in command_mentions(markdown)] == [
        (2, "cstudy doctor --fix"),
        (5, "$ cstudy start two-sum  # go"),
        (14, "cstudy done --rating easy|ok|hard"),
    ]


KNOWN = """# D

```bash
cd ~/w && cstudy doctor --fix
CSTUDY_WORKSPACE=x cstudy start two-sum --lang=go
cstudy --workspace ~/w doctor [--json]
cstudy set add loop "a b" --level 2
uv run cstudy <command> --help
cstudy
brew upgrade cstudy
```
"""


def test_known_commands_and_flags_pass():
    assert commands_in(KNOWN) == []


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("cstudy doctr", "cstudy has no command doctr"),
        ("cstudy doctor --fixx", "cstudy doctor has no flag --fixx"),
        ("cstudy set ad loop", "cstudy set has no command ad"),
        ("cstudy set add loop --lang go", "cstudy set add has no flag --lang"),
        ("cstudy doctor --workspace ~/w", "cstudy doctor has no flag --workspace"),
    ],
)
def test_unknown_commands_and_flags_are_issues(command: str, message: str):
    assert commands_in(f"# D\n\nRun `{command}`.\n") == [f"user-docs/doctor.md: line 9: {message}"]


def test_words_after_end_of_options_and_a_value_are_not_flags():
    assert commands_in("# D\n\n`cstudy start two-sum --lang --x -- --anything`\n") == []


def test_a_terminals_text_is_read_at_its_prompts_and_fixes_only():
    markdown = (
        "# D\n\n```text\nWARN gopls 0.23.0 installed; cstudy needs 0.24.0\n"
        "$ cstudy doctor --fixx\n      fix: cstudy doctor --json --nope\n```\n"
    )
    assert commands_in(markdown) == [
        "user-docs/doctor.md: line 11: cstudy doctor has no flag --fixx",
        "user-docs/doctor.md: line 12: cstudy doctor has no flag --nope",
    ]


def test_text_that_a_shell_cannot_split_is_split_at_spaces():
    assert commands_in("# D\n\n```text\nfix: it's stale; cstudy doctor --fixx\n```\n") == [
        "user-docs/doctor.md: line 10: cstudy doctor has no flag --fixx"
    ]
