import pytest

from coding_study.adapters.conformance_fixtures import conformance_repository
from coding_study.domain.language_limits import CYCLIC_LIST, LIST_IDENTITY, language_limits
from coding_study.domain.problem import Language
from tests.helpers import REPOSITORY_ROOT

FIXTURES = conformance_repository(REPOSITORY_ROOT)


def limits(slug: str, language: Language = Language.RUST) -> tuple[str, ...]:
    problem = FIXTURES.load(slug)
    return language_limits(problem.meta.signature, problem.cases, language)


def test_a_cyclic_list_input_is_beyond_rust():
    assert limits("conformance-cyclic-list") == (CYCLIC_LIST,)


def test_ref_of_and_as_index_into_a_list_are_beyond_rust():
    assert limits("conformance-ref-of-list") == (LIST_IDENTITY,)


@pytest.mark.parametrize(
    "slug", ["conformance-ref-of-tree", "conformance-no-alias", "conformance-types"]
)
def test_tree_identity_and_list_aliasing_are_fine(slug):
    assert limits(slug) == ()


@pytest.mark.parametrize("language", [Language.GO, Language.PYTHON, Language.JAVA])
def test_other_languages_have_no_limits(language):
    assert limits("conformance-cyclic-list", language) == ()
