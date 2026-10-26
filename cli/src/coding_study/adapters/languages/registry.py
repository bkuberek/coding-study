"""Language id to adapter factories. Each language package owns its factories; adding a language
is the only reason to edit this file."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from coding_study.adapters.languages import jvm, python, typescript
from coding_study.adapters.languages.context import LanguageContext
from coding_study.application.ports import LanguageRunner, StubGenerator
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.problem import Language

STUB_GENERATOR = "stub generator"
RUNNER = "runner"


@dataclass(frozen=True, slots=True)
class LanguageFactories:
    stub_generator: Callable[[], StubGenerator]
    runner: Callable[[LanguageContext], LanguageRunner]


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

    def _for(self, language: Language, component: str) -> LanguageFactories:
        factories = self._factories.get(language)
        if factories is None:
            raise LanguageNotSetUpError(language, component)
        return factories


LANGUAGES = LanguageRegistry(
    {
        Language.PYTHON: LanguageFactories(python.create_stub_generator, python.create_runner),
        Language.TYPESCRIPT: LanguageFactories(
            typescript.create_stub_generator, typescript.create_runner
        ),
        Language.JAVA: LanguageFactories(jvm.create_java_stub_generator, jvm.create_java_runner),
        Language.KOTLIN: LanguageFactories(
            jvm.create_kotlin_stub_generator, jvm.create_kotlin_runner
        ),
    }
)
