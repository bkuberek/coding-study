"""The shared contract every language's StubGenerator tests reuse (docs/specs/runners.md).

A language stream's test module looks like this:

    from tests.stub_contract import StubCase, check_stub, stub_cases

    @stub_cases
    def test_python_stub(stub_case: StubCase) -> None:
        text = create_stub_generator().generate(stub_case.meta)
        check_stub(Language.PYTHON, stub_case, text)

Every generator must reproduce its golden file for every case in STUB_CASES. Goldens live in
tests/golden/stubs/<language>/<case>.<ext>. Run the tests with CSTUDY_UPDATE_GOLDENS=1 to write
them, then review each one: the two-sum and lru-cache goldens must equal the stubs printed in
docs/specs/problem-format.md (worked examples), and every golden must compile or import as is.

The cases are meta.yaml documents in tests/golden/stubs/signatures/ plus the conformance type
fixtures, so together they cover every DSL type, void returns, modifiers, all class kinds,
support-class imports and the snake_case naming rules.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from coding_study.adapters.problem_documents import meta_from_document
from coding_study.domain.layout import SOURCE_EXTENSIONS
from coding_study.domain.problem import Language, ProblemMeta
from tests.helpers import REPOSITORY_ROOT

GOLDEN_ROOT = Path(__file__).resolve().parent / "golden" / "stubs"
SIGNATURES_DIRECTORY = GOLDEN_ROOT / "signatures"
CONFORMANCE_DIRECTORY = REPOSITORY_ROOT / "runners" / "conformance"
CONFORMANCE_TYPE_FIXTURES = {
    "conformance-types": CONFORMANCE_DIRECTORY / "9001-conformance-types" / "meta.yaml",
    "conformance-decimal-date-types": (
        CONFORMANCE_DIRECTORY / "9021-conformance-decimal-date-types" / "meta.yaml"
    ),
}
UPDATE_VARIABLE = "CSTUDY_UPDATE_GOLDENS"


@dataclass(frozen=True, slots=True)
class StubCase:
    name: str
    """The golden file name without extension."""
    meta: ProblemMeta


class GoldenFiles:
    def __init__(self, root: Path) -> None:
        self._root = root

    def path(self, language: Language, case_name: str) -> Path:
        return self._root / language / f"{case_name}.{SOURCE_EXTENSIONS[language]}"

    def write(self, language: Language, case_name: str, text: str) -> None:
        path = self.path(language, case_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def assert_matches(self, language: Language, case_name: str, text: str) -> None:
        path = self.path(language, case_name)
        if not path.exists():
            pytest.fail(f"missing golden {path}: run with {UPDATE_VARIABLE}=1, then review it")
        assert text == path.read_text(encoding="utf-8")


def stub_case_sources() -> dict[str, Path]:
    """Case name to the meta.yaml document that defines it."""
    sources = {path.stem: path for path in sorted(SIGNATURES_DIRECTORY.glob("*.yaml"))}
    return {**sources, **CONFORMANCE_TYPE_FIXTURES}


def load_stub_cases() -> tuple[StubCase, ...]:
    return tuple(StubCase(name, _meta(path)) for name, path in stub_case_sources().items())


def check_stub(language: Language, case: StubCase, text: str) -> None:
    """Assert `text` equals the case's golden; with CSTUDY_UPDATE_GOLDENS=1, rewrite the golden."""
    if os.environ.get(UPDATE_VARIABLE) == "1":
        GOLDENS.write(language, case.name, text)
        return
    GOLDENS.assert_matches(language, case.name, text)


def _meta(path: Path) -> ProblemMeta:
    return meta_from_document(yaml.safe_load(path.read_text(encoding="utf-8")), path.name)


GOLDENS = GoldenFiles(GOLDEN_ROOT)
STUB_CASES = load_stub_cases()
stub_cases = pytest.mark.parametrize("stub_case", STUB_CASES, ids=lambda case: case.name)
