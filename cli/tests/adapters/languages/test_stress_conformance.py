"""The stress conformance fixtures 9014 to 9019 through every real runner (Phase 5).

Marked `slow`: Gradle, Node and the workspace venv, as `cstudy verify --conformance` runs them, in
the session's practice workspace over this checkout's content.
"""

import pytest

from coding_study.adapters.conformance_fixtures import load_conformance_suite
from coding_study.adapters.environment_factory import conformance_environment, load_environment
from coding_study.application.verify_conformance import ConformanceRequest, verify_conformance
from coding_study.domain.problem import Language
from tests.helpers import REPOSITORY_ROOT

pytestmark = pytest.mark.slow

STRESS_FIXTURES = (
    "conformance-stress-counter",
    "conformance-stress-stall",
    "conformance-stress-worker-error",
    "conformance-stress-sections",
    "conformance-stress-async-determinism",
    "conformance-stress-leak",
)


@pytest.mark.parametrize("language", list(Language))
def test_every_runner_meets_the_stress_expectations(language, practice_workspace):
    environ = {"CSTUDY_CONTENT": str(REPOSITORY_ROOT), "CSTUDY_WORKSPACE": str(practice_workspace)}
    environment = load_environment(practice_workspace, environ, practice_workspace)
    request = ConformanceRequest(STRESS_FIXTURES, language)
    results = verify_conformance(
        conformance_environment(environment),
        load_conformance_suite(REPOSITORY_ROOT),
        request,
        lambda _line: None,
    )
    failures = [
        f"{result.directory}: {failure}"
        for result in results
        for language_result in result.languages
        for approach in language_result.approaches
        for failure in approach.failures
    ] + [f"{result.directory}: {error}" for result in results for error in result.errors]
    assert failures == []
