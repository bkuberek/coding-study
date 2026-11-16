"""The problems a mock interview picks from, and what the learner profile left of them
(docs/specs/cli.md#cstudy-mock)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.mock_interview import MockRequest, mock_scope, start_mock
from coding_study.application.ports import StubGenerator
from coding_study.domain.errors import UsageError
from coding_study.domain.labels import LabelFilter
from coding_study.domain.problem import Language
from coding_study.domain.profile import NO_PROFILE_EFFECT, Dimension, Profile, Widening
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIRST_CATALOG, copy_catalog_problems

SLICE = (*FIRST_CATALOG, "group-anagrams", "first-missing-positive")
BACKEND = Profile(domains=("backend",))


@pytest.fixture
def environment(tmp_path: Path, tmp_path_factory: pytest.TempPathFactory):
    problems = copy_catalog_problems(tmp_path_factory.mktemp("catalog"), SLICE)
    generators: dict[Language, StubGenerator] = {
        language: FakeStubGenerator() for language in Language
    }
    environment = make_environment(
        repository_root(tmp_path, problems), toolchains=FakeToolchains(stub_generators=generators)
    )
    meta = environment.root / "problems/lru-cache/meta.yaml"
    meta.write_text(meta.read_text().replace("domains: [algorithms]", "domains: [backend]"))
    return environment


def test_the_scope_counts_the_new_medium_and_hard_problems_the_profile_left(environment):
    effect = mock_scope(environment, MockRequest(profile=BACKEND))
    assert (effect.shown, effect.total, effect.hidden) == (1, 3, 2)
    assert effect.narrowed.domains == ("backend",)


def test_the_scope_counts_nothing_while_the_profile_narrows_nothing(environment):
    assert mock_scope(environment, MockRequest()) == NO_PROFILE_EFFECT
    assert mock_scope(environment, MockRequest(profile=Profile())) == NO_PROFILE_EFFECT


def test_the_scope_counts_nothing_where_the_run_widened_every_narrowed_dimension(environment):
    widened = Widening(frozenset({Dimension.DOMAINS}))
    assert mock_scope(environment, MockRequest(profile=BACKEND, widening=widened)) == (
        NO_PROFILE_EFFECT
    )


def test_the_scope_leaves_out_the_problems_with_an_attempt(environment):
    start_mock(environment, MockRequest(count=1))
    effect = mock_scope(environment, MockRequest(profile=BACKEND))
    assert (effect.shown, effect.total) == (1, 2)


def test_the_scope_refuses_a_language_outside_the_workspace(environment):
    narrowed = replace(environment, workspace_languages=(Language.PYTHON,))
    with pytest.raises(UsageError, match="cstudy lang add kotlin"):
        mock_scope(narrowed, MockRequest(language=Language.KOTLIN))


def test_the_scope_starts_nothing(environment):
    mock_scope(environment, MockRequest(profile=BACKEND))
    assert environment.progress.attempts_in_progress() == ()


def test_a_session_names_the_profile_when_it_left_nothing(environment):
    session = start_mock(environment, MockRequest(profile=Profile(domains=("security",))))
    assert (session.problems, session.profile_left_nothing) == ((), True)
    assert (session.profile.shown, session.profile.total) == (0, 3)


def test_a_session_does_not_when_the_scope_holds_nothing_without_the_profile(environment):
    request = MockRequest(tracks=(), profile=BACKEND, labels=LabelFilter(domain="security"))
    widened = replace(request, widening=Widening(frozenset({Dimension.DOMAINS})))
    session = start_mock(environment, widened)
    assert (session.problems, session.profile_left_nothing) == ((), False)


def test_a_session_starts_each_problem_in_its_language(environment):
    environment = replace(environment, workspace_languages=(Language.PYTHON, Language.GO))
    meta = environment.root / "problems/group-anagrams/meta.yaml"
    meta.write_text(
        meta.read_text().replace("estimate_minutes:", "languages: [go]\nestimate_minutes:")
    )
    session = start_mock(environment, MockRequest())
    assert {problem.pick.candidate.slug: problem.language for problem in session.problems} == {
        "group-anagrams": Language.GO,
        "lru-cache": Language.PYTHON,
    }
    assert session.language is Language.PYTHON
