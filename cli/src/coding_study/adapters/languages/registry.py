"""Language id to adapter factories. Each language package owns its factories; adding a language
is the only reason to edit this file."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from coding_study.adapters.languages import go, jvm, python, rust, typescript
from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go.test_generator import GoTestGenerator
from coding_study.adapters.languages.jvm.test_generators import (
    JavaTestGenerator,
    KotlinTestGenerator,
)
from coding_study.adapters.languages.python.test_generator import PythonTestGenerator
from coding_study.adapters.languages.rust.test_generator import RustTestGenerator
from coding_study.adapters.languages.typescript.test_generator import TypeScriptTestGenerator
from coding_study.application.ports import LanguageRunner, ProjectTestGenerator, StubGenerator
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.problem import Language

STUB_GENERATOR = "stub generator"
RUNNER = "runner"
PROJECT_TEST_GENERATOR = "project test generator"


@dataclass(frozen=True, slots=True)
class LanguageFactories:
    stub_generator: Callable[[], StubGenerator]
    runner: Callable[[LanguageContext], LanguageRunner]
    project_test_generator: Callable[[], ProjectTestGenerator] | None = None
    """None: the language has no project problems yet, or no generated tests for them."""


class LanguageRegistry:
    def __init__(self, factories: Mapping[Language, LanguageFactories]) -> None:
        self._factories = dict(factories)

    @property
    def languages(self) -> frozenset[Language]:
        return frozenset(self._factories)

    def stub_generator(self, language: Language) -> StubGenerator:
        """Raises LanguageNotSetUpError until the language's stream implements it."""
        return self._for(language, STUB_GENERATOR).stub_generator()

    def runner(self, language: Language, context: LanguageContext) -> LanguageRunner:
        """Raises LanguageNotSetUpError until the language's stream implements it."""
        return self._for(language, RUNNER).runner(context)

    def project_test_generator(self, language: Language) -> ProjectTestGenerator:
        """Raises LanguageNotSetUpError for a language whose project tests are not generated
        yet (docs/specs/problem-format.md#generated-test-files)."""
        factory = self._for(language, PROJECT_TEST_GENERATOR).project_test_generator
        if factory is None:
            raise LanguageNotSetUpError(language, PROJECT_TEST_GENERATOR)
        return factory()

    def _for(self, language: Language, component: str) -> LanguageFactories:
        factories = self._factories.get(language)
        if factories is None:
            raise LanguageNotSetUpError(language, component)
        return factories


LANGUAGES = LanguageRegistry(
    {
        Language.PYTHON: LanguageFactories(
            python.create_stub_generator, python.create_runner, PythonTestGenerator
        ),
        Language.TYPESCRIPT: LanguageFactories(
            typescript.create_stub_generator, typescript.create_runner, TypeScriptTestGenerator
        ),
        Language.JAVA: LanguageFactories(
            jvm.create_java_stub_generator, jvm.create_java_runner, JavaTestGenerator
        ),
        Language.KOTLIN: LanguageFactories(
            jvm.create_kotlin_stub_generator, jvm.create_kotlin_runner, KotlinTestGenerator
        ),
        Language.GO: LanguageFactories(go.create_stub_generator, go.create_runner, GoTestGenerator),
        Language.RUST: LanguageFactories(
            rust.create_stub_generator, rust.create_runner, RustTestGenerator
        ),
    }
)
