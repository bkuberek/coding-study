import pytest
import yaml

from coding_study.adapters.schema_validation import META_SCHEMA_FILE, SchemaValidator
from coding_study.domain.problem import CORE_LANGUAGES, Language, ProblemKind
from coding_study.domain.signature import ClassSignature, Signature
from tests.helpers import MAPPING_TABLE_TYPES, REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.stub_contract import (
    GOLDEN_ROOT,
    STUB_CASES,
    UPDATE_VARIABLE,
    GoldenFiles,
    stub_case_sources,
)

TEXT = "def two_sum():\n    raise NotImplementedError\n"


def declared_types(signature: Signature) -> set[str]:
    if isinstance(signature, ClassSignature):
        methods = signature.methods
        params = [*signature.constructor_params, *(p for m in methods for p in m.params)]
        returns = [method.returns for method in methods]
    else:
        params, returns = list(signature.params), [signature.returns]
    return {str(param.type) for param in params} | {str(result.type) for result in returns}


def test_cases_include_the_spec_examples():
    assert {"two-sum", "lru-cache"} <= {case.name for case in STUB_CASES}


PROBLEM_FORMAT = REPOSITORY_ROOT / "docs" / "specs" / "problem-format.md"
SPEC_STUB_LABELS = {
    "python": "# python/practice/{snake}.py",
    "typescript": "// typescript/practice/{slug}.ts",
    "java": "// jvm/java/src/main/java/practice/{snake}/{class_name}.java",
    "kotlin": "// jvm/kotlin/src/main/kotlin/practice/{snake}/{class_name}.kt",
}


@pytest.mark.parametrize("language", CORE_LANGUAGES)
@pytest.mark.parametrize(
    ("slug", "class_name"), [("two-sum", "Solution"), ("lru-cache", "LRUCache")]
)
def test_problem_format_worked_examples_print_the_golden_stubs(slug, class_name, language):
    golden = GoldenFiles(GOLDEN_ROOT).path(language, slug).read_text()
    label = SPEC_STUB_LABELS[language].format(
        slug=slug, snake=slug.replace("-", "_"), class_name=class_name
    )
    assert f"{label}\n{golden}```" in PROBLEM_FORMAT.read_text()


@pytest.mark.parametrize("name", sorted(stub_case_sources()))
def test_every_case_is_a_schema_valid_meta(name):
    validator = SchemaValidator.from_file(SCHEMAS_DIRECTORY / META_SCHEMA_FILE)
    document = yaml.safe_load(stub_case_sources()[name].read_text())
    assert validator.violations(document, name) == []


def test_cases_cover_every_kind():
    assert {case.meta.kind for case in STUB_CASES} == set(ProblemKind)


def test_cases_cover_every_type_in_the_mapping_table_and_void():
    covered = set[str]().union(*(declared_types(case.meta.signature) for case in STUB_CASES))
    assert {*MAPPING_TABLE_TYPES, "void"} <= covered


def test_golden_path_is_language_then_case(tmp_path):
    path = GoldenFiles(tmp_path).path(Language.KOTLIN, "two-sum")
    assert path == tmp_path / "kotlin" / "two-sum.kt"


def test_matching_golden_passes(tmp_path):
    goldens = GoldenFiles(tmp_path)
    goldens.write(Language.PYTHON, "two-sum", TEXT)
    goldens.assert_matches(Language.PYTHON, "two-sum", TEXT)


def test_differing_golden_fails(tmp_path):
    goldens = GoldenFiles(tmp_path)
    goldens.write(Language.PYTHON, "two-sum", TEXT)
    with pytest.raises(AssertionError):
        goldens.assert_matches(Language.PYTHON, "two-sum", TEXT + "\n")


def test_missing_golden_explains_how_to_create_it(tmp_path):
    with pytest.raises(pytest.fail.Exception, match=UPDATE_VARIABLE):
        GoldenFiles(tmp_path).assert_matches(Language.JAVA, "two-sum", TEXT)


def test_write_creates_the_language_directory(tmp_path):
    GoldenFiles(tmp_path).write(Language.TYPESCRIPT, "two-sum", TEXT)
    assert (tmp_path / "typescript" / "two-sum.ts").read_text() == TEXT


def test_cases_include_the_conformance_type_fixture():
    assert "conformance-types" in stub_case_sources()
