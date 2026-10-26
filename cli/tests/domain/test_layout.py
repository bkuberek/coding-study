from dataclasses import replace

import pytest

from coding_study.domain import layout
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Language,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.runs import ClassTarget, FileTarget
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import Scalar, ScalarType

INT = ScalarType(Scalar.INT)
ROOT = "/repo"

TWO_SUM = ProblemMeta(
    id="0001",
    slug="two-sum",
    title="Two Sum",
    status=ContentStatus.READY,
    difficulty=Difficulty.EASY,
    track=Track.DSA,
    kind=ProblemKind.FUNCTION,
    signature=FunctionSignature("twoSum", (Param("nums", INT),), Returns(INT)),
    comparator=ComparatorSpec(ComparatorType.UNORDERED),
    approaches=(
        Approach(
            "hash-map",
            "Hash map",
            ApproachRole.OPTIMAL,
            "O(n)",
            "O(n)",
            ComplexityClass.LINEAR,
            ComplexityClass.LINEAR,
        ),
    ),
)
LRU_CACHE = replace(
    TWO_SUM,
    id="0002",
    slug="lru-cache",
    kind=ProblemKind.DESIGN,
    signature=ClassSignature(
        "LRUCache", (Param("capacity", INT),), (Method("get", (), Returns(INT)),)
    ),
    comparator=ComparatorSpec(ComparatorType.OPS),
)


@pytest.mark.parametrize(
    ("meta", "language", "path"),
    [
        (TWO_SUM, Language.PYTHON, "python/practice/two_sum.py"),
        (TWO_SUM, Language.TYPESCRIPT, "typescript/practice/two-sum.ts"),
        (
            TWO_SUM,
            Language.JAVA,
            "jvm/java/src/main/java/practice/two_sum/Solution.java",
        ),
        (
            TWO_SUM,
            Language.KOTLIN,
            "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
        ),
        (
            LRU_CACHE,
            Language.JAVA,
            "jvm/java/src/main/java/practice/lru_cache/LRUCache.java",
        ),
        (
            LRU_CACHE,
            Language.KOTLIN,
            "jvm/kotlin/src/main/kotlin/practice/lru_cache/LRUCache.kt",
        ),
        (LRU_CACHE, Language.PYTHON, "python/practice/lru_cache.py"),
    ],
)
def test_stub_path(meta, language, path):
    assert layout.stub_path(meta, language) == path


def test_statement_path():
    assert layout.statement_path("two-sum") == ".statements/two-sum.md"


def test_archive_directory():
    assert layout.archive_directory("two-sum", 12, Language.KOTLIN) == ".archive/two-sum/12-kotlin"


@pytest.mark.parametrize("language", [Language.PYTHON, Language.TYPESCRIPT])
def test_script_languages_run_the_user_file(language):
    assert layout.user_target(TWO_SUM, language, ROOT) == FileTarget(
        f"{ROOT}/{layout.stub_path(TWO_SUM, language)}"
    )


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_jvm_languages_run_the_user_class(language):
    assert layout.user_target(TWO_SUM, language, ROOT) == ClassTarget("practice.two_sum.Solution")


def test_jvm_class_kinds_run_the_declared_class():
    assert layout.user_target(LRU_CACHE, Language.JAVA, ROOT) == ClassTarget(
        "practice.lru_cache.LRUCache"
    )


def test_script_languages_watch_the_user_file():
    assert layout.watch_path(TWO_SUM, Language.TYPESCRIPT) == ("typescript/practice/two-sum.ts")


def test_jvm_languages_watch_the_problem_package():
    assert layout.watch_path(TWO_SUM, Language.KOTLIN) == (
        "jvm/kotlin/src/main/kotlin/practice/two_sum"
    )


@pytest.mark.parametrize(
    ("language", "name"),
    [
        (Language.PYTHON, "hash-map.py"),
        (Language.TYPESCRIPT, "hash-map.ts"),
        (Language.JAVA, "hash-map.java"),
        (Language.KOTLIN, "hash-map.kt"),
    ],
)
def test_reference_file_name(language, name):
    assert layout.reference_file_name("hash-map", language) == name


def test_language_of_reference_file():
    assert layout.language_of_extension("kt") is Language.KOTLIN


def test_unknown_extension_has_no_language():
    assert layout.language_of_extension("md") is None


@pytest.mark.parametrize(
    ("meta", "language", "path"),
    [
        (TWO_SUM, Language.PYTHON, ".cs/build/python/ref/two_sum/hash_map.py"),
        (TWO_SUM, Language.TYPESCRIPT, ".cs/build/typescript/ref/two-sum/hash-map.ts"),
        (
            TWO_SUM,
            Language.JAVA,
            ".cs/build/jvm/java/src/main/java/ref/two_sum/hash_map/Solution.java",
        ),
        (
            LRU_CACHE,
            Language.KOTLIN,
            ".cs/build/jvm/kotlin/src/main/kotlin/ref/lru_cache/hash_map/LRUCache.kt",
        ),
    ],
)
def test_reference_build_path(meta, language, path):
    assert layout.reference_build_path(meta, "hash-map", language) == path


def test_script_references_run_the_materialized_file():
    assert layout.reference_target(TWO_SUM, "hash-map", Language.PYTHON, ROOT) == FileTarget(
        f"{ROOT}/.cs/build/python/ref/two_sum/hash_map.py"
    )


def test_jvm_references_run_the_materialized_class():
    assert layout.reference_target(TWO_SUM, "hash-map", Language.JAVA, ROOT) == ClassTarget(
        "ref.two_sum.hash_map.Solution"
    )


def test_jvm_reference_package():
    assert layout.jvm_reference_package(TWO_SUM, "hash-map") == "ref.two_sum.hash_map"
