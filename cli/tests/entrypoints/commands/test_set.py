"""`cstudy set`, and `--set` on `cstudy list` and `cstudy next` (docs/specs/cli.md#cstudy-set)."""

import json
from dataclasses import replace
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import list_problems, next_problem, problem_sets
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
LOOP = "backend-loop"


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))
    for module in (problem_sets, list_problems, next_problem):
        monkeypatch.setattr(module, "load_environment", lambda *_: environment)
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: environment)
    return environment


@pytest.fixture
def file(tmp_path: Path) -> Path:
    return tmp_path / "sets.yaml"


def invoke(*arguments: str, typed: str | None = None):
    return runner.invoke(cli.app, ["set", *arguments], input=typed)


def looped(*slugs: str) -> None:
    invoke("create", LOOP)
    if slugs:
        invoke("add", LOOP, *slugs)


def finish(environment, slug: str, status: AttemptStatus = AttemptStatus.PASSED) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(replace(attempt, status=status, ended_at=NOW, grade=Grade.OK))


def listed(*arguments: str) -> list[str]:
    output = runner.invoke(cli.app, ["list", *arguments]).output
    return [line.split()[1] for line in output.splitlines()[1:] if not line.startswith("missing")]


def test_set_with_no_subcommand_shows_its_help(environment):
    assert "create" in invoke().output


def test_create_says_what_it_made_and_what_comes_next(environment):
    assert invoke("create", LOOP).output.splitlines() == [
        f"created {LOOP}",
        f"next    cstudy set add {LOOP} <slug>",
    ]


def test_create_takes_a_description(environment, file):
    invoke("create", LOOP, "--description", "On the 12th")
    assert "description: On the 12th" in file.read_text()


def test_create_on_a_name_that_exists_exits_3(environment):
    looped()
    result = invoke("create", LOOP)
    assert (result.exit_code, f"set {LOOP} already exists" in result.output) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_a_bad_name_exits_3_and_says_what_to_use(environment):
    result = invoke("create", "Backend Loop")
    assert (result.exit_code, "such as backend-loop" in result.output) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_list_with_none_says_how_to_make_one(environment):
    assert invoke("list").output.strip() == "no sets yet: create one with cstudy set create <name>"


def test_list_shows_passed_of_total(environment):
    looped("two-sum", "lru-cache")
    finish(environment, "two-sum")
    assert "1 of 2 passed" in invoke("list").output


def test_list_shows_the_description(environment):
    invoke("create", LOOP, "--description", "On the 12th")
    assert "On the 12th" in invoke("list").output


def test_list_shows_a_missing_count(environment, file):
    file.write_text(f"sets:\n  {LOOP}:\n    problems:\n      - gone\n")
    assert "1 missing" in invoke("list").output


def test_list_json(environment, file):
    file.write_text(f"sets:\n  {LOOP}:\n    problems:\n      - two-sum\n      - gone\n")
    finish(environment, "two-sum")
    assert json.loads(invoke("list", "--json").stdout) == {
        "sets": [
            {
                "name": LOOP,
                "description": None,
                "slugs": ["two-sum", "gone"],
                "passed": 1,
                "total": 1,
                "missing": ["gone"],
            }
        ]
    }


def test_add_says_what_it_added(environment):
    looped()
    assert invoke("add", LOOP, "two-sum").output.strip() == f"added two-sum to {LOOP}"


def test_add_of_a_slug_already_there_does_nothing_and_says_so(environment):
    looped("two-sum")
    result = invoke("add", LOOP, "two-sum")
    assert (result.exit_code, result.output.strip()) == (
        ExitCode.SUCCESS,
        f"two-sum is already in {LOOP}",
    )


def test_add_of_an_unknown_slug_exits_3_with_a_suggestion(environment):
    looped()
    result = invoke("add", LOOP, "two-summ")
    assert (result.exit_code, "did you mean two-sum?" in result.output) == (
        ExitCode.USAGE_ERROR,
        True,
    )


def test_remove_says_what_it_removed(environment):
    looped("two-sum")
    assert invoke("remove", LOOP, "two-sum").output.strip() == f"removed two-sum from {LOOP}"


def test_remove_of_a_slug_not_there_does_nothing_and_says_so(environment):
    looped()
    result = invoke("remove", LOOP, "two-sum")
    assert (result.exit_code, result.output.strip()) == (
        ExitCode.SUCCESS,
        f"two-sum is not in {LOOP}",
    )


def test_move_says_where_it_went(environment):
    looped("two-sum", "lru-cache")
    assert invoke("move", LOOP, "two-sum", "2").output.strip() == (
        f"moved two-sum to 2 of 2 in {LOOP}"
    )


def test_move_outside_the_list_exits_3(environment):
    looped("two-sum")
    assert invoke("move", LOOP, "two-sum", "2").exit_code == ExitCode.USAGE_ERROR


def test_rename_says_so(environment):
    looped()
    assert invoke("rename", LOOP, "platform-loop").output.strip() == (
        f"renamed {LOOP} to platform-loop"
    )


def test_delete_asks_first_and_a_no_keeps_the_set(environment):
    looped()
    result = invoke("delete", LOOP, typed="n\n")
    assert ("Delete the set backend-loop" in result.output, "not deleted" in result.output) == (
        True,
        True,
    )
    assert LOOP in invoke("list").output


def test_delete_with_yes_asks_nothing(environment):
    looped()
    result = invoke("delete", LOOP, "--yes")
    assert (result.output.strip(), invoke("list").output.startswith("no sets yet")) == (
        f"deleted {LOOP}",
        True,
    )


def test_an_unknown_set_exits_3(environment):
    assert invoke("show", "nope").exit_code == ExitCode.USAGE_ERROR


def test_show_prints_the_rows_in_the_set_s_order(environment):
    looped("url-shortener", "two-sum")
    lines = invoke("show", LOOP).output.splitlines()
    assert [line.split()[2] for line in lines if line[:4].strip().isdigit()] == [
        "url-shortener",
        "two-sum",
    ]


def test_show_prints_the_counts_and_what_to_do_next(environment):
    looped("two-sum")
    output = invoke("show", LOOP).output
    assert ("0 of 1 passed" in output, f"cstudy next --set {LOOP}" in output) == (True, True)


def test_show_marks_a_slug_the_catalog_lost_and_exits_0(environment, file):
    file.write_text(f"sets:\n  {LOOP}:\n    problems:\n      - gone\n")
    result = invoke("show", LOOP)
    line = next(line for line in result.output.splitlines() if "gone" in line)
    assert (result.exit_code, "missing" in line) == (ExitCode.SUCCESS, True)


def test_show_json_holds_each_row_with_its_list_entry(environment, file):
    file.write_text(f"sets:\n  {LOOP}:\n    problems:\n      - two-sum\n      - gone\n")
    finish(environment, "two-sum")
    document = json.loads(invoke("show", LOOP, "--json").stdout)
    first, second = document["rows"]
    assert (
        document["name"],
        document["passed"],
        document["total"],
        document["missing"],
        document["today"],
        (first["position"], first["slug"], first["passed"], first["missing"]),
        first["entry"]["status"],
        second,
    ) == (
        LOOP,
        1,
        1,
        ["gone"],
        NOW.date().isoformat(),
        (1, "two-sum", True, False),
        "passed",
        {"position": 2, "slug": "gone", "passed": False, "missing": True, "entry": None},
    )


def test_a_file_that_does_not_parse_exits_4_naming_the_file(environment, file):
    file.write_text("sets: [unclosed\n")
    result = invoke("list")
    assert (result.exit_code, "sets.yaml: line 2" in result.output) == (
        ExitCode.ENVIRONMENT_ERROR,
        True,
    )


def test_list_without_set_does_not_read_a_file_that_does_not_parse(environment, file):
    file.write_text("sets: [unclosed\n")
    assert runner.invoke(cli.app, ["list"]).exit_code == ExitCode.SUCCESS


def test_next_without_set_does_not_read_a_file_that_does_not_parse(environment, file):
    file.write_text("sets: [unclosed\n")
    assert runner.invoke(cli.app, ["next"]).exit_code == ExitCode.SUCCESS


def test_list_set_lists_problems_and_items_in_the_set_s_order(environment):
    looped("url-shortener", "two-sum", "news-feed", "lru-cache")
    assert listed("--set", LOOP) == ["url-shortener", "two-sum", "news-feed", "lru-cache"]


def test_list_set_combines_with_the_other_filters(environment):
    looped("url-shortener", "two-sum", "lru-cache")
    assert listed("--set", LOOP, "--difficulty", "easy") == ["two-sum"]


def test_list_set_names_what_the_catalog_lost(environment, file):
    file.write_text(f"sets:\n  {LOOP}:\n    problems:\n      - two-sum\n      - gone\n")
    result = runner.invoke(cli.app, ["list", "--set", LOOP])
    assert (result.exit_code, result.output.splitlines()[-1]) == (
        ExitCode.SUCCESS,
        "missing from the catalog: gone",
    )


def test_list_set_json_is_the_rows_in_the_set_s_order_and_what_is_missing(environment, file):
    file.write_text(
        f"sets:\n  {LOOP}:\n    problems:\n      - url-shortener\n      - two-sum\n      - gone\n"
    )
    document = json.loads(runner.invoke(cli.app, ["list", "--set", LOOP, "--json"]).stdout)
    assert ([entry["slug"] for entry in document["entries"]], document["set"]) == (
        ["url-shortener", "two-sum"],
        {"name": LOOP, "missing": ["gone"]},
    )


def test_list_json_without_a_set_has_no_set_key(environment):
    assert "set" not in json.loads(runner.invoke(cli.app, ["list", "--json"]).stdout)


def test_list_set_with_an_unknown_set_exits_3(environment):
    assert runner.invoke(cli.app, ["list", "--set", "nope"]).exit_code == ExitCode.USAGE_ERROR


def test_list_set_needs_a_workspace(tmp_path, monkeypatch):
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(tmp_path / "nowhere"))
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(cli.app, ["list", "--set", LOOP])
    assert (result.exit_code, "cstudy init" in result.output) == (ExitCode.USAGE_ERROR, True)


def test_next_set_prints_the_pick_where_it_is_and_the_standing(environment):
    looped("two-sum", "lru-cache")
    finish(environment, "two-sum")
    assert runner.invoke(cli.app, ["next", "--set", LOOP]).output.splitlines() == [
        f"new     lru-cache  (medium · linked-list)  next in {LOOP}, 2 of 2",
        "start   cstudy start lru-cache --lang python",
        f"set     {LOOP}  1 of 2 passed",
    ]


def test_next_set_says_when_the_set_is_finished(environment):
    looped("two-sum")
    finish(environment, "two-sum")
    result = runner.invoke(cli.app, ["next", "--set", LOOP])
    assert (result.exit_code, result.output.strip()) == (
        ExitCode.SUCCESS,
        f"{LOOP} is finished: 1 of 1 passed",
    )


def test_next_set_says_the_set_is_finished_when_only_a_review_is_left(environment):
    looped("two-sum")
    finish(environment, "two-sum")
    state = ReviewState(interval_days=3, reps=1)
    environment.progress.save_schedule_entry(
        ScheduleEntry("two-sum", state, NOW.date(), Grade.OK, NOW)
    )
    assert runner.invoke(cli.app, ["next", "--set", LOOP]).output.splitlines() == [
        "review  two-sum  (easy · arrays-hashing)  due today, interval 3d",
        "start   cstudy start two-sum --lang python",
        f"set     {LOOP}  finished: 1 of 1 passed",
    ]


def test_next_set_start_starts_the_pick_and_says_how_the_set_stands(environment):
    looped("url-shortener")
    result = runner.invoke(cli.app, ["next", "--set", LOOP, "--start"])
    assert (result.exit_code, f"set     {LOOP}  0 of 1 passed" in result.output) == (
        ExitCode.SUCCESS,
        True,
    )
    assert environment.progress.attempts_in_progress()[0].slug == "url-shortener"


def test_next_set_says_when_the_set_is_empty(environment):
    looped()
    assert runner.invoke(cli.app, ["next", "--set", LOOP]).output.strip() == (
        f"{LOOP} is empty: add problems with cstudy set add {LOOP} <slug>"
    )


def test_next_set_says_when_nothing_is_in_the_catalog(environment, file):
    file.write_text(f"sets:\n  {LOOP}:\n    problems:\n      - gone\n")
    assert runner.invoke(cli.app, ["next", "--set", LOOP]).output.strip() == (
        f"nothing in {LOOP} is in the catalog: see cstudy set show {LOOP}"
    )


def test_next_set_keeps_the_message_of_a_filter_that_left_nothing(environment):
    looped("two-sum")
    assert runner.invoke(
        cli.app, ["next", "--set", LOOP, "--difficulty", "hard"]
    ).output.strip() == ("nothing due and no new problems in scope")


def test_next_set_json_keeps_every_field_and_adds_the_set(environment):
    looped("two-sum", "lru-cache")
    document = json.loads(runner.invoke(cli.app, ["next", "--set", LOOP, "--json"]).stdout)
    assert document == {
        "pick": "new",
        "slug": "two-sum",
        "title": "Two Sum",
        "kind": "function",
        "difficulty": "easy",
        "group": "arrays-hashing",
        "reason": f"next in {LOOP}, 1 of 2",
        "language": "python",
        "start": "cstudy start two-sum --lang python",
        "set": {"name": LOOP, "passed": 0, "total": 2, "finished": False},
    }


def test_next_set_json_says_when_the_set_is_finished(environment):
    looped("two-sum")
    finish(environment, "two-sum")
    assert json.loads(runner.invoke(cli.app, ["next", "--set", LOOP, "--json"]).stdout) == {
        "pick": None,
        "message": f"{LOOP} is finished: 1 of 1 passed",
        "set": {"name": LOOP, "passed": 1, "total": 1, "finished": True},
    }


def test_next_json_without_a_set_has_no_set_key(environment):
    assert "set" not in json.loads(runner.invoke(cli.app, ["next", "--json"]).stdout)


def test_a_bad_file_stops_list_set_and_next_set(environment, file):
    file.write_text("sets: [unclosed\n")
    codes = [
        runner.invoke(cli.app, ["list", "--set", LOOP]).exit_code,
        runner.invoke(cli.app, ["next", "--set", LOOP]).exit_code,
    ]
    assert codes == [ExitCode.ENVIRONMENT_ERROR, ExitCode.ENVIRONMENT_ERROR]
