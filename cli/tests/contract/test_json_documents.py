"""The `--json` documents against their schemas in `schemas/cli/`
(docs/specs/compatibility.md#json-documents).

Each document is the real output of its command over a test workspace, validated against
`schemas/cli/<name>.schema.json`. A schema that names no field the command emits, or a command
that emits a field the schema does not name, fails here.

To cover another document:

- add its command's output to a `*_documents` fixture or a test of its own, and pass it to
  `assert_valid("<name>", document)`;
- add one `test_<name>_rejects_an_undocumented_field` over `assert_rejects_extra_field`, naming
  the path to an object of the document;
- `test_every_schema_*` already holds the new file to draft 2020-12 and to closed objects.
"""

import json
import shutil
from collections.abc import Callable, Iterator
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.adapters.problem_overlay import OverlayProblemRepository
from coding_study.adapters.sqlite.progress_store import SqliteProgressStore
from coding_study.adapters.sqlite.schema import latest_schema_version
from coding_study.application.doctor import CheckResult, CheckStatus, DoctorReport
from coding_study.application.environment import Environment
from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.application.ports import CaseListener, RunnerLaunch
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import (
    Attempt,
    AttemptMode,
    AttemptStatus,
    Grade,
    NewAttempt,
    Rating,
    RunRecord,
)
from coding_study.domain.bench_records import BenchRunRecord
from coding_study.domain.bench_runs import BenchReport, BenchRequest
from coding_study.domain.bench_verdict import Confidence, Verdict
from coding_study.domain.config import Config, ProfileSettings
from coding_study.domain.content_ids import ContentType
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.progress_export import ProgressSnapshot, export_text
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    InvalidOutput,
    NotRun,
    Raised,
    Returned,
    RunCase,
    RunJob,
    RunReport,
    RunRequest,
    Stalled,
    TimedOut,
    UserError,
)
from coding_study.domain.sandbox import CommandOutcome, StackStartError, StartupFailure
from coding_study.domain.scheduling import ReviewState, ScheduleEntry
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Comparison,
    Passed,
    Skipped,
    SuiteTest,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import (
    docs,
    doctor,
    export,
    history,
    learn,
    list_problems,
    next_problem,
    problem_sets,
    start,
    stats,
    status,
)
from coding_study.entrypoints.commands import submit as submit_command
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.application.http_grading_fakes import FakeApp, FakeMockControl
from tests.bench_fakes import ScriptedBenchProcess, optimal_user
from tests.concurrency_fakes import duplicating, queue, stalling
from tests.content_id_checks import content_ids_in
from tests.doc_builders import write_docs
from tests.e2e import e2e_environment
from tests.fakes import (
    NOW,
    FakeJdk,
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    declare_jdk,
    jdk_of,
    make_environment,
    repository_root,
    two_sum,
)
from tests.guide_builders import write_guide, write_hashing, write_path
from tests.helpers import (
    CONCURRENCY_PROBLEMS,
    FIRST_CATALOG,
    FIXTURE_RUBRIC_PROBLEMS,
    PROJECT_PROBLEMS,
    REPOSITORY_ROOT,
    copy_catalog_problems,
    mark_workspace,
)
from tests.progress_fixtures import database_at_schema, read_rows
from tests.project_fakes import (
    LEVEL_1_TEST,
    PROJECT_SLUG,
    TALLY_SLUG,
    ScriptedProjectProcess,
    project_environment,
    stress_project_environment,
    tally_answers,
)
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    FOLDER,
    make_content,
    meta_document,
    write_cases,
    write_mock,
    write_problem,
)
from tests.service_problems import (
    SLUG as SERVICE_SLUG,
)
from tests.stats_fixture import fill_progress

SCHEMA_DIRECTORY = REPOSITORY_ROOT / "schemas" / "cli"
SCHEMA_FILES = sorted(SCHEMA_DIRECTORY.glob("*.schema.json"))
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
LATEST = latest_schema_version()
SCHEMAS = range(1, LATEST + 1)
EXPORT_TABLES = (
    "attempts",
    "test_runs",
    "schedule",
    "bench_runs",
    "submissions",
    "level_unlocks",
    "guide_reads",
)
UNDOCUMENTED = "undocumented_field"

runner = CliRunner()


# The harness


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIRECTORY / f"{name}.schema.json").read_text(encoding="utf-8"))


def schema_errors(name: str, document: Any) -> list[str]:
    """What is wrong with `document` as `schemas/cli/<name>.schema.json`, one line each."""
    validator = Draft202012Validator(load_schema(name))
    return [
        f"{'/'.join(str(step) for step in error.absolute_path) or '<document>'}: {error.message}"
        for error in validator.iter_errors(document)
    ]


def assert_valid(name: str, document: Any) -> None:
    assert schema_errors(name, document) == []


def with_extra_field(document: Any, path: tuple[str | int, ...]) -> Any:
    """A copy of `document` whose object at `path` has a field no schema names."""
    changed = deepcopy(document)
    target = changed
    for step in path:
        target = target[step]
    assert isinstance(target, dict)
    target[UNDOCUMENTED] = True
    return changed


def assert_rejects_extra_field(name: str, document: Any, path: tuple[str | int, ...]) -> None:
    """Fails unless the schema accepts `document` and refuses it once the object at `path` has a
    field it does not name."""
    assert_valid(name, document)
    errors = schema_errors(name, with_extra_field(document, path))
    assert len(errors) == 1
    assert UNDOCUMENTED in errors[0]


def schema_objects(schema: Any, where: str = "#") -> Iterator[tuple[str, dict[str, Any]]]:
    """Every subschema that describes an object, with its location."""
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            yield where, schema
        for key, value in schema.items():
            if key != "properties":
                yield from schema_objects(value, f"{where}/{key}")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for name, value in properties.items():
                yield from schema_objects(value, f"{where}/properties/{name}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            yield from schema_objects(value, f"{where}/{index}")


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_every_schema_is_draft_2020_12(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"] == SCHEMA_DIALECT
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("path", SCHEMA_FILES, ids=lambda path: path.name)
def test_every_schema_object_is_closed(path):
    schema = json.loads(path.read_text(encoding="utf-8"))
    open_objects = [
        where
        for where, subschema in schema_objects(schema)
        if subschema.get("additionalProperties") is not False
    ]
    assert open_objects == []


@pytest.mark.parametrize(
    "path",
    [path for path in SCHEMA_FILES if path.name != "export.schema.json"],
    ids=lambda path: path.name,
)
def test_every_schema_object_that_names_content_requires_an_id(path):
    """The export is exempt: its rows are database rows, and the table names the type."""
    schema = json.loads(path.read_text(encoding="utf-8"))
    without_id = [
        where
        for where, subschema in schema_objects(schema)
        if "slug" in subschema.get("properties", {})
        and ("id" not in subschema["properties"] or "id" not in subschema.get("required", []))
    ]
    assert without_id == []


def test_the_schema_directory_is_not_empty():
    assert SCHEMA_FILES


# cstudy stats --json


@pytest.fixture
def problems(tmp_path_factory):
    return copy_catalog_problems(tmp_path_factory.mktemp("catalog"), FIRST_CATALOG)


@pytest.fixture
def empty_environment(tmp_path, problems, monkeypatch):
    environment = make_environment(repository_root(tmp_path, problems, FIXTURE_RUBRIC_PROBLEMS))
    monkeypatch.setattr(stats, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def filled_environment(empty_environment):
    fill_progress(empty_environment)
    return empty_environment


def stats_document(*arguments: str) -> Any:
    result = runner.invoke(cli.app, ["stats", "--json", *arguments])
    assert result.exit_code == ExitCode.SUCCESS
    return json.loads(result.stdout)


def test_stats_over_an_empty_database(empty_environment):
    document = stats_document()
    assert_valid("stats", document)
    assert document["attempts"] == {"finished": 0, "last_7_days": 0, "streak_days": 0}


def test_stats_over_an_empty_database_has_no_pass_rate_or_solve_time(empty_environment):
    groups = stats_document()["groups"]
    assert groups
    assert {(group["pass_rate"], group["median_solve_s"]) for group in groups} == {(None, None)}


def test_stats_over_a_populated_database(filled_environment):
    document = stats_document()
    assert_valid("stats", document)
    assert document["attempts"]["finished"] == 4


def test_stats_over_a_populated_database_has_a_pass_rate_and_a_solve_time(filled_environment):
    groups = stats_document()["groups"]
    assert any(
        isinstance(group["pass_rate"], float) and isinstance(group["median_solve_s"], int)
        for group in groups
    )


@pytest.mark.parametrize("grouping", ["pattern", "track", "lang", "difficulty"])
def test_stats_in_every_grouping(filled_environment, grouping):
    document = stats_document("--by", grouping)
    assert_valid("stats", document)
    assert document["by"] == grouping


def test_stats_since_a_date(filled_environment):
    document = stats_document("--since", "2026-10-01")
    assert_valid("stats", document)
    assert document["since"] == "2026-10-01"


def test_stats_rejects_an_undocumented_field(filled_environment):
    document = stats_document()
    for path in ((), ("groups", 0), ("attempts",), ("reviews",), ("bench",)):
        assert_rejects_extra_field("stats", document, path)


def test_stats_rejects_a_missing_field(filled_environment):
    document = stats_document()
    del document["groups"][0]["weakness"]
    assert schema_errors("stats", document)


# cstudy doctor --json


def doctor_result(*arguments: str):
    return runner.invoke(cli.app, [*arguments, "doctor", "--json"])


def stub_checks(monkeypatch: pytest.MonkeyPatch, *results: CheckResult) -> None:
    monkeypatch.setattr(doctor, "run_doctor", lambda _environment, _notify: DoctorReport(results))


PASSING = (
    CheckResult("python", CheckStatus.OK, "3.13.2"),
    CheckResult("projects", CheckStatus.OK),
    CheckResult("gradle", CheckStatus.WARN, "not found", "brew install gradle"),
)


def test_doctor_over_a_workspace_with_failing_rows(tmp_path):
    workspace = mark_workspace(tmp_path / "workspace")
    result = doctor_result("--workspace", str(workspace))
    document = json.loads(result.stdout)
    assert_valid("doctor", document)
    assert document["workspace"] == str(workspace)
    assert any(check["status"] == "fail" for check in document["checks"])
    assert result.exit_code == ExitCode.ENVIRONMENT_ERROR


def test_doctor_without_a_workspace(tmp_path):
    document = json.loads(doctor_result("--workspace", str(tmp_path / "nowhere")).stdout)
    assert_valid("doctor", document)
    assert document["workspace"] is None


def test_doctor_with_passing_rows(monkeypatch, tmp_path):
    stub_checks(monkeypatch, *PASSING)
    result = doctor_result("--workspace", str(mark_workspace(tmp_path / "workspace")))
    document = json.loads(result.stdout)
    assert_valid("doctor", document)
    assert document["passed"] is True
    assert result.exit_code == ExitCode.SUCCESS


def test_doctor_with_a_failing_row_and_a_fix(monkeypatch):
    stub_checks(
        monkeypatch,
        *PASSING,
        CheckResult("python/.venv", CheckStatus.FAIL, "missing", "cstudy doctor --fix"),
    )
    document = json.loads(doctor_result().stdout)
    assert_valid("doctor", document)
    assert document["passed"] is False


def test_doctor_rejects_an_undocumented_field(monkeypatch):
    stub_checks(monkeypatch, *PASSING)
    document = json.loads(doctor_result().stdout)
    for path in ((), ("checks", 0)):
        assert_rejects_extra_field("doctor", document, path)


def test_doctor_rejects_a_status_it_does_not_name(monkeypatch):
    stub_checks(monkeypatch, *PASSING)
    document = json.loads(doctor_result().stdout)
    document["checks"][0]["status"] = "WARN"
    assert schema_errors("doctor", document)


# cstudy export (the file)


def export_document(environment, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """The file `cstudy export` writes for the environment's progress.db."""
    monkeypatch.setattr(export, "load_environment", lambda *_: environment)
    path = tmp_path / "progress-export.json"
    assert runner.invoke(cli.app, ["export", "--out", str(path)]).exit_code == ExitCode.SUCCESS
    return json.loads(path.read_text(encoding="utf-8"))


def fixture_environment(root: Path, number: int):
    """An environment whose progress.db is the fixture at schema `number`, migrated on first use."""
    database = database_at_schema(root / f"schema-{number}" / "progress.db", number)
    return make_environment(root, progress=SqliteProgressStore(database))


def test_an_export_over_an_empty_database(empty_environment, tmp_path, monkeypatch):
    document = export_document(empty_environment, tmp_path, monkeypatch)
    assert_valid("export", document)
    assert document["tables"] == {table: [] for table in EXPORT_TABLES}


def test_an_export_over_a_populated_database(filled_environment, tmp_path, monkeypatch):
    assert_valid("export", export_document(filled_environment, tmp_path, monkeypatch))


def test_an_export_with_rows_in_every_table(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    assert_valid("export", document)
    assert {table: bool(rows) for table, rows in document["tables"].items()} == dict.fromkeys(
        EXPORT_TABLES, True
    )


@pytest.mark.parametrize("number", SCHEMAS)
def test_an_export_of_the_fixture_at_each_schema_after_it_migrates(
    content_root, tmp_path, monkeypatch, number
):
    environment = fixture_environment(content_root, number)
    document = export_document(environment, tmp_path, monkeypatch)
    assert_valid("export", document)
    assert document["schema_version"] == LATEST


@pytest.mark.parametrize("number", SCHEMAS)
def test_an_export_built_at_each_schema(content_root, number):
    database = database_at_schema(content_root / "built" / "progress.db", number)
    rows = read_rows(database)
    text = export_text(
        ProgressSnapshot(number, {table: tuple(held) for table, held in rows.items()}),
        NOW + timedelta(hours=1),
    )
    document = json.loads(text)
    assert_valid("export", document)
    assert document["schema_version"] == number


def test_export_rejects_an_undocumented_field(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    paths: tuple[tuple[str | int, ...], ...] = ((), ("tables",))
    rows = tuple(("tables", table, 0) for table in EXPORT_TABLES)
    for path in (*paths, *rows):
        assert_rejects_extra_field("export", document, path)


def test_export_rejects_a_table_it_does_not_name(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    document["tables"]["undocumented_table"] = []
    assert schema_errors("export", document)


def test_export_rejects_another_version(content_root, tmp_path, monkeypatch):
    environment = fixture_environment(content_root, LATEST)
    document = export_document(environment, tmp_path, monkeypatch)
    document["version"] = 2
    assert schema_errors("export", document)


# The content and progress documents

FIXTURES = REPOSITORY_ROOT / "cli" / "tests" / "fixtures"
PRACTICE = FIXTURES / "practice" / "problems"
PHASE4 = FIXTURES / "phase4" / "problems"
TOOLCHAINS = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
COMMANDS = (
    docs,
    history,
    learn,
    list_problems,
    next_problem,
    problem_sets,
    start,
    status,
    submit_command,
    test_command,
)
ENTRY_KINDS = {
    "function",
    "design",
    "progressive",
    "concurrent",
    "project",
    "system-design",
    "code-review",
}
LOOP = "backend-loop"
SETS = f"""\
sets:
  {LOOP}:
    description: Before the 12th
    problems:
      - two-sum
      - url-shortener
      - {{slug: level-store, level: 2}}
      - gone
  warm-up:
    problems: []
"""
STORE = "level-store"
RUBRIC = "url-shortener"


def install(monkeypatch: pytest.MonkeyPatch, environment: Environment) -> Environment:
    """Makes `environment` the one every command of these documents loads."""
    for module in COMMANDS:
        for name in ("load_environment", "load_catalog_environment"):
            if hasattr(module, name):
                monkeypatch.setattr(module, name, lambda *_: environment)
    return environment


def command_document(*arguments: str) -> Any:
    result = runner.invoke(cli.app, [*arguments, "--json"])
    assert result.exit_code == ExitCode.SUCCESS, result.output
    return json.loads(result.stdout)


def assert_ids(document: Any, *types: ContentType) -> None:
    """Every object of `document` that names content carries its canonical ID, of these types."""
    assert {content_type for content_type, _ in content_ids_in(document)} == set(types)


def add_attempt(
    environment: Environment,
    slug: str,
    language: Language,
    started_at: datetime = NOW,
    **fields: Any,
) -> int:
    """An attempt of `slug`, with `fields` changed."""
    new = NewAttempt(slug, language, AttemptMode.NEW, started_at)
    started = environment.progress.add_attempt(new)
    environment.progress.update_attempt(replace(started, **fields))
    return started.id


def add_run(environment: Environment, attempt_id: int, passed: int, **fields: Any) -> None:
    tally = Tally(total=4, passed=passed, failed=4 - passed)
    environment.progress.add_test_run(RunRecord(attempt_id, NOW, "abc", tally, 10, **fields))


def find_attempt(environment: Environment, slug: str) -> Attempt:
    attempts = environment.progress.attempts(slug)
    assert attempts
    return attempts[-1]


# cstudy list --json


@pytest.fixture
def every_kind(tmp_path, tmp_path_factory, monkeypatch) -> Environment:
    """A problem of each kind, rubric problems, a service project and a problem of your own,
    with JDK 26 selected."""
    root = repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS)
    for problems in (PHASE4, CONCURRENCY_PROBLEMS, PROJECT_PROBLEMS):
        shutil.copytree(problems, root / "problems", dirs_exist_ok=True)
    write_problem(root)
    declare_jdk(root, "two-sum", "{min: 24}")
    yours = tmp_path_factory.mktemp("yours")
    (yours / "problems").mkdir()
    shutil.move(root / "problems" / "parking-lot", yours / "problems" / "parking-lot")
    problems = OverlayProblemRepository(FsProblemRepository(root), yours)
    return install(monkeypatch, make_environment(root, problems=problems, jdk=jdk_of(26)))


def test_a_list_with_every_kind(every_kind):
    document = command_document("list")
    assert_valid("list", document)
    entries = document["entries"]
    assert {entry["kind"] for entry in entries} == ENTRY_KINDS
    assert_ids(document, ContentType.PROBLEM)


def test_a_list_names_rubric_problems_and_your_own(every_kind):
    entries = {entry["slug"]: entry for entry in command_document("list")["entries"]}
    assert entries[RUBRIC]["checked_by"] == ["rubric"]
    assert entries[RUBRIC]["requires"] is None
    assert entries["parking-lot"]["source"] == "workspace"
    assert entries["two-sum"]["checked_by"] == ["tests"]


def test_a_list_holds_a_service_project_s_needs_and_a_jdk_range(every_kind):
    entries = {entry["slug"]: entry for entry in command_document("list")["entries"]}
    assert entries[SERVICE_SLUG]["requires"]["docker"] is True
    assert entries["two-sum"]["jdk"] == {"min": 24, "max": 26}


def test_a_list_of_progress(every_kind):
    add_attempt(every_kind, "two-sum", Language.PYTHON)
    add_attempt(every_kind, "lru-cache", Language.PYTHON, status=AttemptStatus.PASSED, ended_at=NOW)
    state = ReviewState(ease=2.5, interval_days=3, reps=1, lapses=0)
    due = ScheduleEntry("lru-cache", state, NOW.date(), Grade.OK, NOW)
    every_kind.progress.save_schedule_entry(due)
    document = command_document("list")
    assert_valid("list", document)
    entries = {entry["slug"]: entry for entry in document["entries"]}
    assert entries["two-sum"]["status"] == "in_progress"
    assert entries["two-sum"]["in_progress"] == [
        {"attempt_id": 1, "language": "python", "mode": "new"}
    ]
    assert entries["lru-cache"]["due_on"] == NOW.date().isoformat()


def test_a_list_without_a_selected_jdk(every_kind, monkeypatch):
    install(monkeypatch, replace(every_kind, jdk=FakeJdk(None)))
    document = command_document("list")
    assert_valid("list", document)
    assert document["selected_jdk"] is None


def test_a_list_of_a_set(every_kind):
    (every_kind.root / "sets.yaml").write_text(SETS)
    document = command_document("list", "--set", LOOP)
    assert_valid("list", document)
    assert document["set"] == {"name": LOOP, "missing": ["gone"]}


def test_list_rejects_an_undocumented_field(every_kind):
    add_attempt(every_kind, "two-sum", Language.PYTHON)
    document = command_document("list")
    entries = document["entries"]
    for path in ((), ("selected_jdk",), ("entries", 0)):
        assert_rejects_extra_field("list", document, path)
    for field in ("requires", "levels", "jdk"):
        index = next(index for index, entry in enumerate(entries) if entry[field])
        assert_rejects_extra_field("list", document, ("entries", index, field))
    index = next(index for index, entry in enumerate(entries) if entry["in_progress"])
    assert_rejects_extra_field("list", document, ("entries", index, "in_progress", 0))


def test_a_list_under_a_narrowed_profile(every_kind, monkeypatch):
    narrowed = replace(
        every_kind,
        config=Config(profile=ProfileSettings(job_roles=("backend",), domains=("security",))),
        workspace_languages=(Language.PYTHON, Language.GO),
    )
    install(monkeypatch, narrowed)
    document = command_document("list")
    assert_valid("list", document)
    profile = document["profile"]
    assert (profile["languages"], profile["job_roles"], profile["domains"]) == (
        ["python", "go"],
        ["backend"],
        ["security"],
    )
    assert profile["hidden"]["problems"] > 0
    for path in (("profile",), ("profile", "hidden")):
        assert_rejects_extra_field("list", document, path)


def test_list_of_a_set_rejects_an_undocumented_field(every_kind):
    (every_kind.root / "sets.yaml").write_text(SETS)
    assert_rejects_extra_field("list", command_document("list", "--set", LOOP), ("set",))


def test_list_rejects_the_id_of_another_type(every_kind):
    document = command_document("list")
    document["entries"][0]["id"] = "guide/two-sum"
    assert schema_errors("list", document)


def test_list_rejects_a_kind_it_does_not_name(every_kind):
    document = command_document("list")
    document["entries"][0]["kind"] = "puzzle"
    assert schema_errors("list", document)


# cstudy next --json


@pytest.fixture
def practised(tmp_path, monkeypatch) -> Environment:
    """The practice problems, the progressive problems and the rubric problems."""
    root = repository_root(tmp_path, PRACTICE, FIXTURE_RUBRIC_PROBLEMS)
    shutil.copytree(PHASE4, root / "problems", dirs_exist_ok=True)
    (root / "sets.yaml").write_text(SETS)
    return install(monkeypatch, make_environment(root, toolchains=TOOLCHAINS))


def test_next_with_a_new_problem_to_pick(practised):
    document = command_document("next")
    assert_valid("next", document)
    assert document["pick"] == "new"
    assert_ids(document, ContentType.PROBLEM)


def test_next_with_a_review_to_pick(practised):
    add_attempt(practised, "two-sum", Language.PYTHON, status=AttemptStatus.PASSED, ended_at=NOW)
    state = ReviewState(ease=2.5, interval_days=3, reps=1, lapses=0)
    practised.progress.save_schedule_entry(
        ScheduleEntry("two-sum", state, date(2026, 10, 20), Grade.OK, NOW)
    )
    document = command_document("next", "--review")
    assert_valid("next", document)
    assert document["pick"] == "review"


def test_next_with_an_attempt_to_resume(practised):
    add_attempt(practised, "two-sum", Language.PYTHON)
    add_attempt(practised, STORE, Language.PYTHON)
    document = command_document("next", "--track", "dsa", "--track", "practical")
    assert_valid("next", document)
    assert document["pick"] == "resume"
    assert [other["slug"] for other in document["also_open"]] == ["two-sum"]
    assert_ids(document, ContentType.PROBLEM)


def test_next_with_a_rubric_problem_to_pick(practised):
    document = command_document("next", "--scope", "system")
    assert_valid("next", document)
    assert (document["kind"], document["checked_by"], document["language"]) == (
        "system-design",
        ["rubric"],
        None,
    )


def test_next_in_a_set(practised):
    document = command_document("next", "--set", LOOP)
    assert_valid("next", document)
    assert document["set"] == {"name": LOOP, "passed": 0, "total": 3, "finished": False}


def test_next_with_nothing_to_pick(practised):
    document = command_document("next", "--pattern", "tries")
    assert_valid("next", document)
    assert document["pick"] is None


def test_next_in_an_empty_set_has_nothing_to_pick(practised):
    document = command_document("next", "--set", "warm-up")
    assert_valid("next", document)
    assert (document["pick"], document["set"]["total"]) == (None, 0)


def test_next_rejects_an_undocumented_field(practised):
    pick = command_document("next", "--set", LOOP)
    for path in ((), ("set",)):
        assert_rejects_extra_field("next", pick, path)
    nothing = command_document("next", "--set", "warm-up")
    for path in ((), ("set",)):
        assert_rejects_extra_field("next", nothing, path)
    add_attempt(practised, "two-sum", Language.PYTHON)
    add_attempt(practised, STORE, Language.PYTHON)
    resume = command_document("next", "--track", "dsa", "--track", "practical")
    for path in ((), ("also_open", 0)):
        assert_rejects_extra_field("next", resume, path)


def test_next_rejects_a_pick_without_its_fields(practised):
    document = command_document("next")
    del document["start"]
    assert schema_errors("next", document)


# cstudy status --json


@pytest.fixture
def attempted(practised) -> Environment:
    """An autograded attempt with a test run, a progressive one with a time box and levels, and a
    rubric one."""
    start_attempt(practised, StartRequest("two-sum", Language.PYTHON))
    start_attempt(practised, StartRequest(STORE, Language.PYTHON, timer_s=600))
    start_item_attempt(practised, ItemStartRequest(RUBRIC))
    add_run(practised, find_attempt(practised, "two-sum").id, passed=3)
    add_run(practised, find_attempt(practised, STORE).id, passed=2, levels_passed=1)
    return practised


@pytest.fixture
def project(tmp_path, monkeypatch) -> Environment:
    """A project attempt that submitted twice."""
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    attempt_id = find_attempt(environment, PROJECT_SLUG).id
    for minutes, passed in ((0, 1), (5, 2)):
        tallies = (LevelTally(1, 1, passed, 2, passed),)
        environment.progress.add_submission(
            SubmissionRecord(
                attempt_id=attempt_id,
                submitted_at=NOW + timedelta(minutes=minutes),
                code_hash="abc",
                graded_up_to=1,
                every_level=True,
                levels=tallies,
                tally=Tally(total=3, passed=passed + 1, failed=2 - passed),
                duration_ms=300,
            )
        )
    return install(monkeypatch, environment)


def service_environment(tmp_path, monkeypatch, meta: dict[str, object]) -> Environment:
    root = repository_root(tmp_path, PRACTICE)
    write_problem(root, meta)
    write_mock(root)
    environment = make_environment(root, sandbox=FakeSandbox())
    install(monkeypatch, environment)
    result = runner.invoke(cli.app, ["start", SERVICE_SLUG, "--no-open", "--yes"])
    assert result.exit_code == ExitCode.SUCCESS, result.output
    return environment


MOCKS = [{"name": "room-vendor", "config": CONFIG}]


def test_status_of_an_autograded_attempt(attempted):
    document = command_document("status", "two-sum")
    assert_valid("status", document)
    assert (document["kind"], document["last_test_run"]["passed"]) == ("function", 3)
    assert_ids(document, ContentType.PROBLEM)


def test_status_of_an_attempt_with_hints_and_a_revealed_solution(attempted):
    attempt = find_attempt(attempted, "two-sum")
    attempted.progress.update_attempt(replace(attempt, hints_used=1, solution_revealed=True))
    document = command_document("status", "two-sum")
    assert_valid("status", document)
    assert document["solution_revealed"] is True


def test_status_of_a_progressive_attempt(attempted):
    document = command_document("status", STORE)
    assert_valid("status", document)
    assert document["levels"]["passed"] == 1
    assert document["timer"]["limit_s"] == 600


def test_status_of_a_rubric_attempt(attempted):
    document = command_document("status", RUBRIC)
    assert_valid("status", document)
    assert (document["checked_by"], document["language"]) == (["rubric"], None)
    assert (document["last_test_run"], document["levels"]) == (None, None)


def test_status_of_a_project_attempt(project):
    document = command_document("status")
    assert_valid("status", document)
    assert document["kind"] == "project"
    assert document["latest_submission"]["level_tallies"]
    assert document["best_per_level"]
    assert document["files"]["entries"]


def test_status_of_a_service_project_in_typescript(tmp_path, monkeypatch):
    service_environment(tmp_path, monkeypatch, meta_document(mocks=MOCKS))
    document = command_document("status")
    assert_valid("status", document)
    assert document["service"] == {"mocks": [{"name": "room-vendor", "scenarios": ["outage"]}]}
    assert document["no_code_intelligence"] is None


def test_status_rejects_an_undocumented_field(attempted):
    function = command_document("status", "two-sum")
    for path in ((), ("hints",), ("last_test_run",)):
        assert_rejects_extra_field("status", function, path)
    progressive = command_document("status", STORE)
    for path in (("levels",), ("timer",)):
        assert_rejects_extra_field("status", progressive, path)


def test_status_of_a_project_rejects_an_undocumented_field(project):
    submitted = command_document("status")
    for path in (
        ("latest_submission",),
        ("latest_submission", "level_tallies", 0),
        ("best_per_level", 0),
        ("files",),
        ("files", "entries", 0),
    ):
        assert_rejects_extra_field("status", submitted, path)


def test_status_of_a_service_project_rejects_an_undocumented_field(tmp_path, monkeypatch):
    service_environment(tmp_path, monkeypatch, meta_document(mocks=MOCKS))
    document = command_document("status")
    for path in (("service",), ("service", "mocks", 0)):
        assert_rejects_extra_field("status", document, path)


# cstudy history --json


def add_bench_run(environment: Environment, attempt_id: int) -> None:
    environment.progress.add_bench_run(
        BenchRunRecord(
            attempt_id=attempt_id,
            slug="two-sum",
            language=Language.PYTHON,
            ran_at=NOW,
            code_hash="abc",
            sizes=(100,),
            series=(),
            verdict=Verdict.OPTIMAL,
            confidence=Confidence.MEDIUM,
            reference_id="hash-map",
            ratio=1.3,
        )
    )


@pytest.fixture
def lived(practised) -> Environment:
    """A problem with an abandoned, a failed and a passed attempt, a bench run and a schedule; a
    progressive problem with an attempt that passed through level 1; a rubric problem with an
    attempt."""
    week_ago = NOW - timedelta(days=7)
    abandoned = add_attempt(
        practised,
        "two-sum",
        Language.PYTHON,
        status=AttemptStatus.ABANDONED,
        started_at=week_ago,
        ended_at=week_ago,
    )
    add_run(practised, abandoned, passed=0)
    failed = add_attempt(
        practised,
        "two-sum",
        Language.PYTHON,
        status=AttemptStatus.FAILED,
        started_at=week_ago,
        ended_at=week_ago + timedelta(minutes=41),
        grade=Grade.AGAIN,
        hints_used=2,
        solution_revealed=True,
        time_limit_s=600,
    )
    add_run(practised, failed, passed=3, time_limit="5x")
    passed = add_attempt(
        practised,
        "two-sum",
        Language.KOTLIN,
        status=AttemptStatus.PASSED,
        ended_at=NOW + timedelta(minutes=18),
        rating=Rating.OK,
        grade=Grade.OK,
    )
    add_run(practised, passed, passed=4)
    add_bench_run(practised, passed)
    state = ReviewState(ease=2.5, interval_days=7, reps=2, lapses=0)
    practised.progress.save_schedule_entry(
        ScheduleEntry("two-sum", state, date(2026, 11, 1), Grade.OK, NOW)
    )
    add_attempt(
        practised,
        STORE,
        Language.PYTHON,
        status=AttemptStatus.PASSED,
        ended_at=NOW + timedelta(minutes=30),
        grade=Grade.OK,
        level_unlocked=2,
        levels_passed=1,
        levels_total=2,
    )
    start_item_attempt(practised, ItemStartRequest(RUBRIC))
    return practised


def test_history_of_an_autograded_problem(lived):
    document = command_document("history", "two-sum")
    assert_valid("history", document)
    assert [attempt["status"] for attempt in document["attempts"]] == [
        "passed",
        "failed",
        "abandoned",
    ]
    assert document["schedule"]["due_on"] == "2026-11-01"
    assert document["levels"] is None
    assert_ids(document, ContentType.PROBLEM)


def test_history_of_a_progressive_problem(lived):
    document = command_document("history", STORE)
    assert_valid("history", document)
    assert document["levels"]["languages"] == [
        {"language": "python", "best": 1, "last_time": 1, "try_level": 2}
    ]


def test_history_of_a_rubric_problem(lived):
    document = command_document("history", RUBRIC)
    assert_valid("history", document)
    assert document["attempts"][0]["language"] is None


def test_history_of_a_problem_without_attempts(lived):
    document = command_document("history", "parking-lot")
    assert_valid("history", document)
    assert (document["attempts"], document["schedule"]) == ([], None)


def test_history_of_a_project(project):
    document = command_document("history", PROJECT_SLUG)
    assert_valid("history", document)
    submissions = document["attempts"][0]["submissions"]
    assert [found["passed"] for found in submissions] == [2, 3]
    assert submissions[0]["levels"]


def test_history_rejects_an_undocumented_field(lived):
    document = command_document("history", "two-sum")
    for path in (
        (),
        ("schedule",),
        ("attempts", 0),
        ("attempts", 1, "test_runs", 0),
        ("attempts", 0, "bench_runs", 0),
    ):
        assert_rejects_extra_field("history", document, path)
    progressive = command_document("history", STORE)
    for path in (("levels",), ("levels", "languages", 0)):
        assert_rejects_extra_field("history", progressive, path)


def test_history_of_a_project_rejects_an_undocumented_field(project):
    document = command_document("history", PROJECT_SLUG)
    for path in (("attempts", 0, "submissions", 0), ("attempts", 0, "submissions", 0, "levels", 0)):
        assert_rejects_extra_field("history", document, path)


# cstudy set list --json, cstudy set show --json


def test_the_sets_when_one_is_empty_and_one_is_filled(practised):
    document = command_document("set", "list")
    assert_valid("set-list", document)
    empty, filled = sorted(document["sets"], key=lambda found: len(found["slugs"]))
    assert (empty["slugs"], empty["levels"]) == ([], {})
    assert (filled["missing"], filled["levels"]) == (["gone"], {STORE: 2})


def test_no_sets(practised):
    (practised.root / "sets.yaml").unlink()
    document = command_document("set", "list")
    assert_valid("set-list", document)
    assert document["sets"] == []


def test_a_filled_set(practised):
    add_attempt(practised, "two-sum", Language.PYTHON, status=AttemptStatus.PASSED, ended_at=NOW)
    document = command_document("set", "show", LOOP)
    assert_valid("set-show", document)
    assert [row["slug"] for row in document["rows"]] == ["two-sum", RUBRIC, STORE, "gone"]
    assert [row["missing"] for row in document["rows"]] == [False, False, False, True]
    assert document["rows"][3]["entry"] is None
    assert_ids(document, ContentType.PROBLEM)


def test_an_empty_set(practised):
    document = command_document("set", "show", "warm-up")
    assert_valid("set-show", document)
    assert (document["rows"], document["total"]) == ([], 0)


def test_set_list_rejects_an_undocumented_field(practised):
    document = command_document("set", "list")
    for path in ((), ("sets", 0)):
        assert_rejects_extra_field("set-list", document, path)


def test_set_list_rejects_a_target_for_a_name_that_is_not_a_slug(practised):
    document = command_document("set", "list")
    document["sets"][0]["levels"]["Not A Slug"] = 2
    assert schema_errors("set-list", document)


def test_set_show_rejects_an_undocumented_field(practised):
    document = command_document("set", "show", LOOP)
    for path in ((), ("rows", 0), ("rows", 0, "entry")):
        assert_rejects_extra_field("set-show", document, path)
    levelled = next(index for index, row in enumerate(document["rows"]) if row["entry"]["levels"])
    assert_rejects_extra_field("set-show", document, ("rows", levelled, "entry", "levels"))


# cstudy learn --json


@pytest.fixture
def guides(content_root: Path, monkeypatch) -> Environment:
    """Two guides and two paths: one over a problem with a target level, one over a problem the
    catalog lacks."""
    write_hashing(content_root)
    write_path(
        content_root,
        "extras",
        ["guide: hash-functions", "problem: gone"],
        title="Extras",
        level="core",
    )
    return install(monkeypatch, make_environment(content_root))


def test_the_guides_and_the_paths(guides):
    document = command_document("learn")
    assert_valid("learn-list", document)
    assert [path["slug"] for path in document["paths"]] == ["hashing", "extras"]
    assert_ids(document, ContentType.GUIDE, ContentType.PATH)


def test_the_guides_and_the_paths_with_a_narrowed_profile(guides, monkeypatch):
    write_guide(guides.root, "tls", "TLS", domains=("security",), job_roles=("backend",))
    narrowed = replace(guides, config=Config(profile=ProfileSettings(domains=("data",))))
    install(monkeypatch, narrowed)
    document = command_document("learn")
    assert_valid("learn-list", document)
    assert document["profile"] == {
        "languages": None,
        "job_roles": None,
        "domains": ["data"],
        "hidden": {"guides": 3, "paths": 2},
    }


def test_the_guides_and_the_paths_after_a_read(guides):
    command_document("learn", "hash-functions", "--done")
    document = command_document("learn")
    assert_valid("learn-list", document)
    assert [guide["read"] for guide in document["guides"]] == [True, False]


def test_a_guide(guides):
    document = command_document("learn", "hash-maps")
    assert_valid("learn-guide", document)
    assert (document["read"], document["prerequisites"], document["problems"]) == (
        False,
        ["hash-functions"],
        ["two-sum"],
    )
    assert document["examples"]
    assert_ids(document, ContentType.GUIDE)


def test_a_guide_that_is_read(guides):
    command_document("learn", "hash-maps", "--done")
    document = command_document("learn", "hash-maps")
    assert_valid("learn-guide", document)
    assert document["read_at"] is not None


def test_a_guide_marked_read(guides):
    document = command_document("learn", "hash-functions", "--done")
    assert_valid("learn-done", document)
    assert document["already"] is False
    assert_ids(document, ContentType.GUIDE)


def test_a_guide_marked_read_again(guides):
    command_document("learn", "hash-functions", "--done")
    document = command_document("learn", "hash-functions", "--done")
    assert_valid("learn-done", document)
    assert document["already"] is True


def test_a_path(guides):
    document = command_document("learn", "--path", "hashing")
    assert_valid("learn-path", document)
    assert [step["kind"] for step in document["steps"]] == ["guide", "guide", "problem", "problem"]
    assert document["steps"][3]["level"] == 2
    assert document["next"] == document["steps"][0]
    assert_ids(document, ContentType.PATH, ContentType.GUIDE, ContentType.PROBLEM)


def test_a_path_with_progress(guides):
    command_document("learn", "hash-functions", "--done")
    add_attempt(guides, "two-sum", Language.PYTHON, status=AttemptStatus.PASSED, ended_at=NOW)
    document = command_document("learn", "--path", "hashing")
    assert_valid("learn-path", document)
    assert [step["done"] for step in document["steps"]] == [True, False, True, False]


def test_a_path_with_every_step_done(guides):
    for slug in ("hash-functions", "hash-maps"):
        command_document("learn", slug, "--done")
    add_attempt(guides, "two-sum", Language.PYTHON, status=AttemptStatus.PASSED, ended_at=NOW)
    add_attempt(
        guides,
        "tamper-evident-ledger",
        Language.PYTHON,
        status=AttemptStatus.PASSED,
        ended_at=NOW,
        levels_passed=2,
    )
    document = command_document("learn", "--path", "hashing")
    assert_valid("learn-path", document)
    assert (document["done"], document["next"]) == (4, None)


def test_a_path_with_a_step_the_catalog_lacks(guides):
    document = command_document("learn", "--path", "extras")
    assert_valid("learn-path", document)
    assert document["steps"][1]["status"] == "missing"


def test_learn_rejects_an_undocumented_field(guides):
    listing = command_document("learn")
    for path in ((), ("guides", 0), ("paths", 0), ("profile",), ("profile", "hidden")):
        assert_rejects_extra_field("learn-list", listing, path)
    assert_rejects_extra_field("learn-guide", command_document("learn", "hash-maps"), ())
    assert_rejects_extra_field("learn-done", command_document("learn", "hash-maps", "--done"), ())
    path = command_document("learn", "--path", "hashing")
    for where in ((), ("next",), ("steps", 0)):
        assert_rejects_extra_field("learn-path", path, where)


# cstudy docs --json


@pytest.fixture
def user_docs(content_root: Path, monkeypatch) -> Environment:
    write_docs(content_root)
    return install(monkeypatch, make_environment(content_root))


def test_the_docs_list(user_docs):
    document = command_document("docs")
    assert_valid("docs-list", document)
    assert [page["slug"] for page in document["pages"]] == ["getting-started", "doctor", "practice"]
    assert_ids(document, ContentType.DOC)


def test_the_docs_list_without_pages(content_root, monkeypatch):
    install(monkeypatch, make_environment(content_root))
    document = command_document("docs")
    assert_valid("docs-list", document)
    assert document["pages"] == []


def test_a_docs_page(user_docs):
    document = command_document("docs", "doctor")
    assert_valid("docs-page", document)
    assert [heading["level"] for heading in document["headings"]] == [2, 3]
    assert_ids(document, ContentType.DOC)


def test_docs_reject_an_undocumented_field(user_docs):
    listing = command_document("docs")
    for path in ((), ("pages", 1), ("pages", 1, "headings", 0)):
        assert_rejects_extra_field("docs-list", listing, path)
    page = command_document("docs", "doctor")
    for path in ((), ("headings", 0)):
        assert_rejects_extra_field("docs-page", page, path)


# cstudy test --json

TWO_SUM = "two-sum"
TWO_SUM_STUB = "python/practice/two_sum.py"
STORE_STUB = "python/practice/level_store.py"
HASH_MAP = PRACTICE / TWO_SUM / "solutions" / "hash-map.py"
STORE_REFERENCE = PHASE4 / STORE / "solutions" / "hash-map.py"
ERRORED = UserError("KeyError", "'ivy'", 'File "bank/bank.py", line 9')
TEST_VARIANTS = ("single-file", "project", "service")


def run_document(*arguments: str) -> Any:
    """The document of `cstudy test --json` or `cstudy submit --json`, which ends with the exit
    code it holds."""
    result = runner.invoke(cli.app, [*arguments, "--json"])
    document = json.loads(result.stdout)
    assert result.exit_code == document["exit_code"], result.output
    return document


def variant_errors(variant: str, document: Any) -> list[str]:
    """What is wrong with `document` as the `variant` of `test.schema.json`."""
    defs = load_schema("test")["$defs"]
    validator = Draft202012Validator({"$ref": f"#/$defs/{variant}", "$defs": defs})
    return [
        f"{'/'.join(str(step) for step in error.absolute_path) or '<document>'}: {error.message}"
        for error in validator.iter_errors(document)
    ]


def assert_test_document(document: Any, variant: str) -> None:
    """`document` is valid, and no variant but `variant` accepts it."""
    assert variant_errors(variant, document) == []
    assert_valid("test", document)
    assert [other for other in TEST_VARIANTS if not variant_errors(other, document)] == [variant]
    assert_ids(document, ContentType.PROBLEM)


@pytest.fixture
def solving(tmp_path, monkeypatch) -> Environment:
    """Two Sum, with a time box, and the progressive Level Store, run by a real Python runner."""
    root = repository_root(tmp_path, PRACTICE)
    shutil.copytree(PHASE4, root / "problems", dirs_exist_ok=True)
    environment = install(monkeypatch, e2e_environment(root))
    start_attempt(environment, StartRequest(TWO_SUM, timer_s=1500))
    start_attempt(environment, StartRequest(STORE))
    return environment


def test_a_passing_function_run(solving):
    solving.workspace.write_text(TWO_SUM_STUB, HASH_MAP.read_text())
    document = run_document("test", TWO_SUM)
    assert_test_document(document, "single-file")
    assert (document["outcome"], document["exit_code"]) == ("passed", 0)
    assert document["timer"]["limit_s"] == 1500


def test_a_failing_function_run(solving):
    solving.workspace.write_text(TWO_SUM_STUB, "def two_sum(nums, target):\n    return [3, 3]\n")
    document = run_document("test", TWO_SUM)
    assert_test_document(document, "single-file")
    failed = next(found for found in document["cases"] if found["status"] == "fail")
    assert {"input", "expected", "actual"} <= set(failed)


def test_a_function_run_with_an_exception(solving):
    solving.workspace.write_text(
        TWO_SUM_STUB, "def two_sum(nums, target):\n    raise KeyError(1)\n"
    )
    document = run_document("test", TWO_SUM)
    assert_test_document(document, "single-file")
    assert document["cases"][0]["error"]["type"] == "KeyError"


def test_a_function_run_of_code_that_does_not_load(solving):
    solving.workspace.write_text(TWO_SUM_STUB, "def two_sum(:\n")
    document = run_document("test", TWO_SUM)
    assert_test_document(document, "single-file")
    assert (document["outcome"], document["cases"]) == ("load_failed", [])
    assert document["load_error"]["type"]
    assert document["diagnostics"]


def test_a_function_run_with_oracle_inputs(solving):
    solving.workspace.write_text(TWO_SUM_STUB, HASH_MAP.read_text())
    document = run_document("test", TWO_SUM, "--stress", "3")
    assert_test_document(document, "single-file")
    assert [found["seed"] for found in document["oracle"]["inputs"]] == [1, 2, 3]


def test_a_progressive_run_with_levels(solving):
    solving.workspace.write_text(STORE_STUB, STORE_REFERENCE.read_text())
    document = run_document("test", STORE)
    assert_test_document(document, "single-file")
    assert document["levels"]["ran_up_to"] == 1


class CasesAndBench:
    """Answers the cases with `cases` and benches with `optimal_user`."""

    def __init__(self) -> None:
        self.cases = ScriptedRunnerProcess(two_sum)
        self.bench_process: ScriptedBenchProcess = optimal_user()

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        return self.cases.run(launch, request, listener)

    def bench(self, launch: RunnerLaunch, request: BenchRequest) -> BenchReport:
        return self.bench_process.bench(launch, request)


def scripted_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, problems: Path, slug: str, process: Any
) -> Environment:
    """`slug` started in Python, its cases answered by `process`."""
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    environment = make_environment(
        repository_root(tmp_path, problems), toolchains=toolchains, runner_process=process
    )
    install(monkeypatch, environment)
    start_attempt(environment, StartRequest(slug, Language.PYTHON))
    return environment


def yours_answers(outcome: CaseOutcome) -> Callable[[RunJob, RunCase], CaseOutcome]:
    """`outcome` for every case of your code; a reference solution, whose job ID is the slug and
    the approach, answers as ever."""

    def answer(job: RunJob, case: RunCase) -> CaseOutcome:
        return two_sum(job, case) if "/" in job.job_id else outcome

    return answer


def test_a_function_run_with_a_perf_check(tmp_path, monkeypatch):
    scripted_environment(tmp_path, monkeypatch, PRACTICE, TWO_SUM, CasesAndBench())
    document = run_document("test", TWO_SUM, "--perf")
    assert_test_document(document, "single-file")
    assert document["perf"]["verdict"] == "unknown"


@pytest.mark.parametrize(
    ("outcome", "status"),
    [
        (Raised(ERRORED, 1000, stdout="printed\n"), "error"),
        (InvalidOutput("not a list", 1000), "invalid"),
        (TimedOut(500), "timeout"),
        (Crashed(139, ("segfault",)), "error"),
        (NotRun("the runner did not start"), "not_run"),
    ],
    ids=["raised", "invalid", "timed-out", "crashed", "not-run"],
)
def test_a_function_run_of_each_kind_of_outcome(tmp_path, monkeypatch, outcome, status):
    scripted_environment(
        tmp_path, monkeypatch, PRACTICE, TWO_SUM, ScriptedRunnerProcess(yours_answers(outcome))
    )
    document = run_document("test", TWO_SUM)
    assert_test_document(document, "single-file")
    assert document["cases"][0]["status"] == status


def test_a_function_run_with_a_case_over_its_time_limit(tmp_path, monkeypatch):
    def slow(job: RunJob, case: RunCase) -> CaseOutcome:
        correct = two_sum(job, case)
        return correct if "/" in job.job_id else Returned(correct.output, 400_000_000)

    scripted_environment(tmp_path, monkeypatch, PRACTICE, TWO_SUM, ScriptedRunnerProcess(slow))
    document = run_document("test", TWO_SUM, "--time-limit=10ms")
    assert_test_document(document, "single-file")
    assert document["cases"][0]["status"] == "tle"
    assert document["cases"][0]["time_limit_basis"] is None


def test_a_design_run_with_an_exception_in_an_operation(tmp_path, monkeypatch):
    raising = Raised(ERRORED, 1000, op_index=1, partial_output=(None,))
    scripted_environment(
        tmp_path, monkeypatch, PRACTICE, "lru-cache", ScriptedRunnerProcess(yours_answers(raising))
    )
    document = run_document("test", "lru-cache")
    assert_test_document(document, "single-file")
    assert document["cases"][0]["op_index"] == 1
    assert "ops" in document["cases"][0]["input"]


@pytest.mark.parametrize(
    ("answer", "status", "failures"),
    [(queue, "pass", 0), (duplicating, "fail", 3), (stalling, "stalled", 3)],
    ids=["passing", "failing", "stalling"],
)
def test_a_concurrent_run_with_stress(tmp_path, monkeypatch, answer, status, failures):
    scripted_environment(
        tmp_path,
        monkeypatch,
        CONCURRENCY_PROBLEMS,
        "bounded-blocking-queue",
        ScriptedRunnerProcess(answer),
    )
    document = run_document("test", "bounded-blocking-queue")
    assert_test_document(document, "single-file")
    assert {found["status"] for found in document["stress"]} == {status}
    assert [len(found["failures"]) for found in document["stress"]] == [failures] * 2


@pytest.fixture
def project_process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess()


@pytest.fixture
def running_project(tmp_path, monkeypatch, project_process) -> Environment:
    environment = project_environment(tmp_path, project_process)
    install(monkeypatch, environment)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    return environment


def test_a_passing_project_run(running_project):
    document = run_document("test")
    assert_test_document(document, "project")
    assert document["outcome"] == "passed"


def test_a_project_run_with_every_kind_of_test(running_project, project_process):
    failed = AssertionFailed("assert -1 == 5", 1000, comparison=Comparison(5, -1), stdout="x\n")
    project_process.tests = (
        LEVEL_1_TEST,
        SuiteTest("tests/test_level_1.py::test_ex2", failed),
        SuiteTest("tests/test_overdraft.py::test_refuses", Passed(1000)),
        SuiteTest("README.md::test_readme", Passed(1000)),
        SuiteTest("tests/test_overdraft.py::test_later", Skipped("not yet", 0)),
        SuiteTest("tests/test_level_1.py::test_ex3", Raised(ERRORED, 1000)),
        SuiteTest("tests/test_level_1.py::test_ex4", Crashed(139, ("segfault",))),
        SuiteTest("tests/test_level_1.py::test_ex5", TimedOut(5000)),
    )
    project_process.stopped_early = "the runner crashed"
    document = run_document("test")
    assert_test_document(document, "project")
    assert document["outcome"] == "failed"
    assert {found["origin"] for found in document["cases"]} == {"level", "yours", "starter"}
    assert document["stopped_early"] == "the runner crashed"


def test_a_project_run_of_a_suite_that_does_not_load(running_project, project_process):
    project_process.tests = ()
    project_process.suite_load_error = ERRORED
    document = run_document("test")
    assert_test_document(document, "project")
    assert document["outcome"] == "load_failed"


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox(exec_outcome=CommandOutcome(0, "ok 1 - rooms\n"))


@pytest.fixture
def served(engine) -> FakeApp:
    right = HttpResponse(200, {}, b'{"ok": true}', 5_000_000)
    return FakeApp([], answers={"/a": right, "/b": right})


@pytest.fixture
def service(tmp_path, monkeypatch, engine, served) -> Environment:
    """A service project with two levels and a visible and a hidden case on the first, through
    a fake engine and fake HTTP clients."""
    ok = {"status": 200, "body": {"ok": True}}

    def case(case_id: str, level: int, path: str, **fields: object) -> dict[str, object]:
        request = {"method": "GET", "path": path}
        return {"id": case_id, "level": level, "request": request, "expected": ok, **fields}

    root = make_content(tmp_path)
    document = meta_document()
    document["levels"] = [{"level": 1, "title": "One"}, {"level": 2, "title": "Two"}]
    write_problem(root, document)
    write_cases(
        root,
        [case("v1", 1, "/a", visible=True), case("h1", 1, "/a"), case("v2", 2, "/b", visible=True)],
    )

    def clients(_endpoints: StackEndpoints) -> StackClients:
        return StackClients(served, FakeMockControl([]))

    environment = install(
        monkeypatch, make_environment(root, sandbox=engine, stack_clients=clients)
    )
    (root / FOLDER / "node_modules").mkdir(parents=True)
    assert runner.invoke(cli.app, ["start", SERVICE_SLUG, "--no-open", "--yes"]).exit_code == 0
    return environment


def test_a_passing_service_run(service):
    document = run_document("test", SERVICE_SLUG)
    assert_test_document(document, "service")
    assert document["outcome"] == "passed"
    assert [found["id"] for found in document["tests"]] == ["commands.test"]


def test_a_service_run_with_a_failing_case(service, served):
    served.answers["/a"] = HttpResponse(500, {}, b"{}", 5_000_000)
    document = run_document("test", SERVICE_SLUG)
    assert_test_document(document, "service")
    assert document["outcome"] == "failed"
    assert document["cases"][0]["status"] == "fail"


def test_a_service_run_with_a_failing_command(service, engine):
    engine.exec_outcome = CommandOutcome(1, "not ok\n")
    document = run_document("test", SERVICE_SLUG)
    assert_test_document(document, "service")
    assert document["tests"][0]["message"] == "exited with 1"


def test_a_service_run_with_a_command_that_timed_out(service, engine):
    engine.exec_outcome = CommandOutcome(1, "", timed_out=True)
    document = run_document("test", SERVICE_SLUG)
    assert_test_document(document, "service")
    assert document["tests"][0]["status"] == "timeout"


def test_a_service_run_whose_stack_does_not_start(service, engine):
    engine.start_error = StackStartError(StartupFailure.APP_EXITED, "your app exited", "tail\n")
    document = run_document("test", SERVICE_SLUG)
    assert_test_document(document, "service")
    assert (document["outcome"], document["tests"]) == ("load_failed", [])


def test_a_service_run_without_docker(service, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)
    assert runner.invoke(cli.app, ["test", SERVICE_SLUG, "--json"]).exit_code == (
        ExitCode.ENVIRONMENT_ERROR
    )


def test_a_function_run_rejects_an_undocumented_field(solving):
    solving.workspace.write_text(TWO_SUM_STUB, "def two_sum(nums, target):\n    return [3, 3]\n")
    document = run_document("test", TWO_SUM, "--stress", "2")
    paths: tuple[tuple[str | int, ...], ...] = (
        (),
        ("timer",),
        ("build",),
        ("tally",),
        ("cases", 0),
        ("oracle",),
        ("oracle", "inputs", 0),
    )
    for path in paths:
        assert_rejects_extra_field("test", document, path)


def test_a_progressive_run_rejects_an_undocumented_field(solving):
    document = run_document("test", STORE)
    assert_rejects_extra_field("test", document, ("levels",))


def test_a_run_with_an_exception_rejects_an_undocumented_field(tmp_path, monkeypatch):
    raised = Raised(ERRORED, 1000, op_index=1, partial_output=(None,))
    scripted_environment(
        tmp_path, monkeypatch, PRACTICE, "lru-cache", ScriptedRunnerProcess(yours_answers(raised))
    )
    document = run_document("test", "lru-cache")
    assert_rejects_extra_field("test", document, ("cases", 0, "error"))


def test_a_function_run_of_code_that_does_not_load_rejects_an_undocumented_field(solving):
    solving.workspace.write_text(TWO_SUM_STUB, "def two_sum(:\n")
    document = run_document("test", TWO_SUM)
    for path in (("load_error",), ("diagnostics", 0)):
        assert_rejects_extra_field("test", document, path)


@pytest.mark.parametrize("answer", [duplicating, stalling], ids=["failing", "stalling"])
def test_a_concurrent_run_rejects_an_undocumented_field(tmp_path, monkeypatch, answer):
    scripted_environment(
        tmp_path,
        monkeypatch,
        CONCURRENCY_PROBLEMS,
        "bounded-blocking-queue",
        ScriptedRunnerProcess(answer),
    )
    document = run_document("test", "bounded-blocking-queue")
    for path in (("stress", 0), ("stress", 0, "failures", 0)):
        assert_rejects_extra_field("test", document, path)


def test_a_function_run_with_a_perf_check_rejects_an_undocumented_field(tmp_path, monkeypatch):
    scripted_environment(tmp_path, monkeypatch, PRACTICE, TWO_SUM, CasesAndBench())
    document = run_document("test", TWO_SUM, "--perf")
    assert_rejects_extra_field("test", document, ("perf",))


def test_a_project_run_rejects_an_undocumented_field(running_project, project_process):
    project_process.tests = (
        LEVEL_1_TEST,
        SuiteTest("t::fail", AssertionFailed("assert", 1, comparison=Comparison(1, 2))),
        SuiteTest("t::raise", Raised(ERRORED, 1)),
    )
    document = run_document("test")
    for path in ((), ("levels",), ("build",), ("cases", 0), ("cases", 2, "error")):
        assert_rejects_extra_field("test", document, path)


def test_a_service_run_rejects_an_undocumented_field(service):
    document = run_document("test", SERVICE_SLUG)
    for path in ((), ("tests", 0), ("cases", 0), ("tally",)):
        assert_rejects_extra_field("test", document, path)


def test_a_run_of_no_variant_is_rejected(solving):
    document = run_document("test", STORE)
    document["stopped_early"] = None
    assert schema_errors("test", document)
    assert [variant for variant in TEST_VARIANTS if not variant_errors(variant, document)] == []


# cstudy submit --json

BANK_CASES = json.loads(
    (PROJECT_PROBLEMS / PROJECT_SLUG / "tests.json").read_text(encoding="utf-8")
)["cases"]
BANK_EXPECTED = {case["id"]: case["expected"] for case in BANK_CASES}
DEADLOCK = Stalled(
    (), 7, op_index=2, reason="op 2 (deposit): deadlock at 0 ms", partial_output=(None, True)
)


def correct(job: RunJob, case: RunCase) -> CaseOutcome:
    return Returned(BANK_EXPECTED[case.id], 1000)


def wrong_on(*case_ids: str) -> Callable[[RunJob, RunCase], CaseOutcome]:
    def answer(job: RunJob, case: RunCase) -> CaseOutcome:
        return Returned(["wrong"], 1000) if case.id in case_ids else correct(job, case)

    return answer


@pytest.fixture
def submitting(tmp_path, monkeypatch, project_process) -> Environment:
    """A project attempt, timed, whose cases `project_process` answers correctly."""
    project_process.answer = correct
    environment = project_environment(tmp_path, project_process)
    install(monkeypatch, environment)
    start_attempt(environment, StartRequest(PROJECT_SLUG, timer_s=5400))
    return environment


def assert_submit_document(document: Any) -> None:
    assert_valid("submit", document)
    assert_ids(document, ContentType.PROBLEM)


def test_a_passing_submit(submitting):
    document = run_document("submit")
    assert_submit_document(document)
    assert (document["outcome"], document["exit_code"], document["mode"]) == ("passed", 0, "new")
    assert document["timer"]["limit_s"] == 5400


def test_a_failing_submit(submitting, project_process):
    project_process.answer = wrong_on("h1")
    document = run_document("submit")
    assert_submit_document(document)
    assert document["outcome"] == "failed"


def test_a_submit_of_code_that_does_not_load(submitting, project_process):
    project_process.load_error = ERRORED
    document = run_document("submit")
    assert_submit_document(document)
    assert (document["outcome"], document["load_error"]["type"]) == ("load_failed", "KeyError")


def test_a_submit_with_a_deadlocked_case(submitting, project_process):
    project_process.answer = lambda job, case: DEADLOCK if case.id == "h2" else correct(job, case)
    document = run_document("submit")
    assert_submit_document(document)
    assert "stalled" in {found["status"] for found in document["cases"]}


def test_a_mock_submit(submitting):
    start_attempt(submitting, StartRequest(PROJECT_SLUG, fresh=True, mock=True))
    document = run_document("submit")
    assert_submit_document(document)
    assert document["mode"] == "mock"
    assert all(found["visible"] for found in document["cases"])


@pytest.fixture
def stressed(tmp_path, monkeypatch) -> tuple[Environment, ScriptedProjectProcess]:
    """A project attempt with stress cases, at its second level."""
    process = ScriptedProjectProcess()
    environment = stress_project_environment(tmp_path, process)
    process.answer = tally_answers(environment.problems.load(TALLY_SLUG))
    install(monkeypatch, environment)
    start_attempt(environment, StartRequest(TALLY_SLUG))
    attempt = find_attempt(environment, TALLY_SLUG)
    environment.progress.update_attempt(replace(attempt, level_unlocked=2))
    return environment, process


def test_a_submit_with_stress_cases(stressed):
    document = run_document("submit")
    assert_submit_document(document)
    assert document["stress"]
    assert {found["level"] for found in document["stress"]} <= {1, 2}


def test_a_submit_with_a_racy_stress_case(stressed):
    environment, process = stressed
    process.answer = tally_answers(environment.problems.load(TALLY_SLUG), racy=True)
    document = run_document("submit")
    assert_submit_document(document)
    assert document["outcome"] == "failed"
    assert any(found["failures"] for found in document["stress"])


def test_a_submit_of_a_service_project(service):
    document = run_document("submit", SERVICE_SLUG)
    assert_submit_document(document)
    assert document["startup_s"] == 2.5


def test_a_submit_rejects_an_undocumented_field(stressed):
    environment, process = stressed
    process.answer = tally_answers(environment.problems.load(TALLY_SLUG), racy=True)
    document = run_document("submit")
    paths: tuple[tuple[str | int, ...], ...] = (
        (),
        ("levels",),
        ("level_tallies", 0),
        ("cases", 0),
        ("stress", 0),
        ("tally",),
    )
    for path in paths:
        assert_rejects_extra_field("submit", document, path)
    racy = next(index for index, found in enumerate(document["stress"]) if found["failures"])
    assert_rejects_extra_field("submit", document, ("stress", racy, "failures", 0))


def test_a_submit_that_did_not_load_rejects_an_undocumented_field(submitting, project_process):
    project_process.load_error = ERRORED
    document = run_document("submit")
    assert_rejects_extra_field("submit", document, ("load_error",))
