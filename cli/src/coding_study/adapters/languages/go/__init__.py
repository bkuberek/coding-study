"""Go adapters: the stub generator and the runner (docs/decisions/0012-go-and-rust.md)."""

from coding_study.adapters.languages.go.stub_generator import GoStubGenerator
from coding_study.application.ports import StubGenerator


def create_stub_generator() -> StubGenerator:
    return GoStubGenerator()
