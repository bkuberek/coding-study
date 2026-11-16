"""`cstudy learn` (docs/specs/cli.md#cstudy-learn)."""

import io
import json
from dataclasses import replace
from pathlib import Path

import pytest
from rich.console import Console
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.learn import (
    GuideEntry,
    LearnListing,
    PathView,
    guide_page,
    label_scope,
    learn_listing,
)
from coding_study.domain.concept_guides import (
    GuideLevel,
    GuideMeta,
    LearningPath,
    PathStep,
    StepProgress,
)
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.content_ids import ContentType
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import learn
from coding_study.entrypoints.shared import ExitCode
from tests.content_id_checks import content_ids_in
from tests.fakes import NOW, make_environment
from tests.guide_builders import write_guide, write_hashing, write_path

runner = CliRunner()
HINT = "Read with rendered diagrams in the web UI: cstudy learn"
LANG_PRINTS = (
    "--lang picks the language of a printed guide's examples: "
    "cstudy learn <guide> --lang <language>"
)


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
        "hashing                     intro     0 of 4 done     Hashing",
        "next      cstudy learn --path hashing",
        f"{HINT} <guide> --open",
    ]


def test_the_list_as_json_has_no_hint(environment: Environment):
    learn.mark_read(environment, "hash-maps")
    document = json.loads(invoke("--json").output)
    assert (document["guides"][1], document["paths"]) == (
        {
            "id": "guide/hash-maps",
            "slug": "hash-maps",
            "title": "Hash maps",
            "summary": "A short summary.",
            "level": "intro",
            "domains": ["algorithms"],
            "job_roles": ["general"],
            "prerequisites": ["hash-functions"],
            "related": [],
            "problems": ["two-sum"],
            "read": True,
            "read_at": NOW.isoformat(),
        },
        [
            {
                "id": "path/hashing",
                "slug": "hashing",
                "title": "Hashing",
                "summary": "From hash functions on.",
                "level": "intro",
                "guides": ["hash-functions", "hash-maps"],
                "done": 1,
                "total": 4,
            }
        ],
    )


def test_the_list_narrows_by_a_search_and_a_status(environment: Environment):
    learn.mark_read(environment, "hash-functions")
    assert invoke("--search", "maps", "--status", "not_read").output.splitlines() == [
        "GUIDES",
        "SLUG                        LEVEL     READ  TITLE",
        "hash-maps                   intro     -     Hash maps",
        "",
        "PATHS",
        'no paths match "maps", status: not read',
        f"{HINT} <guide> --open",
    ]


def test_a_narrowed_list_as_json_holds_what_matches(environment: Environment):
    document = json.loads(invoke("--level", "intro", "--search", "functions", "--json").output)
    assert ([guide["slug"] for guide in document["guides"]], document["paths"][0]["slug"]) == (
        ["hash-functions"],
        "hashing",
    )


def test_a_list_that_nothing_matches_says_what_was_asked(environment: Environment):
    assert invoke("--search", "zebra", "--level", "advanced").output.splitlines() == [
        "GUIDES",
        'no guides match "zebra", level: advanced',
        "",
        "PATHS",
        'no paths match "zebra", level: advanced',
    ]


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


@pytest.fixture
def variants(content_root: Path, environment: Environment) -> Environment:
    """hash-maps with its example in Python, TypeScript and Go."""
    write_guide(content_root, "hash-maps", "Hash maps", variants=True)
    return environment


def test_a_guide_shows_an_example_in_default_lang_and_names_its_other_languages(
    variants: Environment,
):
    output = invoke("hash-maps").output
    assert (
        "```python examples/hello.py" in output,
        "```typescript examples/hello.ts" in output,
        "Also in typescript, go: `cstudy learn hash-maps --lang <language>`" in output,
    ) == (True, False, True)


def test_lang_shows_every_example_that_has_it_in_that_language(variants: Environment):
    output = invoke("hash-maps", "--lang", "go").output
    assert (
        "```go examples/hello.go" in output,
        "```python examples/hello.py" in output,
        "Also in python, typescript: `cstudy learn hash-maps --lang <language>`" in output,
    ) == (True, False, True)


def test_a_language_no_example_has_shows_each_by_the_rule(variants: Environment):
    output = invoke("hash-maps", "--lang", "rust").output
    assert ("```python examples/hello.py" in output, "Also in typescript, go" in output) == (
        True,
        True,
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


def test_the_labels_of_a_guide_are_in_the_list_and_the_guide_as_json(
    environment: Environment, content_root: Path
):
    write_guide(
        content_root,
        "labeled",
        "Labeled",
        domains=("algorithms", "backend"),
        job_roles=("general",),
    )
    listing = json.loads(invoke("--json").output)
    guide = json.loads(invoke("labeled", "--json").output)
    labeled = next(entry for entry in listing["guides"] if entry["slug"] == "labeled")
    assert [(found["domains"], found["job_roles"]) for found in (labeled, guide)] == [
        (["algorithms", "backend"], ["general"])
    ] * 2


def test_a_guide_carries_its_labels_in_the_json(environment: Environment):
    document = json.loads(invoke("hash-maps", "--json").output)
    assert (document["domains"], document["job_roles"]) == (["algorithms"], ["general"])


def test_done_marks_the_guide_read_once(environment: Environment):
    assert (invoke("hash-maps", "--done").output, invoke("hash-maps", "--done").output) == (
        "marked hash-maps read\n",
        f"hash-maps was marked read on {NOW.date().isoformat()}\n",
    )


def test_done_as_json(environment: Environment):
    document = json.loads(invoke("hash-maps", "--done", "--json").output)
    assert document == {
        "id": "guide/hash-maps",
        "slug": "hash-maps",
        "read_at": NOW.isoformat(),
        "already": False,
    }


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
        (("hash-maps", "--open", "--lang", "go"), LANG_PRINTS),
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


def test_a_guide_and_a_path_of_one_slug_have_two_ids(environment: Environment):
    listing = json.loads(invoke("--json").output)
    guide = json.loads(invoke("hash-maps", "--json").output)
    path = json.loads(invoke("--path", "hashing", "--json").output)
    assert content_ids_in(listing) == [
        (ContentType.GUIDE, "hash-functions"),
        (ContentType.GUIDE, "hash-maps"),
        (ContentType.PATH, "hashing"),
    ]
    assert content_ids_in(guide) == [(ContentType.GUIDE, "hash-maps")]
    assert content_ids_in(path) == [
        (ContentType.PATH, "hashing"),
        (ContentType.GUIDE, "hash-functions"),
        (ContentType.GUIDE, "hash-functions"),
        (ContentType.GUIDE, "hash-maps"),
        (ContentType.PROBLEM, "two-sum"),
        (ContentType.PROBLEM, "tamper-evident-ledger"),
    ]


def test_a_path_as_json(environment: Environment):
    document = json.loads(invoke("--path", "hashing", "--json").output)
    assert (document["done"], document["total"], document["next"], document["steps"][3]) == (
        0,
        4,
        {
            "position": 1,
            "kind": "guide",
            "id": "guide/hash-functions",
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
            "id": "problem/tamper-evident-ledger",
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
        (("hash-maps", "--level", "core"), "--search, --level and --status narrow the list"),
        (("--path", "hashing", "--search", "x"), "--search, --level and --status narrow the list"),
        (("--lang", "go"), LANG_PRINTS),
        (("--path", "hashing", "--lang", "go"), LANG_PRINTS),
        (("hash-maps", "--done", "--lang", "go"), LANG_PRINTS),
        (("hash-maps", "--json", "--lang", "go"), LANG_PRINTS),
        (
            ("hash-maps", "--lang", "ruby"),
            'unknown language "ruby"; one of bash, python, typescript, java, kotlin, go, rust, '
            "javascript",
        ),
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
    assert {row[lines[1].index("LEVEL")] for row in path_rows} == {learn.NO_LEVEL}
    assert {row.index("0 of 0") for row in path_rows} == {len(long_guide) + 2 + learn.LEVEL_WIDTH}


# The learner profile, `--domain`, `--role` and `--widen` (docs/specs/cli.md#the-profile-line)

PROFILE_LINE = (
    "filtered by your profile: 1 of 4 guides, 2 of 3 paths · domains security · "
    "--widen all shows them all"
)


@pytest.fixture
def narrowed(environment: Environment, content_root: Path, monkeypatch: pytest.MonkeyPatch):
    """A security profile over hashing's two algorithms guides, one guide for security and one for
    data, each in a path of its own."""
    write_guide(content_root, "tls", "TLS", domains=("security",), job_roles=("security-engineer",))
    write_guide(content_root, "etl", "ETL", domains=("data",), job_roles=("data-engineer",))
    write_path(content_root, "secure", ["guide: tls"], title="Secure")
    write_path(content_root, "pipelines", ["guide: etl"], title="Pipelines")
    profile = ProfileSettings(domains=("security",))
    profiled = replace(make_environment(content_root), config=Config(profile=profile))
    monkeypatch.setattr(learn, "load_catalog_environment", lambda *_: profiled)
    return profiled


def listed(output: str) -> set[str]:
    rows = (line.split() for line in output.splitlines())
    return {row[0] for row in rows if row and row[0] not in {"GUIDES", "PATHS", "SLUG", "next"}}


def test_the_profile_narrows_the_list_and_the_line_ends_it_after_the_web_hint(narrowed):
    lines = invoke().output.splitlines()
    assert (lines[-2], lines[-1]) == (f"{HINT} <guide> --open", PROFILE_LINE)
    assert {"tls", "secure", "etl", "pipelines"} & listed(invoke().output) == {"tls", "secure"}


def test_widen_all_lists_everything_and_prints_no_line(narrowed):
    output = invoke("--widen", "all").output
    assert {"tls", "secure", "etl", "pipelines"} <= listed(output)
    assert "filtered by your profile" not in output


def test_widen_domain_drops_the_domains_and_the_line(narrowed):
    output = invoke("--widen", "domain").output
    assert ({"etl", "pipelines"} <= listed(output), "filtered by your profile" in output) == (
        True,
        False,
    )


def test_widen_repeats(narrowed):
    assert "filtered by your profile" not in invoke("--widen", "role", "--widen", "domain").output


def test_an_explicit_domain_replaces_the_profile_and_names_no_dimension(narrowed):
    output = invoke("--domain", "data").output
    assert ({"etl", "pipelines"} <= listed(output), {"tls", "secure"} & listed(output)) == (
        True,
        set(),
    )
    assert "filtered by your profile" not in output


def test_an_explicit_role_keeps_the_profile_line_for_the_domains(narrowed):
    lines = invoke("--role", "data-engineer").output.splitlines()
    assert lines[-1].startswith("filtered by your profile: ")
    assert "domains security" in lines[-1]
    assert "roles" not in lines[-1]


def test_a_profile_that_hides_nothing_prints_no_line(
    environment: Environment, monkeypatch: pytest.MonkeyPatch
):
    profile = ProfileSettings(domains=("algorithms",))
    profiled = replace(environment, config=Config(profile=profile))
    monkeypatch.setattr(learn, "load_catalog_environment", lambda *_: profiled)
    assert "filtered by your profile" not in invoke().output


def test_the_profile_line_counts_what_the_search_leaves(narrowed):
    line = invoke("--search", "etl").output.splitlines()[-1]
    assert line == (
        "filtered by your profile: 0 of 1 guides, 0 of 0 paths · domains security · "
        "--widen all shows them all"
    )


def test_json_carries_what_the_profile_hid_and_prints_no_line(narrowed):
    result = invoke("--json")
    document = json.loads(result.output)
    assert document["profile"] == {
        "languages": None,
        "job_roles": None,
        "domains": ["security"],
        "hidden": {"guides": 3, "paths": 1},
    }
    assert {guide["slug"] for guide in document["guides"]} == {"tls"}


def test_json_widened_has_null_values_and_zero_hidden(narrowed):
    document = json.loads(invoke("--json", "--widen", "all").output)
    assert document["profile"] == {
        "languages": None,
        "job_roles": None,
        "domains": None,
        "hidden": {"guides": 0, "paths": 0},
    }


def test_a_default_profile_gives_the_listing_it_always_gave(environment: Environment):
    document = json.loads(invoke("--json").output)
    assert document["profile"] == {
        "languages": None,
        "job_roles": None,
        "domains": None,
        "hidden": {"guides": 0, "paths": 0},
    }
    assert [guide["slug"] for guide in document["guides"]] == ["hash-functions", "hash-maps"]


def test_the_line_is_dim_on_a_terminal_and_plain_text_otherwise(narrowed):
    scope = label_scope(narrowed)
    plain, styled = io.StringIO(), io.StringIO()
    whole = learn_listing(narrowed)
    learn._print_listing(Console(file=plain, width=200), narrowed, whole, False, scope=scope)
    terminal = Console(file=styled, force_terminal=True, width=200, color_system="standard")
    learn._print_listing(terminal, narrowed, whole, False, scope=scope)
    assert plain.getvalue().splitlines()[-1] == PROFILE_LINE
    assert f"\x1b[2m{PROFILE_LINE}\x1b[0m" in styled.getvalue()


def test_an_unknown_domain_or_role_is_a_usage_error(narrowed):
    domain = invoke("--domain", "fintek")
    role = invoke("--role", "wizard")
    assert (domain.exit_code, role.exit_code) == (ExitCode.USAGE_ERROR, ExitCode.USAGE_ERROR)
    assert 'unknown domain "fintek"; use one of algorithms, backend' in domain.output
    assert 'unknown job role "wizard"; use one of general, backend' in role.output


@pytest.mark.parametrize("value", ["lang", "everything"])
def test_a_widening_a_guide_cannot_take_is_a_usage_error(narrowed, value: str):
    result = invoke("--widen", value)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert f'unknown widening "{value}"; cstudy learn takes role, domain, all' in result.output


@pytest.mark.parametrize("flags", [("--domain", "data"), ("--role", "backend"), ("--widen", "all")])
@pytest.mark.parametrize("target", [("hash-maps",), ("--path", "hashing")])
def test_the_profile_flags_apply_to_the_list_not_to_a_guide_or_a_path(
    narrowed, flags: tuple[str, ...], target: tuple[str, ...]
):
    result = invoke(*target, *flags)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert "apply to the list" in result.output


def test_a_guide_and_a_path_ignore_the_profile(narrowed):
    assert invoke("etl").exit_code == ExitCode.SUCCESS
    assert "filtered by your profile" not in invoke("etl").output
    assert invoke("--path", "pipelines").exit_code == ExitCode.SUCCESS
