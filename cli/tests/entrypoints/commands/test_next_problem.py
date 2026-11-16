import json
from dataclasses import replace
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import next_problem
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import NOW, RecordingEditor, jdk_of, repository_root
from tests.helpers import FIRST_CATALOG, copy_catalog_problems

runner = CliRunner()


@pytest.fixture
def editor() -> RecordingEditor:
    return RecordingEditor()


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def environment(tmp_path, editor, monkeypatch, problems):
    environment = e2e_environment(repository_root(tmp_path, problems), editor=editor)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: environment)
    return environment


def invoke(*arguments: str):
    return runner.invoke(cli.app, ["next", *arguments])


def schedule_review(environment, slug: str, overdue_days: int, interval: int = 7) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(slug, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(
        replace(attempt, status=AttemptStatus.PASSED, ended_at=NOW, grade=Grade.OK)
    )
    due_on = NOW.date() - timedelta(days=overdue_days)
    state = ReviewState(interval_days=interval, reps=2)
    progress.save_schedule_entry(ScheduleEntry(slug, state, due_on, Grade.OK, NOW))


def test_a_new_problem_names_the_weakest_pattern(environment):
    assert invoke().output.splitlines() == [
        "new     two-sum  (easy · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "start   cstudy start two-sum --lang python",
    ]


def test_a_review_names_the_overdue_days_and_interval(environment):
    schedule_review(environment, "lru-cache", overdue_days=3)
    assert invoke().output.splitlines()[0] == (
        "review  lru-cache  (medium · linked-list)  overdue 3d, interval 7d"
    )


def test_a_review_due_today(environment):
    schedule_review(environment, "lru-cache", overdue_days=0, interval=3)
    assert invoke().output.splitlines()[0].endswith("due today, interval 3d")


def test_the_start_hint_uses_the_language_given(environment):
    assert invoke("--lang", "kotlin").output.splitlines()[1] == (
        "start   cstudy start two-sum --lang kotlin"
    )


def test_a_lang_outside_the_workspaces_languages_exits_3_with_the_lang_add_hint(
    environment, monkeypatch
):
    narrowed = replace(environment, workspace_languages=(Language.PYTHON, Language.GO))
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: narrowed)
    result = invoke("--lang", "rust")
    assert (result.exit_code, result.output) == (
        ExitCode.USAGE_ERROR,
        "error: rust is not one of this workspace's languages (python, go): cstudy lang add rust\n",
    )


def test_a_refused_lang_with_start_starts_nothing(environment, monkeypatch):
    narrowed = replace(environment, workspace_languages=(Language.PYTHON,))
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: narrowed)
    result = invoke("--lang", "rust", "--start")
    assert (result.exit_code, environment.progress.active_attempt()) == (ExitCode.USAGE_ERROR, None)


def test_the_start_hint_uses_the_first_workspace_language_when_the_default_is_not_one(
    environment, monkeypatch
):
    narrowed = replace(environment, workspace_languages=(Language.GO, Language.RUST))
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: narrowed)
    assert invoke().output.splitlines()[1] == "start   cstudy start two-sum --lang go"


def test_nothing_in_scope(environment):
    result = invoke("--track", "practical")
    assert (result.exit_code, result.output) == (0, "nothing due and no new problems in scope\n")


def test_new_and_review_together_are_a_usage_error(environment):
    assert invoke("--new", "--review").exit_code == ExitCode.USAGE_ERROR


def test_review_only_without_reviews_finds_nothing(environment):
    assert invoke("--review").output == "nothing due and no new problems in scope\n"


def test_start_begins_the_attempt(environment):
    invoke("--start")
    attempt = environment.progress.active_attempt()
    assert (attempt.slug, attempt.language) == ("two-sum", Language.PYTHON)


def test_start_prints_the_pick_and_the_started_files(environment):
    assert invoke("--start").output.splitlines() == [
        "new     two-sum  (easy · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "two-sum · easy · arrays-hashing · python",
        "stub       python/practice/two_sum.py",
        "statement  .statements/two-sum.md",
        "next       cstudy test --watch",
    ]


def test_start_opens_the_editor(environment, editor):
    invoke("--start")
    assert len(editor.opened) == 1


def test_start_respects_open_on_start(environment, editor, monkeypatch):
    closed = replace(environment, config=Config(open_on_start=False))
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: closed)
    invoke("--start")
    assert editor.opened == []


def test_start_with_nothing_to_pick_starts_nothing(environment):
    invoke("--start", "--track", "practical")
    assert environment.progress.active_attempt() is None


def test_an_unknown_pattern_is_a_usage_error(environment):
    assert invoke("--pattern", "no-such-pattern").exit_code == ExitCode.USAGE_ERROR


@pytest.fixture
def with_a_practical_problem(tmp_path, editor, monkeypatch, tmp_path_factory):
    """The first catalog problems and the banking system, a `practical` problem."""
    problems = copy_catalog_problems(
        tmp_path_factory.mktemp("catalog"), (*FIRST_CATALOG, "banking-system")
    )
    environment = e2e_environment(repository_root(tmp_path, problems), editor=editor)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: environment)
    return environment


def test_a_domain_searches_every_track(with_a_practical_problem):
    assert invoke("--domain", "fintech").output.splitlines() == [
        "new     banking-system  (hard · practical)  weakest track: practical (0.75)",
        "start   cstudy start banking-system --lang python",
    ]


def test_a_role_searches_every_track(with_a_practical_problem):
    assert invoke("--role", "backend").output.splitlines()[0].startswith("new     banking-system")


def test_a_scope_searches_every_track(with_a_practical_problem):
    assert invoke("--scope", "function").output.splitlines()[0].startswith("new     two-sum")


def test_a_track_given_narrows_a_label_filter(with_a_practical_problem):
    result = invoke("--domain", "fintech", "--track", "dsa")
    assert result.output == "nothing due and no new problems in scope\n"


def test_a_domain_no_problem_names_finds_nothing(with_a_practical_problem):
    assert invoke("--domain", "security").output == "nothing due and no new problems in scope\n"


@pytest.mark.parametrize("flag", ["--domain", "--role", "--scope"])
def test_a_label_outside_its_list_is_a_usage_error(environment, flag):
    assert invoke(flag, "no-such-value").exit_code == ExitCode.USAGE_ERROR


def test_command_is_registered():
    assert "next" in {command.name for command in cli.app.registered_commands}


UNPROFILED = {
    "languages": None,
    "job_roles": None,
    "domains": None,
    "hidden": {"problems": 0},
}
"""`profile` of a run the profile narrowed nothing in."""


def document(*arguments: str):
    return json.loads(invoke("--json", *arguments).stdout)


def test_json_describes_a_new_pick(environment):
    assert document() == {
        "pick": "new",
        "id": "problem/two-sum",
        "slug": "two-sum",
        "title": "Two Sum",
        "kind": "function",
        "checked_by": ["tests"],
        "difficulty": "easy",
        "group": "arrays-hashing",
        "reason": "weakest pattern: arrays-hashing (0.75)",
        "language": "python",
        "start": "cstudy start two-sum --lang python",
        "profile": UNPROFILED,
    }


def test_json_says_a_problem_with_a_rubric_is_checked_by_tests_then_rubric(environment, tmp_path):
    (tmp_path / "problems" / "two-sum" / "rubric.md").write_text("# Two Sum: Rubric\n")
    assert document()["checked_by"] == ["tests", "rubric"]


def test_json_says_a_rubric_problem_is_checked_by_its_rubric(
    tmp_path, editor, monkeypatch, tmp_path_factory
):
    problems = copy_catalog_problems(
        tmp_path_factory.mktemp("catalog"), (*FIRST_CATALOG, "url-shortener")
    )
    environment = e2e_environment(repository_root(tmp_path, problems), editor=editor)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: environment)
    found = document("--track", "system-design")
    assert (found["id"], found["slug"], found["kind"], found["checked_by"]) == (
        "problem/url-shortener",
        "url-shortener",
        "system-design",
        ["rubric"],
    )


def test_json_describes_a_review(environment):
    schedule_review(environment, "lru-cache", overdue_days=3)
    found = document()
    assert (found["pick"], found["reason"]) == ("review", "overdue 3d, interval 7d")


def test_json_starts_in_the_language_given(environment):
    found = document("--lang", "kotlin")
    assert (found["language"], found["start"]) == (
        "kotlin",
        "cstudy start two-sum --lang kotlin",
    )


def test_json_with_nothing_to_pick_says_so(environment):
    assert document("--track", "practical") == {
        "pick": None,
        "message": "nothing due and no new problems in scope",
        "profile": UNPROFILED,
    }


def test_json_and_start_together_are_a_usage_error(environment):
    result = invoke("--json", "--start")
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: --json excludes --start\n",
    )


def test_json_and_start_together_start_nothing(environment):
    invoke("--json", "--start")
    assert environment.progress.active_attempt() is None


JDK_27_REASON = "JDK 27 (JAVA_HOME) cannot run java problems; cstudy supports JDK 21 to 26"


def on_jdk(environment, monkeypatch, jdk) -> None:
    selecting = replace(environment, jdk=jdk)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: selecting)


def test_a_jdk_that_cannot_run_java_leaves_nothing_to_pick_in_java(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    result = invoke("--lang", "java")
    assert (result.exit_code, result.output) == (
        ExitCode.SUCCESS,
        f"nothing to pick: {JDK_27_REASON}\n",
    )


def test_the_json_message_says_so_too(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    assert document("--lang", "java") == {
        "pick": None,
        "message": f"nothing to pick: {JDK_27_REASON}",
        "profile": UNPROFILED,
    }


def test_the_same_jdk_leaves_python_alone(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    assert invoke().output.splitlines()[0].startswith("new")


def test_start_never_starts_a_problem_the_jdk_cannot_run(environment, monkeypatch):
    on_jdk(environment, monkeypatch, jdk_of(27))
    result = invoke("--lang", "java", "--start")
    assert result.exit_code == ExitCode.SUCCESS
    assert environment.progress.active_attempt() is None


def open_attempt(environment, slug: str, hours_ago: int = 0, language=Language.PYTHON):
    started = NOW - timedelta(hours=hours_ago)
    return environment.progress.add_attempt(NewAttempt(slug, language, AttemptMode.NEW, started))


def test_an_attempt_in_progress_is_resumed_before_a_new_problem(environment):
    open_attempt(environment, "lru-cache")
    assert invoke().output.splitlines() == [
        "resume  lru-cache  (medium · linked-list)  attempt 1 in python, last used 2026-10-24",
        "start   cstudy start lru-cache --lang python",
    ]


def test_an_attempt_in_progress_is_resumed_before_a_due_review(environment):
    schedule_review(environment, "lru-cache", overdue_days=3)
    open_attempt(environment, "two-sum")
    assert invoke().output.splitlines()[0].startswith("resume  two-sum")


def test_the_attempt_used_most_recently_is_the_one_resumed(environment):
    open_attempt(environment, "two-sum", hours_ago=5)
    open_attempt(environment, "lru-cache", hours_ago=1)
    assert invoke().output.splitlines()[0].startswith("resume  lru-cache")


def test_the_other_attempts_in_progress_are_named_on_a_line_of_their_own(environment):
    open_attempt(environment, "two-sum", hours_ago=5)
    open_attempt(environment, "lru-cache", hours_ago=1)
    assert invoke().output.splitlines()[2] == "also    two-sum (python)"


def test_one_attempt_in_progress_names_no_others(environment):
    open_attempt(environment, "two-sum")
    assert len(invoke().output.splitlines()) == 2


def test_the_start_line_of_a_resume_names_the_language_of_the_attempt(environment):
    open_attempt(environment, "two-sum", language=Language.KOTLIN)
    assert invoke().output.splitlines()[1] == "start   cstudy start two-sum --lang kotlin"


def test_new_forces_a_new_problem_with_an_attempt_in_progress(environment):
    open_attempt(environment, "two-sum")
    assert invoke("--new").output.splitlines()[0].startswith("new     lru-cache")


def test_review_forces_a_review_with_an_attempt_in_progress(environment):
    schedule_review(environment, "lru-cache", overdue_days=3)
    open_attempt(environment, "two-sum")
    assert invoke("--review").output.splitlines()[0].startswith("review  lru-cache")


def test_start_resumes_the_attempt_instead_of_beginning_another(environment):
    first = open_attempt(environment, "two-sum")
    invoke("--start")
    assert [attempt.id for attempt in environment.progress.attempts_in_progress()] == [first.id]


def test_json_describes_a_resume_with_its_attempt_and_the_others(environment):
    open_attempt(environment, "two-sum", hours_ago=5)
    newest = open_attempt(environment, "lru-cache", hours_ago=1)
    assert document() == {
        "pick": "resume",
        "id": "problem/lru-cache",
        "slug": "lru-cache",
        "title": "LRU Cache",
        "kind": "design",
        "checked_by": ["tests"],
        "difficulty": "medium",
        "group": "linked-list",
        "reason": "attempt 2 in python, last used 2026-10-24",
        "language": "python",
        "start": "cstudy start lru-cache --lang python",
        "attempt_id": newest.id,
        "also_open": [
            {"attempt_id": 1, "id": "problem/two-sum", "slug": "two-sum", "language": "python"}
        ],
        "profile": UNPROFILED,
    }


def test_json_of_a_new_pick_gains_no_field_with_an_attempt_forced_aside(environment):
    open_attempt(environment, "two-sum")
    assert set(document("--new")) == {
        "profile",
        "pick",
        "id",
        "slug",
        "title",
        "checked_by",
        "kind",
        "difficulty",
        "group",
        "reason",
        "language",
        "start",
    }


# The learner profile (docs/specs/cli.md#the-learner-profile)

BACKEND_LINE = (
    "filtered by your profile: picked from 1 of 3 problems · domains backend · "
    "--widen all picks from all 3"
)


def use_profile(monkeypatch, environment, **changes) -> None:
    profiled = replace(environment, **changes)
    monkeypatch.setattr(next_problem, "load_environment", lambda *_: profiled)


def label_lru_cache_backend(environment) -> None:
    meta = environment.root / "problems/lru-cache/meta.yaml"
    meta.write_text(meta.read_text().replace("domains: [algorithms]", "domains: [backend]"))


@pytest.fixture
def backend_profile(environment, monkeypatch):
    label_lru_cache_backend(environment)
    use_profile(
        monkeypatch, environment, config=Config(profile=ProfileSettings(domains=("backend",)))
    )


def test_the_profile_narrows_the_pick_and_the_report_ends_with_its_line(backend_profile):
    assert invoke().output.splitlines() == [
        "new     lru-cache  (medium · linked-list)  weakest pattern: linked-list (0.75)",
        "start   cstudy start lru-cache --lang python",
        BACKEND_LINE,
    ]


def test_the_profile_line_is_dim_on_a_terminal_and_goes_to_standard_output(backend_profile):
    result = runner.invoke(cli.app, ["next"], env={"FORCE_COLOR": "1"})
    assert result.stdout.splitlines()[-1] == f"\x1b[2m{BACKEND_LINE}\x1b[0m"
    assert "filtered by" not in result.stderr


def test_widen_all_picks_from_every_problem_and_prints_no_line(backend_profile):
    assert invoke("--widen", "all").output.splitlines() == [
        "new     two-sum  (easy · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "start   cstudy start two-sum --lang python",
    ]


def test_widen_domain_drops_the_domains_of_the_profile(backend_profile):
    assert invoke("--widen", "domain").output == invoke("--widen", "all").output


def test_widen_role_keeps_the_domains_of_the_profile(backend_profile):
    assert BACKEND_LINE in invoke("--widen", "role").output


def test_a_domain_given_replaces_the_profiles_domains(backend_profile):
    result = invoke("--domain", "algorithms", "--track", "dsa")
    assert result.output.splitlines()[0].startswith("new     two-sum")
    assert "filtered by" not in result.output


@pytest.mark.parametrize("value", ["lang", "everything"])
def test_widen_takes_only_role_domain_and_all(environment, value):
    result = invoke("--widen", value)
    assert result.exit_code == ExitCode.USAGE_ERROR
    assert f'unknown widening "{value}"; use role, domain or all' in result.stderr


def test_the_profile_that_left_nothing_says_so_and_prints_no_line(environment, monkeypatch):
    config = Config(profile=ProfileSettings(job_roles=("backend",), domains=("security",)))
    use_profile(monkeypatch, environment, config=config)
    assert invoke().output == (
        "nothing to pick in your profile (roles backend and general, domains security); "
        "widen with cstudy next --widen all\n"
    )


def test_a_scope_that_holds_nothing_without_the_profile_keeps_the_usual_message_and_the_line(
    backend_profile,
):
    assert invoke("--track", "practical").output.splitlines() == [
        "nothing due and no new problems in scope",
    ]


def test_json_holds_the_profile_and_what_it_hid(backend_profile):
    assert document()["profile"] == {
        "languages": None,
        "job_roles": None,
        "domains": ["backend"],
        "hidden": {"problems": 2},
    }


def test_json_prints_no_line_and_holds_zero_hidden_without_a_narrowing_profile(environment):
    result = invoke("--json")
    assert "filtered by" not in result.stdout
    assert json.loads(result.stdout)["profile"] == UNPROFILED


def test_json_with_nothing_to_pick_in_the_profile_says_so(environment, monkeypatch):
    use_profile(
        monkeypatch, environment, config=Config(profile=ProfileSettings(domains=("security",)))
    )
    found = document()
    assert found["pick"] is None
    assert found["message"] == (
        "nothing to pick in your profile (domains security); widen with cstudy next --widen all"
    )
    assert found["profile"]["hidden"] == {"problems": 3}


def test_the_workspace_languages_narrow_and_start_the_pick(environment, monkeypatch):
    meta = environment.root / "problems/two-sum/meta.yaml"
    meta.write_text(
        meta.read_text().replace("estimate_minutes:", "languages: [kotlin, go]\nestimate_minutes:")
    )
    use_profile(monkeypatch, environment, workspace_languages=(Language.PYTHON, Language.KOTLIN))
    assert invoke().output.splitlines() == [
        "new     two-sum  (easy · arrays-hashing)  weakest pattern: arrays-hashing (0.75)",
        "start   cstudy start two-sum --lang kotlin",
    ]


def test_the_profile_line_ends_a_start_report_too(backend_profile):
    assert invoke("--start").output.splitlines()[-1] == BACKEND_LINE
