from pathlib import Path

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.registry import LANGUAGES
from coding_study.adapters.languages.typescript.runner import TypeScriptRunner
from coding_study.adapters.languages.typescript.stub_generator import TypeScriptStubGenerator
from coding_study.domain.problem import Language


def test_registry_creates_the_typescript_stub_generator():
    assert isinstance(LANGUAGES.stub_generator(Language.TYPESCRIPT), TypeScriptStubGenerator)


def test_registry_creates_the_typescript_runner():
    runner = LANGUAGES.runner(
        Language.TYPESCRIPT, LanguageContext(Path("/ws"), Path("/content/runners"))
    )
    assert isinstance(runner, TypeScriptRunner)
