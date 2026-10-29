"""Go adapters: the stub generator and the runner (docs/decisions/0012-go-and-rust.md)."""

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.go.runner import GoRunner
from coding_study.adapters.languages.go.stub_generator import GoStubGenerator
from coding_study.adapters.languages.go.toolchain import SubprocessGo
from coding_study.application.ports import LanguageRunner, StubGenerator


def create_stub_generator() -> StubGenerator:
    return GoStubGenerator()


def create_runner(context: LanguageContext) -> LanguageRunner:
    return GoRunner(context, SubprocessGo())
