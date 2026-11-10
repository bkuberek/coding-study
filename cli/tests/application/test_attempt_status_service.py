"""`cstudy status` of a service project (docs/specs/cli.md#cstudy-status): its next step names the
commands a service project takes, it has code intelligence in a sidecar in TypeScript and Python
and none yet in another language, and it names its mock servers with the scenarios a dev stack may
switch them to."""

from datetime import timedelta

import pytest

from coding_study.application.attempt_status import SERVICE_NEXT, attempt_status
from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.code_intelligence import NoCodeIntelligence
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.service_project import MockScenarios
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from tests.fakes import NOW, make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    SLUG,
    make_content,
    meta_document,
    write_mock,
    write_problem,
)


@pytest.fixture
def service(tmp_path) -> Environment:
    root = make_content(tmp_path)
    write_problem(root)
    environment = make_environment(root, sandbox=FakeSandbox())
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))
    return environment


def test_a_typescript_service_project_has_code_intelligence_in_its_sidecar(service):
    assert attempt_status(service, None, None).no_code_intelligence is None


def test_a_service_project_in_a_language_without_a_sidecar_server_has_none_yet(tmp_path):
    root = make_content(tmp_path)
    write_problem(root, {**meta_document(), "languages": ["go"]})
    environment = make_environment(root, sandbox=FakeSandbox())
    start_attempt(environment, StartRequest(SLUG, Language.GO))

    assert attempt_status(environment, None, None).no_code_intelligence is (
        NoCodeIntelligence.SERVICE_PROJECT
    )


def test_a_service_project_without_mock_servers_names_none(service):
    assert attempt_status(service, None, None).service == ()


def test_each_mock_server_is_named_with_its_visible_scenarios_only(tmp_path):
    root = make_content(tmp_path)
    write_problem(root, meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}]))
    write_mock(root)
    environment = make_environment(root, sandbox=FakeSandbox())
    start_attempt(environment, StartRequest(SLUG, Language.TYPESCRIPT))

    assert attempt_status(environment, None, None).service == (
        MockScenarios("room-vendor", ("outage",)),
    )


def test_before_any_submission_a_service_project_names_dev_then_its_tests(service):
    assert attempt_status(service, None, None).next_step == SERVICE_NEXT


def test_the_service_next_step_takes_no_flag_of_a_native_run():
    assert "--" not in SERVICE_NEXT


def test_after_a_submission_a_service_project_names_its_unlocked_level(service):
    attempt = service.progress.active_attempt()
    assert attempt is not None
    level = LevelTally(level=1, visible_total=4, visible_passed=2, hidden_total=0, hidden_passed=0)
    service.progress.add_submission(
        SubmissionRecord(
            attempt_id=attempt.id,
            submitted_at=NOW + timedelta(minutes=5),
            code_hash="abc",
            graded_up_to=1,
            every_level=True,
            levels=(level,),
            tally=Tally(total=level.total, passed=level.passed),
            duration_ms=300,
        )
    )
    assert attempt_status(service, None, None).next_step == "cstudy submit once level 1 passes"
