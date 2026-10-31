"""The TypeScript project fixtures 9023 and 9025 through the conformance suite.

Marked `slow`: the real TypeScript runner grades each reference build and hosts `node:test` for the
suite fixture (docs/specs/runners.md#conformance-suite). The first tests stand in for the generated
level test files, one empty passing test per visible case under the case's id, so they need only
Node; the last runs `cstudy verify --conformance` with the TypeScript test generator.
"""

import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.conformance_fixtures import load_conformance_suite
from coding_study.adapters.environment_factory import conformance_environment
from coding_study.adapters.languages.registry import LANGUAGES
from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker, TypeScriptRunner
from coding_study.adapters.subprocess_runner import SubprocessRunner
from coding_study.application.environment import Environment
from coding_study.application.verify_conformance import (
    ConformanceRequest,
    FixtureVerification,
    verify_conformance,
)
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.problem import Language
from coding_study.domain.project_tests import LevelTests
from coding_study.entrypoints import cli
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeToolchains, make_environment
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed"),
]

CONFORMANCE = REPOSITORY_ROOT / "runners" / "conformance"
FIXTURES = ("9023-conformance-project-typescript", "9025-conformance-suite-node-test")
GRADING, SUITE = "conformance-project-typescript", "conformance-suite-node-test"


class EmptyLevelTests:
    """Writes one passing `node:test` test per visible case, named after the case."""

    def generate(self, tests: LevelTests) -> str:
        cases = "".join(f'\ntest("{test.case_id}", () => {{}});\n' for test in tests.tests)
        return f'import {{ test }} from "node:test";\n{cases}'


def has_typescript_test_generator() -> bool:
    try:
        LANGUAGES.project_test_generator(Language.TYPESCRIPT)
    except LanguageNotSetUpError:
        return False
    return True


@pytest.fixture(scope="module")
def environment(tmp_path_factory: pytest.TempPathFactory) -> Environment:
    root = tmp_path_factory.mktemp("content")
    shutil.copytree(SCHEMAS_DIRECTORY, root / "schemas")
    (root / "problems").mkdir()
    fixtures = root / "runners" / "conformance"
    for directory in FIXTURES:
        shutil.copytree(CONFORMANCE / directory, fixtures / directory)
    expectations = json.loads((CONFORMANCE / "expectations.json").read_text())
    expectations["expectations"] = [
        entry for entry in expectations["expectations"] if entry["problem"] in (GRADING, SUITE)
    ]
    (fixtures / "expectations.json").write_text(json.dumps(expectations))
    runner = TypeScriptRunner(root, REPOSITORY_ROOT / "runners", PnpmTypeChecker())
    toolchains = FakeToolchains(
        runners={Language.TYPESCRIPT: runner},
        project_test_generators={Language.TYPESCRIPT: EmptyLevelTests()},
    )
    process = SubprocessRunner(root / ".cs" / "runs")
    return conformance_environment(
        make_environment(root, toolchains=toolchains, runner_process=process)
    )


def conformance(environment: Environment, slug: str) -> FixtureVerification:
    request = ConformanceRequest((slug,), Language.TYPESCRIPT)
    suite = load_conformance_suite(environment.root)
    [result] = verify_conformance(environment, suite, request, lambda _: None)
    return result


def failures(result: FixtureVerification) -> tuple[str, ...]:
    return (
        *result.errors,
        *(problem for language in result.languages for problem in language.problems),
        *(
            failure
            for language in result.languages
            for approach in language.approaches
            for failure in approach.failures
        ),
    )


def test_the_typescript_runner_imports_between_the_files_of_a_project(environment):
    assert failures(conformance(environment, GRADING)) == ()


def test_the_typescript_runner_reports_every_status_of_a_node_test_suite(environment):
    assert failures(conformance(environment, SUITE)) == ()


NO_GENERATOR = "the TypeScript project test generator is not set up"


@pytest.mark.skipif(not has_typescript_test_generator(), reason=NO_GENERATOR)
def test_the_typescript_runner_meets_the_project_expectations(
    practice_workspace: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    root = workspace_like(practice_workspace, tmp_path / "ws")
    monkeypatch.setenv("CSTUDY_CONTENT", str(REPOSITORY_ROOT))
    monkeypatch.setenv("CSTUDY_WORKSPACE", str(root))
    monkeypatch.setenv("CSTUDY_CONFIG", str(tmp_path / "absent-config.toml"))
    arguments = ["verify", "--conformance", "--lang", "typescript", GRADING, SUITE]
    result = CliRunner().invoke(cli.app, arguments)
    assert (result.exit_code, result.output.splitlines()[:2]) == (
        ExitCode.SUCCESS,
        [
            "9023-conformance-project-typescript  ts ok",
            "9025-conformance-suite-node-test     ts ok",
        ],
    )
