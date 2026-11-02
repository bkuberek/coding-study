"""The project stress fixtures 9037 to 9042 through every real runner
(docs/specs/runners.md#conformance-suite): each language's reference passes its stress case in 10
of 10 runs and its broken overlay fails it in at least 9.

Marked `slow`: Gradle, Node, the workspace venv and the Go and Rust toolchains, as `cstudy verify
--conformance` runs them, in the session's practice workspace over this checkout's content. Each
fixture lists one language.
"""

import pytest

from coding_study.adapters.conformance_fixtures import load_conformance_suite
from coding_study.adapters.environment_factory import conformance_environment, load_environment
from coding_study.application.verify_conformance import ConformanceRequest, verify_conformance
from coding_study.domain.problem import Language
from tests.helpers import REPOSITORY_ROOT
from tests.toolchains import jvm_marked

pytestmark = pytest.mark.slow

PROJECT_STRESS_FIXTURES = tuple(
    f"conformance-project-stress-{language}"
    for language in ("python", "typescript", "java", "kotlin", "go", "rust")
)


@pytest.mark.parametrize("language", jvm_marked(Language))
def test_every_runner_meets_the_project_stress_expectations(language, practice_workspace):
    environ = {"CSTUDY_CONTENT": str(REPOSITORY_ROOT), "CSTUDY_WORKSPACE": str(practice_workspace)}
    environment = load_environment(practice_workspace, environ, practice_workspace)
    request = ConformanceRequest(PROJECT_STRESS_FIXTURES, language)
    results = verify_conformance(
        conformance_environment(environment),
        load_conformance_suite(REPOSITORY_ROOT),
        request,
        lambda _line: None,
    )
    ran = [result for result in results if result.languages]
    failures = [
        f"{result.directory}: {failure}"
        for result in results
        for language_result in result.languages
        for approach in language_result.approaches
        for failure in approach.failures
    ] + [f"{result.directory}: {error}" for result in results for error in result.errors]
    assert (len(ran), failures) == (1, [])
