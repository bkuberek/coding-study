"""TypeScript adapters, owned by the TypeScript stream (T3b): the stub generator and the runner."""

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.typescript.runner import PnpmTypeChecker, TypeScriptRunner
from coding_study.adapters.languages.typescript.stub_generator import TypeScriptStubGenerator
from coding_study.application.ports import LanguageRunner, StubGenerator


def create_stub_generator() -> StubGenerator:
    return TypeScriptStubGenerator()


def create_runner(context: LanguageContext) -> LanguageRunner:
    return TypeScriptRunner(context.workspace, context.runners, PnpmTypeChecker())
