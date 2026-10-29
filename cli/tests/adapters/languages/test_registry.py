from pathlib import Path
from typing import cast

import pytest

from coding_study.adapters.languages.context import LanguageContext
from coding_study.adapters.languages.registry import (
    LANGUAGES,
    LanguageFactories,
    LanguageRegistry,
)
from coding_study.application.ports import BuildScope, PrepareResult, ProgressNotice
from coding_study.domain.errors import LanguageNotSetUpError
from coding_study.domain.problem import Language, ProblemMeta

CONTEXT = LanguageContext(workspace=Path("/ws"), runners=Path("/content/runners"))


class FakeStubGenerator:
    def generate(self, meta: ProblemMeta) -> str:
        return meta.slug


class FakeRunner:
    def __init__(self, context: LanguageContext) -> None:
        self.context = context

    def prepare(self, scope: BuildScope, notify: ProgressNotice) -> PrepareResult:
        raise NotImplementedError


def fake_registry() -> LanguageRegistry:
    return LanguageRegistry({Language.PYTHON: LanguageFactories(FakeStubGenerator, FakeRunner)})


def test_every_language_is_registered():
    assert LANGUAGES.languages == frozenset(Language)


def test_a_language_without_an_adapter_has_no_stub_generator_yet():
    with pytest.raises(LanguageNotSetUpError, match="kotlin stub generator is not set up yet"):
        fake_registry().stub_generator(Language.KOTLIN)


def test_creates_the_registered_stub_generator():
    assert isinstance(fake_registry().stub_generator(Language.PYTHON), FakeStubGenerator)


def test_passes_the_context_to_the_runner_factory():
    runner = fake_registry().runner(Language.PYTHON, CONTEXT)
    assert cast(FakeRunner, runner).context == CONTEXT


def test_unregistered_language_is_not_set_up():
    with pytest.raises(LanguageNotSetUpError, match="kotlin runner is not set up yet"):
        fake_registry().runner(Language.KOTLIN, CONTEXT)
