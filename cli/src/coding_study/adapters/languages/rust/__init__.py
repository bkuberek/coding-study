"""Rust adapters: the stub generator and the runner (docs/decisions/0012-go-and-rust.md)."""

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.rust.runner import RustRunner
from coding_study.adapters.languages.rust.stub_generator import RustStubGenerator
from coding_study.adapters.languages.rust.toolchain import SubprocessCargo
from coding_study.application.ports import LanguageRunner, StubGenerator


def create_stub_generator() -> StubGenerator:
    return RustStubGenerator()


def create_runner(context: LanguageContext) -> LanguageRunner:
    return RustRunner(context, SubprocessCargo())
