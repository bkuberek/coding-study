import pytest

from coding_study.domain.naming import (
    ClassNames,
    FunctionNames,
    ReservedNameConflict,
    is_reserved,
    member_name,
    reserved_name_conflicts,
    shadowed_python_builtins,
    shadowed_python_imports,
    snake_case,
    symbol_names,
)
from coding_study.domain.problem import Language
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import Scalar, ScalarType, VoidType

INT = ScalarType(Scalar.INT)


def function(name: str, *param_names: str) -> FunctionSignature:
    params = tuple(Param(param_name, INT) for param_name in param_names)
    return FunctionSignature(name, params, Returns(INT))


def design_class(name: str, *method_names: str) -> ClassSignature:
    methods = tuple(Method(method, (), Returns(VoidType())) for method in method_names)
    return ClassSignature(name, (Param("capacity", INT),), methods)


@pytest.mark.parametrize(
    ("canonical", "converted"),
    [
        ("twoSum", "two_sum"),
        ("nums", "nums"),
        ("maxValue", "max_value"),
        ("getRandom", "get_random"),
        ("getHTTPCode", "get_http_code"),
        ("userID", "user_id"),
        ("echoUTF8Text", "echo_utf8_text"),
        ("sum2Values", "sum2_values"),
        ("a1B", "a1_b"),
        ("x", "x"),
    ],
)
def test_snake_case_follows_the_spec_rule(canonical, converted):
    assert snake_case(canonical) == converted


def test_python_members_are_snake_case():
    assert member_name("twoSum", Language.PYTHON) == "two_sum"


@pytest.mark.parametrize("language", [Language.TYPESCRIPT, Language.JAVA, Language.KOTLIN])
def test_other_languages_keep_canonical_member_names(language):
    assert member_name("twoSum", language) == "twoSum"


def test_python_function_names_convert_function_and_params():
    names = symbol_names(function("twoSum", "nums", "maxValue"), Language.PYTHON)
    assert names == FunctionNames("two_sum", {"nums": "nums", "maxValue": "max_value"})


def test_kotlin_function_names_are_canonical():
    names = symbol_names(function("twoSum", "maxValue"), Language.KOTLIN)
    assert names == FunctionNames("twoSum", {"maxValue": "maxValue"})


def test_python_class_names_keep_the_class_and_convert_methods():
    names = symbol_names(design_class("LRUCache", "get", "getRandom"), Language.PYTHON)
    assert names == ClassNames("LRUCache", {"get": "get", "getRandom": "get_random"})


def test_typescript_class_names_are_canonical():
    names = symbol_names(design_class("LRUCache", "getRandom"), Language.TYPESCRIPT)
    assert names == ClassNames("LRUCache", {"getRandom": "getRandom"})


@pytest.mark.parametrize(
    ("word", "language"),
    [
        ("lambda", Language.PYTHON),
        ("None", Language.PYTHON),
        ("default", Language.JAVA),
        ("null", Language.JAVA),
        ("val", Language.KOTLIN),
        ("fun", Language.KOTLIN),
        ("function", Language.TYPESCRIPT),
        ("await", Language.TYPESCRIPT),
    ],
)
def test_reserved_words_per_language(word, language):
    assert is_reserved(word, language)


def test_ordinary_names_are_not_reserved():
    assert not any(is_reserved("nums", language) for language in Language)


def test_no_conflicts_for_ordinary_names():
    assert reserved_name_conflicts(function("twoSum", "nums", "target")) == ()


def test_conflicts_name_every_language_that_reserves_the_name():
    conflicts = reserved_name_conflicts(function("check", "in"))
    assert conflicts == (
        ReservedNameConflict("in", Language.PYTHON, "in"),
        ReservedNameConflict("in", Language.TYPESCRIPT, "in"),
        ReservedNameConflict("in", Language.KOTLIN, "in"),
    )


def test_conflicts_are_checked_after_conversion():
    [conflict] = reserved_name_conflicts(function("check", "lambda"))
    assert conflict == ReservedNameConflict("lambda", Language.PYTHON, "lambda")


def test_conflicts_cover_methods_and_constructor_params():
    signature = ClassSignature(
        "Box", (Param("val", INT),), (Method("default", (), Returns(VoidType())),)
    )
    assert {conflict.name for conflict in reserved_name_conflicts(signature)} == {"val", "default"}


def test_shadowed_python_builtins_are_reported_once():
    assert shadowed_python_builtins(function("sum", "list", "list")) == ("sum", "list")


def test_shadowing_uses_the_python_name():
    assert shadowed_python_builtins(function("maxValue", "nums")) == ()


DATE = ScalarType(Scalar.DATE)
DECIMAL = ScalarType(Scalar.DECIMAL)


def test_a_parameter_named_date_shadows_the_imported_date_type():
    signature = FunctionSignature("daysLeft", (Param("date", DATE),), Returns(INT))
    assert shadowed_python_imports(signature) == ("date",)


def test_a_method_named_date_shadows_the_imported_date_type():
    method = Method("date", (), Returns(DATE))
    signature = ClassSignature("Policy", (), (method,))
    assert shadowed_python_imports(signature) == ("date",)


def test_a_class_named_decimal_shadows_the_imported_decimal_type():
    method = Method("total", (Param("amount", DECIMAL),), Returns(VoidType()))
    signature = ClassSignature("Decimal", (), (method,))
    assert shadowed_python_imports(signature) == ("Decimal",)


def test_a_name_shadows_only_a_type_the_signature_uses():
    signature = FunctionSignature("daysLeft", (Param("date", INT),), Returns(DECIMAL))
    assert shadowed_python_imports(signature) == ()


def test_shadowed_imports_are_reported_once():
    params = (Param("date", DATE), Param("date", DATE))
    assert shadowed_python_imports(FunctionSignature("date", params, Returns(DATE))) == ("date",)
