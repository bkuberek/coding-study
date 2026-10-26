"""Python adapters, owned by the Python stream (T3a): the stub generator and the runner.

The registry imports both factories by name; keep their names and signatures.
"""

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.python.runner import PythonRunner
from coding_study.adapters.languages.python.stub_generator import PythonStubGenerator
from coding_study.application.ports import LanguageRunner, StubGenerator


def create_stub_generator() -> StubGenerator:
    return PythonStubGenerator()


def create_runner(context: LanguageContext) -> LanguageRunner:
    return PythonRunner(context.workspace)
