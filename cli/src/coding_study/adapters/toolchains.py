from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.registry import LanguageRegistry
from coding_study.adapters.runner_runtime import RunnerRuntime
from coding_study.application.ports import LanguageRunner, StubGenerator, Toolchains
from coding_study.domain.problem import Language


class RegistryToolchains:
    """`Toolchains` from the language registry, bound to one workspace."""

    def __init__(self, registry: LanguageRegistry, context: LanguageContext) -> None:
        self._registry = registry
        self._context = context

    def stub_generator(self, language: Language) -> StubGenerator:
        return self._registry.stub_generator(language)

    def runner(self, language: Language) -> LanguageRunner:
        return self._registry.runner(language, self._context)


class RuntimeToolchains:
    """Brings the workspace's runner runtime in step with the content before the first runner of
    a command is handed out, so an upgraded `cstudy` or an edited checkout never runs stale runners
    (docs/specs/installation-and-workspaces.md#runner-runtime)."""

    def __init__(self, toolchains: Toolchains, runtime: RunnerRuntime) -> None:
        self._toolchains = toolchains
        self._runtime = runtime
        self._current = False

    def stub_generator(self, language: Language) -> StubGenerator:
        return self._toolchains.stub_generator(language)

    def runner(self, language: Language) -> LanguageRunner:
        if not self._current:
            self._runtime.ensure()
            self._current = True
        return self._toolchains.runner(language)
