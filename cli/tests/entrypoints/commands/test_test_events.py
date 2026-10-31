"""`cstudy test --events` on function, design and progressive problems: each case as it starts
and ends, the build, time-limit revisions, the diagnostics of code that does not build or load,
and the level a run opens (docs/specs/cli.md#event-stream)."""

import json
from datetime import timedelta
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner, Result

from coding_study.application.ports import BuildFailed, LanguageRunner, Prepared
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.domain.runs import UserError
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.e2e import e2e_environment
from tests.fakes import (
    FAKE_LAUNCH,
    FakeClock,
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
    two_sum,
)
from tests.helpers import SCHEMAS_DIRECTORY

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
PRACTICE = FIXTURES / "practice" / "problems"
PHASE4 = FIXTURES / "phase4" / "problems"
STUB = "python/practice/two_sum.py"
SOLVED = (PRACTICE / "0001-two-sum" / "solutions" / "hash-map.py").read_text()
LEVEL_STORE_STUB = "python/practice/level_store.py"
LEVEL_STORE = (PHASE4 / "0001-level-store" / "solutions" / "hash-map.py").read_text()
SLOW_SOLUTION = (
    "import time\n\ndef two_sum(nums, target):\n    time.sleep(0.15)\n    return [1, 2]\n"
)
WRONG_SOLUTION = "def two_sum(nums, target):\n    return [0, 0]\n"
BROKEN = UserError("SyntaxError", "invalid syntax (two_sum.py, line 4)", "two_sum.py:4")
COMPILER_LINE = "go/practice/two_sum/two_sum.go:4:9: undefined: undefinedThing"
TSC_LINE = (
    "practice/two-sum.ts(3,5): error TS2322: Type 'string' is not assignable to type 'number'."
)
SINGLE_FILE_TYPES = {
    "run_start",
    "output",
    "build",
    "case_start",
    "case_result",
    "case_revised",
    "diagnostic",
    "run_end",
}
"""Of function problems; levels, stress runs and `--perf` have tests of their own."""
VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
)


@pytest.fixture
def environment(tmp_path, monkeypatch):
    """Two-sum in Python, run by the mini runner."""
    environment = e2e_environment(repository_root(tmp_path, PRACTICE))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum"))
    return environment


@pytest.fixture
def level_store(tmp_path, monkeypatch):
    """Level-store, a progressive problem, solved in Python."""
    environment = e2e_environment(repository_root(tmp_path, PHASE4))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("level-store", Language.PYTHON))
    environment.workspace.write_text(LEVEL_STORE_STUB, LEVEL_STORE)
    return environment


def scripted(
    tmp_path,
    monkeypatch,
    language: Language,
    runner: LanguageRunner | None = None,
    process: ScriptedRunnerProcess | None = None,
):
    """Two-sum in `language`, built by `runner` and run by `process`; Python computes the
    expected values of generated cases."""
    runners: dict[Language, LanguageRunner] = {Language.PYTHON: FakeLanguageRunner()}
    runners[language] = runner or FakeLanguageRunner()
    toolchains = FakeToolchains(runners=runners, stub_generators={language: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, PRACTICE),
        toolchains=toolchains,
        runner_process=process or ScriptedRunnerProcess(two_sum),
    )
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("two-sum", language))
    return environment


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, ["test", *arguments])


def events(*arguments: str) -> list[dict]:
    return [json.loads(line) for line in cs(*arguments, "--events").stdout.splitlines()]


def warmed(*arguments: str) -> list[dict]:
    """The second run's events, once generated expected values are cached."""
    events(*arguments)
    return events(*arguments)


def types(found: list[dict]) -> list[str]:
    return [event["type"] for event in found]


def of_type(found: list[dict], event_type: str) -> list[dict]:
    return [event for event in found if event["type"] == event_type]


def timeless(event: dict) -> dict:
    """Two runs of one case take different times."""
    return event | {"duration_ns": None}


def untimed(document: dict) -> dict:
    """A `--json` document without the times that differ from run to run."""
    cases = [timeless(case) for case in document["cases"]]
    return document | {"cases": cases, "duration_s": None}


def test_a_run_reports_each_case_as_it_starts_and_ends(environment):
    environment.workspace.write_text(STUB, SOLVED)
    assert types(warmed()) == ["run_start", *(["case_start", "case_result"] * 4), "run_end"]


def test_the_start_names_the_run_and_what_it_will_report(environment):
    assert events()[0] == {
        "type": "run_start",
        "version": 1,
        "command": "test",
        "slug": "two-sum",
        "language": "python",
        "attempt_id": 1,
        "mode": "new",
        "levels": None,
        "kind": "function",
        "track": "dsa",
        "timer": None,
        "time_limit": None,
        "planned": {
            "cases": 4,
            "visible": 2,
            "hidden": 1,
            "generated": 1,
            "oracle_inputs": 0,
            "stress": None,
        },
    }


def test_the_start_names_the_time_box(tmp_path, monkeypatch):
    environment = scripted(tmp_path, monkeypatch, Language.PYTHON)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON, fresh=True, timer_s=1500))
    assert isinstance(environment.clock, FakeClock)
    environment.clock.advance(timedelta(seconds=90))
    assert events()[0]["timer"] == {"elapsed_s": 90, "limit_s": 1500}


def test_the_start_names_the_time_limit_the_run_asks_for(environment):
    assert events("--time-limit=1500ms", "--case", "ex1")[0]["time_limit"] == "1500ms"


def test_the_start_counts_the_oracle_inputs(environment):
    assert events("--stress", "3")[0]["planned"]["oracle_inputs"] == 3


def test_computing_expected_values_is_an_output_event(environment):
    assert events()[1] == {
        "type": "output",
        "version": 1,
        "text": "computing expected values for generated cases (one-time)",
    }


def test_a_started_case_names_its_visibility(environment):
    assert of_type(warmed(), "case_start")[0] == {
        "type": "case_start",
        "version": 1,
        "id": "ex1",
        "visible": True,
        "level": None,
    }


def test_a_case_result_is_the_json_documents_case(environment):
    environment.workspace.write_text(STUB, WRONG_SOLUTION)
    document = json.loads(cs("--json").stdout)
    h1 = of_type(events(), "case_result")[2]
    expected = {"type": "case_result", "version": 1} | document["cases"][2] | {"level": None}
    assert timeless(h1) == timeless(expected)


def test_the_end_carries_the_json_document(environment):
    environment.workspace.write_text(STUB, SOLVED)
    document = json.loads(cs("--json").stdout)
    assert untimed(events()[-1]["summary"]) == untimed(document)


def test_a_passing_run_ends_passed_with_exit_code_0(environment):
    environment.workspace.write_text(STUB, SOLVED)
    end = events()[-1]
    assert (end["outcome"], end["exit_code"], end["message"]) == ("passed", 0, None)


def test_a_failing_run_exits_as_its_end_says(environment):
    environment.workspace.write_text(STUB, WRONG_SOLUTION)
    result = cs("--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["outcome"], end["exit_code"]) == (1, "failed", 1)


def test_a_design_problem_names_its_kind(environment):
    start_attempt(environment, StartRequest("lru-cache"))
    assert events("lru-cache")[0]["kind"] == "design"


def test_a_case_that_names_no_case_writes_no_event(environment):
    result = cs("--case", "nope", "--events")
    assert (result.exit_code, result.stdout) == (ExitCode.USAGE_ERROR, "")


def test_all_is_accepted_and_changes_nothing(environment):
    environment.workspace.write_text(STUB, SOLVED)
    warmed()
    assert types(events("--all")) == types(events())


@pytest.mark.parametrize("flag", ["--json", "--watch", "--debug"])
def test_events_exclude_the_other_outputs(environment, flag):
    result = cs(flag, "--events")
    assert (result.exit_code, result.stderr) == (3, f"error: --events excludes {flag}\n")


def test_an_oracle_input_starts_as_one(environment):
    environment.workspace.write_text(STUB, SOLVED)
    started = of_type(events("--stress", "1", "--seed", "17"), "case_start")[-1]
    assert (started["id"], started["oracle"], started["seed"]) == ("oracle-17", True, 17)


def test_an_oracle_input_is_the_json_documents_input(environment):
    environment.workspace.write_text(STUB, SOLVED)
    document = json.loads(cs("--stress", "2", "--seed", "17", "--json").stdout)
    oracle = of_type(events("--stress", "2", "--seed", "17"), "case_result")[-1]
    entry = document["oracle"]["inputs"][-1] | {"level": None, "oracle": True}
    assert timeless(oracle) == timeless({"type": "case_result", "version": 1} | entry)


def test_a_case_over_its_time_limit_passes_then_is_revised(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    found = events("--time-limit=20ms", "--case", "ex1")
    revised = of_type(found, "case_revised")
    assert (of_type(found, "case_result")[0]["status"], len(revised), revised[0]["status"]) == (
        "pass",
        1,
        "tle",
    )


def test_a_revision_is_the_json_documents_case(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    document = json.loads(cs("--time-limit=20ms", "--case", "ex1", "--json").stdout)
    (revised,) = of_type(events("--time-limit=20ms", "--case", "ex1"), "case_revised")
    expected = {"type": "case_revised", "version": 1} | document["cases"][0] | {"level": None}
    assert timeless(revised) == timeless(expected)


def test_a_revision_comes_after_every_result(environment):
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    found = types(events("--time-limit=20ms", "--case", "ex1", "--case", "ex2"))
    last_result = len(found) - 1 - found[::-1].index("case_result")
    assert found.index("case_revised") > last_result


def test_a_case_within_its_time_limit_is_not_revised(environment):
    environment.workspace.write_text(STUB, SOLVED)
    assert of_type(events("--time-limit=1500ms", "--case", "ex1"), "case_revised") == []


def test_a_language_without_a_build_writes_no_build_event(environment):
    assert of_type(events(), "build") == []


def test_a_build_is_written_before_the_first_case(tmp_path, monkeypatch):
    runner = FakeLanguageRunner(Prepared(FAKE_LAUNCH, build_note="go, warm"))
    scripted(tmp_path, monkeypatch, Language.GO, runner=runner)
    found = warmed("--case", "ex1")
    assert (types(found)[1:3], found[1]["note"]) == (["build", "case_start"], "go, warm")


def test_a_failed_build_is_written_without_a_note(tmp_path, monkeypatch):
    runner = FakeLanguageRunner(BuildFailed((COMPILER_LINE,)))
    scripted(tmp_path, monkeypatch, Language.GO, runner=runner)
    (build,) = of_type(events(), "build")
    assert (set(build), build["note"]) == ({"type", "version", "seconds", "note"}, None)


def test_code_that_does_not_load_is_a_diagnostic_at_the_users_file(tmp_path, monkeypatch):
    process = ScriptedRunnerProcess(two_sum, {"two-sum": BROKEN})
    scripted(tmp_path, monkeypatch, Language.PYTHON, process=process)
    (diagnostic,) = of_type(events(), "diagnostic")
    assert diagnostic == {
        "type": "diagnostic",
        "version": 1,
        "source": "load",
        "severity": "error",
        "file": STUB,
        "line": 4,
        "column": None,
        "code": "SyntaxError",
        "message": "invalid syntax (two_sum.py, line 4)",
    }


def test_code_that_does_not_load_ends_load_failed_with_exit_code_2(tmp_path, monkeypatch):
    process = ScriptedRunnerProcess(two_sum, {"two-sum": BROKEN})
    scripted(tmp_path, monkeypatch, Language.PYTHON, process=process)
    result = cs("--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["outcome"], end["exit_code"]) == (2, "load_failed", 2)


def test_code_that_does_not_load_writes_no_case(tmp_path, monkeypatch):
    process = ScriptedRunnerProcess(two_sum, {"two-sum": BROKEN})
    scripted(tmp_path, monkeypatch, Language.PYTHON, process=process)
    assert types(warmed()) == ["run_start", "diagnostic", "run_end"]


def test_each_compiler_line_is_a_build_diagnostic(tmp_path, monkeypatch):
    runner = FakeLanguageRunner(BuildFailed((COMPILER_LINE,)))
    scripted(tmp_path, monkeypatch, Language.GO, runner=runner)
    assert of_type(events(), "diagnostic") == [
        {
            "type": "diagnostic",
            "version": 1,
            "source": "build",
            "severity": "error",
            "file": None,
            "line": None,
            "column": None,
            "code": None,
            "message": COMPILER_LINE,
        }
    ]


def test_code_that_does_not_build_ends_build_failed_with_exit_code_2(tmp_path, monkeypatch):
    runner = FakeLanguageRunner(BuildFailed((COMPILER_LINE,)))
    scripted(tmp_path, monkeypatch, Language.GO, runner=runner)
    result = cs("--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["outcome"], end["exit_code"]) == (2, "build_failed", 2)


def test_a_type_error_is_a_typecheck_diagnostic_at_its_place(tmp_path, monkeypatch):
    runner = FakeLanguageRunner(BuildFailed((TSC_LINE,)))
    scripted(tmp_path, monkeypatch, Language.TYPESCRIPT, runner=runner)
    (diagnostic,) = of_type(events("--typecheck"), "diagnostic")
    assert diagnostic == {
        "type": "diagnostic",
        "version": 1,
        "source": "typecheck",
        "severity": "error",
        "file": "typescript/practice/two-sum.ts",
        "line": 3,
        "column": 5,
        "code": "TS2322",
        "message": "Type 'string' is not assignable to type 'number'.",
    }


def test_the_diagnostics_are_the_json_documents(tmp_path, monkeypatch):
    runner = FakeLanguageRunner(BuildFailed((TSC_LINE,)))
    scripted(tmp_path, monkeypatch, Language.TYPESCRIPT, runner=runner)
    (diagnostic,) = of_type(events("--typecheck"), "diagnostic")
    document = json.loads(cs("--typecheck", "--json").stdout)
    assert document["diagnostics"] == [{key: diagnostic[key] for key in list(diagnostic)[2:]}]


def test_a_progressive_start_names_its_levels(level_store):
    start = events()[0]
    assert (start["kind"], start["levels"]) == (
        "progressive",
        {"up_to": 1, "unlocked": 1, "last": 3},
    )


def test_a_progressive_case_names_its_level(level_store):
    assert {event["level"] for event in of_type(events(), "case_result")} == {1}


def test_a_progressive_run_grades_no_level_of_its_own(level_store):
    assert of_type(events(), "level_result") == []


def test_a_run_that_opens_a_level_names_it_last(level_store):
    found = events()
    assert types(found)[-2:] == ["level_unlocked", "run_end"]


def test_an_opened_progressive_level_has_no_test_file(level_store):
    assert of_type(events(), "level_unlocked")[0] == {
        "type": "level_unlocked",
        "version": 1,
        "level": 2,
        "title": "Remove and size",
        "methods": ["remove(key: str) -> bool", "size() -> int"],
        "tests": None,
        "statement": ".statements/level-store.md",
    }


def test_a_run_that_opens_no_level_names_none(level_store):
    level_store.workspace.write_text(LEVEL_STORE_STUB, "class LevelStore:\n    pass\n")
    assert of_type(events(), "level_unlocked") == []


def every_event(environment, tmp_path, monkeypatch) -> list[dict]:
    environment.workspace.write_text(STUB, WRONG_SOLUTION)
    found = events("--stress", "2")
    environment.workspace.write_text(STUB, SLOW_SOLUTION)
    found += events("--time-limit=20ms")
    process = ScriptedRunnerProcess(two_sum, {"two-sum": BROKEN})
    scripted(tmp_path / "load", monkeypatch, Language.PYTHON, process=process)
    found += events()
    runner = FakeLanguageRunner(Prepared(FAKE_LAUNCH, build_note="go, warm"))
    scripted(tmp_path / "go", monkeypatch, Language.GO, runner=runner)
    found += events()
    runner = FakeLanguageRunner(BuildFailed((TSC_LINE,)))
    scripted(tmp_path / "typecheck", monkeypatch, Language.TYPESCRIPT, runner=runner)
    return found + events("--typecheck")


def test_every_event_matches_the_schema(environment, tmp_path, monkeypatch):
    found = every_event(environment, tmp_path, monkeypatch)
    assert [event for event in found if not VALIDATOR.is_valid(event)] == []


def test_every_progressive_event_matches_the_schema(level_store):
    found = events() + events()
    assert [event for event in found if not VALIDATOR.is_valid(event)] == []


def test_function_runs_write_every_event_type_of_their_kind(environment, tmp_path, monkeypatch):
    found = every_event(environment, tmp_path, monkeypatch)
    assert set(types(found)) == SINGLE_FILE_TYPES
