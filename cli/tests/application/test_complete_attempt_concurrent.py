"""`cstudy done` on concurrent problems: a full run stores one verdict per sequential case plus
one per (stress case, variant), so the JVM's two thread variants make a full run larger than the
case list (docs/specs/cli.md#cstudy-done, problem-format.md#concurrent-problems)."""

import pytest

from coding_study.application.complete_attempt import DoneRequest, complete_attempt
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptStatus, Rating, RunRecord
from coding_study.domain.errors import UsageError
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import CONCURRENCY_PROBLEMS

SEQUENTIAL_CASES = 6
STRESS_CASES = 2


@pytest.fixture
def repository(tmp_path):
    return repository_root(tmp_path, CONCURRENCY_PROBLEMS)


def stub_generators() -> dict[Language, StubGenerator]:
    return {language: FakeStubGenerator() for language in Language}


def attempt_in(repository, language: Language):
    environment = make_environment(
        repository, toolchains=FakeToolchains(stub_generators=stub_generators())
    )
    start_attempt(environment, StartRequest("bounded-blocking-queue", language))
    return environment


def record_run(environment, total: int, passed: int | None = None) -> None:
    attempt = environment.progress.active_attempt()
    passed = total if passed is None else passed
    tally = Tally(total=total, passed=passed, failed=total - passed)
    environment.progress.add_test_run(RunRecord(attempt.id, NOW, "hash", tally, 10))


def done(environment, **fields):
    return complete_attempt(environment, DoneRequest(**fields))


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_a_full_jvm_run_counts_a_verdict_per_thread_variant(repository, language):
    environment = attempt_in(repository, language)
    record_run(environment, SEQUENTIAL_CASES + STRESS_CASES * 2)
    assert done(environment, rating=Rating.OK).attempt.status is AttemptStatus.PASSED


@pytest.mark.parametrize("language", [Language.PYTHON, Language.TYPESCRIPT])
def test_a_full_single_variant_run_counts_one_verdict_per_stress_case(repository, language):
    environment = attempt_in(repository, language)
    record_run(environment, SEQUENTIAL_CASES + STRESS_CASES)
    assert done(environment, rating=Rating.OK).attempt.status is AttemptStatus.PASSED


def test_a_jvm_run_of_one_variant_is_not_a_full_run(repository):
    environment = attempt_in(repository, Language.JAVA)
    record_run(environment, SEQUENTIAL_CASES + STRESS_CASES)
    with pytest.raises(UsageError, match="did not pass every case"):
        done(environment, rating=Rating.OK)


def test_a_partial_jvm_run_is_not_a_full_run(repository):
    environment = attempt_in(repository, Language.JAVA)
    record_run(environment, total=1)
    with pytest.raises(UsageError, match="did not pass every case"):
        done(environment, rating=Rating.OK)


def test_a_full_jvm_run_with_a_failure_is_not_a_pass(repository):
    environment = attempt_in(repository, Language.JAVA)
    record_run(environment, SEQUENTIAL_CASES + STRESS_CASES * 2, passed=9)
    with pytest.raises(UsageError, match="did not pass every case"):
        done(environment, rating=Rating.OK)
