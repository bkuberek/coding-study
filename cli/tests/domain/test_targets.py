import pytest

from coding_study.domain.problem import Language
from coding_study.domain.targets import SolutionFile, is_path_target, parse_solution_file

JAVA_DIRECTORY = "jvm/java/src/main/java/practice/two_sum"
KOTLIN_DIRECTORY = "jvm/kotlin/src/main/kotlin/practice/lru_cache"


@pytest.mark.parametrize(
    "target",
    [
        "python/practice/two_sum.py",
        "./two_sum.py",
        "two_sum.py",
        "typescript/practice/two-sum.ts",
        "Solution.java",
        "Solution.kt",
        "/abs/ws/jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
        "practice\\two_sum.py",
    ],
)
def test_a_separator_or_a_solution_extension_makes_a_path(target):
    assert is_path_target(target)


@pytest.mark.parametrize("target", ["two-sum", "lru-cache", "0001", "py", "ts-kt"])
def test_a_slug_or_id_is_not_a_path(target):
    assert not is_path_target(target)


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("python/practice/two_sum.py", SolutionFile(Language.PYTHON, "two_sum")),
        ("typescript/practice/two-sum.ts", SolutionFile(Language.TYPESCRIPT, "two-sum")),
        (f"{JAVA_DIRECTORY}/Solution.java", SolutionFile(Language.JAVA, "two_sum")),
        (
            "jvm/kotlin/src/main/kotlin/practice/two_sum/Solution.kt",
            SolutionFile(Language.KOTLIN, "two_sum"),
        ),
        (f"{KOTLIN_DIRECTORY}/LRUCache.kt", SolutionFile(Language.KOTLIN, "lru_cache")),
    ],
)
def test_a_layout_path_names_its_language_and_problem(path, expected):
    assert parse_solution_file(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "",
        "README.md",
        "python/practice/two_sum.ts",
        "python/practice/nested/two_sum.py",
        "python/other/two_sum.py",
        "python/practice/two_sum",
        "typescript/practice/two-sum.py",
        "jvm/java/src/main/java/practice/two_sum/Solution.kt",
        "jvm/java/src/main/kotlin/practice/two_sum/Solution.java",
        "jvm/java/src/main/java/practice/Solution.java",
        "jvm/java/src/main/java/practice/two_sum/inner/Solution.java",
        "jvm/java/src/test/java/practice/two_sum/Solution.java",
        "jvm/scala/src/main/scala/practice/two_sum/Solution.scala",
        "../python/practice/two_sum.py",
    ],
)
def test_a_path_outside_the_layout_names_nothing(path):
    assert parse_solution_file(path) is None


def test_a_python_file_belongs_to_the_slug_with_the_same_snake_case():
    assert SolutionFile(Language.PYTHON, "two_sum").belongs_to("two-sum")


def test_a_python_file_does_not_belong_to_another_slug():
    assert not SolutionFile(Language.PYTHON, "two_sum").belongs_to("three-sum")


def test_a_typescript_file_belongs_to_the_slug_it_is_named_after():
    assert SolutionFile(Language.TYPESCRIPT, "two-sum").belongs_to("two-sum")


def test_a_typescript_file_name_is_not_snake_case():
    assert not SolutionFile(Language.TYPESCRIPT, "two_sum").belongs_to("two-sum")
