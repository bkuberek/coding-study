from pathlib import Path

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.adapters.languages.registry import LANGUAGES
from coding_study.adapters.runner_runtime import RunnerRuntime
from coding_study.adapters.toolchains import RegistryToolchains, RuntimeToolchains
from coding_study.application.ports import Prepared, RunnerLaunch
from coding_study.domain.problem import Language
from tests.fakes import FakeLanguageRunner, FakeStubGenerator, FakeToolchains

GENERATOR = PythonTestGenerator()


class CountingRuntime(RunnerRuntime):
    def __init__(self) -> None:
        super().__init__(Path("/content/runners"), Path("/ws"))
        self.ensured = 0

    def ensure(self) -> Path:
        self.ensured += 1
        return self.directory


@pytest.fixture
def runtime() -> CountingRuntime:
    return CountingRuntime()


@pytest.fixture
def toolchains(runtime: CountingRuntime) -> RuntimeToolchains:
    runner = FakeLanguageRunner(Prepared(RunnerLaunch(("python",), Path("/"), 1000)))
    fakes = FakeToolchains(
        {Language.PYTHON: runner},
        {Language.PYTHON: FakeStubGenerator()},
        {Language.PYTHON: GENERATOR},
    )
    return RuntimeToolchains(fakes, runtime)


def test_the_first_runner_brings_the_runtime_up_to_date(toolchains, runtime):
    toolchains.runner(Language.PYTHON)
    assert runtime.ensured == 1


def test_later_runners_of_the_same_command_do_not_check_again(toolchains, runtime):
    toolchains.runner(Language.PYTHON)
    toolchains.runner(Language.PYTHON)
    assert runtime.ensured == 1


def test_stub_generators_need_no_runtime(toolchains, runtime):
    toolchains.stub_generator(Language.PYTHON)
    assert runtime.ensured == 0


def test_project_test_generators_come_from_the_wrapped_toolchains(toolchains):
    assert toolchains.project_test_generator(Language.PYTHON) is GENERATOR


def test_project_test_generators_need_no_runtime(toolchains, runtime):
    toolchains.project_test_generator(Language.PYTHON)
    assert runtime.ensured == 0


def test_the_registry_toolchains_generate_python_project_tests():
    registry = RegistryToolchains(LANGUAGES, LanguageContext(Path("/ws"), Path("/runners")))
    assert isinstance(registry.project_test_generator(Language.PYTHON), PythonTestGenerator)
