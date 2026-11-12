"""`cstudy learn` (docs/specs/cli.md#cstudy-learn)."""

import io
import json
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.learn import GuideEntry, LearnListing, PathView, guide_page
from coding_study.domain.concept_guides import (
    GuideLevel,
    GuideMeta,
    LearningPath,
    PathStep,
    StepProgress,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import learn
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, make_environment
from tests.guide_builders import write_hashing

runner = CliRunner()
HINT = "Read with rendered diagrams in the web UI: cstudy learn"


@pytest.fixture
def environment(content_root: Path, monkeypatch: pytest.MonkeyPatch) -> Environment:
    write_hashing(content_root)
    environment = make_environment(content_root)
    monkeypatch.setattr(learn, "load_environment", lambda *_: environment)
    monkeypatch.setattr(learn, "load_catalog_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["learn", *arguments])


def test_the_list_shows_the_guides_the_paths_and_what_comes_next(environment: Environment):
    lines = invoke().output.splitlines()
    assert lines == [
        "GUIDES",
        "SLUG                        LEVEL     READ  TITLE",
        "hash-functions              intro     -     Hash functions",
        "hash-maps                   intro     -     Hash maps",
        "",
        "PATHS",
        "hashing                     0 of 4 done     Hashing",
        "next      cstudy learn --path hashing",
        f"{HINT} <guide> --open",
    ]


def test_the_list_as_json_has_no_hint(environment: Environment):
    learn.mark_read(environment, "hash-maps")
    document = json.loads(invoke("--json").output)
    assert (document["guides"][1], document["paths"]) == (
        {
            "slug": "hash-maps",
            "title": "Hash maps",
            "summary": "A short summary.",
            "level": "intro",
            "prerequisites": ["hash-functions"],
            "related": [],
            "problems": ["two-sum"],
            "read": True,
            "read_at": NOW.isoformat(),
        },
        [
            {
                "slug": "hashing",
                "title": "Hashing",
                "summary": "From hash functions on.",
                "done": 1,
                "total": 4,
            }
        ],
    )


def test_no_guides_says_where_it_looked(content_root: Path, monkeypatch: pytest.MonkeyPatch):
    environment = make_environment(content_root)
    monkeypatch.setattr(learn, "load_catalog_environment", lambda *_: environment)
    assert invoke().output == f"no guides in {content_root}\n"


def test_a_guide_prints_as_markdown_with_its_diagrams_as_text(environment: Environment):
    output = invoke("hash-maps").output
    assert (
        output.startswith("# Hash maps\n"),
        "```mermaid" in output,
        "[k] --> [b]" in output,
        output.splitlines()[-2:],
    ) == (
        True,
        False,
        True,
        ["done      cstudy learn hash-maps --done", f"{HINT} hash-maps --open"],
    )


def test_a_guide_names_its_examples_folder(environment: Environment, content_root: Path):
    folder = content_root / "guides" / "hash-maps" / "examples"
    assert f"examples  {folder}" in invoke("hash-maps").output


def test_a_read_guide_says_when(environment: Environment):
    learn.mark_read(environment, "hash-maps")
    assert "read      2026-" in invoke("hash-maps").output


def test_on_a_terminal_a_guide_is_rendered_markdown(environment: Environment):
    buffer = io.StringIO()
    terminal = Console(file=buffer, force_terminal=True, width=100, color_system=None)
    learn._print_guide(terminal, guide_page(environment, "hash-maps"), as_json=False)
    text = buffer.getvalue()
    assert ("# Hash maps" in text, "Hash maps" in text, "[k] --> [b]" in text) == (
        False,
        True,
        True,
    )


def test_a_guide_as_json_holds_its_markdown_and_examples(environment: Environment):
    document = json.loads(invoke("hash-maps", "--json").output)
    assert (
        document["markdown"].startswith("# Hash maps"),
        [Path(name).name for name in document["examples"]],
    ) == (True, ["hello.py"])


def test_done_marks_the_guide_read_once(environment: Environment):
    assert (invoke("hash-maps", "--done").output, invoke("hash-maps", "--done").output) == (
        "marked hash-maps read\n",
        f"hash-maps was marked read on {NOW.date().isoformat()}\n",
    )


def test_done_as_json(environment: Environment):
    document = json.loads(invoke("hash-maps", "--done", "--json").output)
    assert document == {"slug": "hash-maps", "read_at": NOW.isoformat(), "already": False}


@pytest.fixture
def served(environment: Environment, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """The views `cstudy learn --open` asked the server to land on, which then stops at once as
    after Ctrl-C."""
    views: list[str] = []

    def run_server(_context: object, *, port: int, open_browser: bool, view: str | None) -> None:
        assert (port, open_browser) == (0, True)
        views.append(view or "")

    monkeypatch.setattr(learn, "run_server", run_server)
    return views


def test_open_serves_the_page_landing_on_the_guide(served: list[str]):
    result = invoke("hash-maps", "--open")
    assert (result.exit_code, served) == (ExitCode.SUCCESS, ["/guides/hash-maps"])


def test_open_with_a_path_lands_on_the_path(served: list[str]):
    result = invoke("--path", "hashing", "--open")
    assert (result.exit_code, served) == (ExitCode.SUCCESS, ["/paths/hashing"])


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("hash-map", "--open"), 'unknown guide "hash-map"; did you mean hash-maps'),
        (("--path", "hashin", "--open"), 'unknown path "hashin"; did you mean hashing'),
        (("hash-maps", "--open", "--done"), "--open takes no --done or --json"),
        (("hash-maps", "--open", "--json"), "--open takes no --done or --json"),
    ],
)
def test_open_starts_no_server_for_a_usage_error(
    served: list[str], arguments: tuple[str, ...], message: str
):
    result = invoke(*arguments)
    assert (result.exit_code, message in result.output, served) == (
        ExitCode.USAGE_ERROR,
        True,
        [],
    )


def test_a_path_shows_its_steps_and_the_next_command(environment: Environment):
    learn.mark_read(environment, "hash-functions")
    lines = invoke("--path", "hashing").output.splitlines()
    assert lines == [
        "hashing  Hashing",
        "From hash functions on.",
        "1 of 4 done",
        "#   KIND     STEP                       TARGET   STATUS          TITLE",
        "1   guide    hash-functions                      read            Hash functions",
        "2   guide    hash-maps                           not read        Hash maps",
        "3   problem  two-sum                             new             Two Sum",
        "4   problem  tamper-evident-ledger      level 2  new             Tamper-Evident Ledger",
        "next      cstudy learn hash-maps",
    ]


def test_a_path_as_json(environment: Environment):
    document = json.loads(invoke("--path", "hashing", "--json").output)
    assert (document["done"], document["total"], document["next"], document["steps"][3]) == (
        0,
        4,
        {
            "position": 1,
            "kind": "guide",
            "slug": "hash-functions",
            "title": "Hash functions",
            "level": None,
            "done": False,
            "status": "not read",
            "level_passed": None,
        },
        {
            "position": 4,
            "kind": "problem",
            "slug": "tamper-evident-ledger",
            "title": "Tamper-Evident Ledger",
            "level": 2,
            "done": False,
            "status": "new",
            "level_passed": 0,
        },
    )


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("hash-map",), 'unknown guide "hash-map"; did you mean hash-maps'),
        (("--path", "hashin"), 'unknown path "hashin"; did you mean hashing'),
        (("hash-maps", "--path", "hashing"), "give a guide or --path, not both"),
        (("--done",), "--done needs a guide"),
        (("--open",), "--open needs a guide or a path: cstudy learn <guide> --open"),
    ],
)
def test_usage_errors_exit_3(environment: Environment, arguments: tuple[str, ...], message: str):
    result = invoke(*arguments)
    assert (result.exit_code, message in result.output) == (ExitCode.USAGE_ERROR, True)


def test_a_path_with_long_slugs_keeps_its_columns_aligned():
    steps = tuple(
        StepProgress(PathStep.guide(slug), title, done=False, status="not read")
        for slug, title in (
            ("hash-maps", "Hash maps"),
            ("longest-substring-without-repeats", "Longest Substring"),
            ("longest-repeating-replacement", "Longest Repeating"),
        )
    )
    view = PathView(LearningPath("windows", "Windows", "Sliding windows.", ()), steps)
    buffer = io.StringIO()
    learn._print_path(Console(file=buffer, width=200), view, as_json=False)
    rows = buffer.getvalue().splitlines()[3:7]
    assert {
        row.index(label)
        for row, label in zip(
            rows, ("TITLE", "Hash maps", "Longest Substring", "Longest Repeating"), strict=True
        )
    } == {rows[0].index("TITLE")}
    assert {row.index("not read") for row in rows[1:]} == {rows[0].index("STATUS")}


def test_the_list_with_long_slugs_keeps_its_columns_aligned(environment: Environment):
    long_guide = "a-guide-whose-slug-is-longer-than-the-column"
    long_path = "a-path-whose-slug-is-longer-than-the-column"
    guides = tuple(
        GuideEntry(GuideMeta(slug, "Title", "Summary.", GuideLevel.CORE), None)
        for slug in ("short", long_guide)
    )
    paths = tuple(
        PathView(LearningPath(slug, "Path title", "Summary.", ()), ())
        for slug in ("short", long_path)
    )
    buffer = io.StringIO()
    learn._print_listing(
        Console(file=buffer, width=200), environment, LearnListing(guides, paths), as_json=False
    )
    lines = buffer.getvalue().splitlines()
    guide_rows = [line for line in lines if "Title" in line]
    path_rows = [line for line in lines if "Path title" in line]
    assert {row.index("core") for row in guide_rows} == {lines[1].index("LEVEL")}
    assert {row.index("0 of 0") for row in path_rows} == {len(long_guide) + 2}
