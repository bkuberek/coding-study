import pytest

from coding_study.domain.problem import Language
from coding_study.domain.project import Project
from coding_study.domain.runner_grading import graded_signature, grading_target
from coding_study.domain.runs import CompiledTarget, FileTarget, ProjectTarget
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Returns,
)
from coding_study.domain.type_dsl import Scalar, ScalarType

LONG = ScalarType(Scalar.LONG)
STRING = ScalarType(Scalar.STRING)
CREATE = Method("createAccount", (Param("accountId", STRING),), Returns(LONG), level=1)
TOP = Method("topSpenders", (Param("n", LONG),), Returns(STRING), level=2)
MERGE = Method("mergeAccounts", (Param("otherId", STRING),), Returns(LONG), level=3)
BANK = ClassSignature("Bank", (Param("seed", LONG),), (CREATE, TOP, MERGE))


def test_grading_a_level_keeps_the_methods_of_that_level_and_below():
    assert graded_signature(BANK, 2).methods == (CREATE, TOP)


def test_grading_the_last_level_keeps_every_method():
    assert graded_signature(BANK, 3) == BANK


def test_grading_keeps_the_class_and_its_constructor():
    graded = graded_signature(BANK, 1)
    assert (graded.name, graded.constructor_params) == ("Bank", BANK.constructor_params)


def test_a_method_without_a_level_is_always_graded():
    signature = ClassSignature("Bank", (), (Method("ping", (), Returns(LONG)), TOP))
    assert [method.name for method in graded_signature(signature, 1).methods] == ["ping"]


def test_a_function_signature_has_no_levels_to_grade():
    function = FunctionSignature("twoSum", (), Returns(LONG))
    with pytest.raises(ValueError, match="class"):
        graded_signature(function, 1)


def test_a_python_project_is_graded_through_its_folder_and_entry_module():
    target = grading_target(Project("bank.bank"), Language.PYTHON, "/ws/projects/bank")
    assert target == ProjectTarget("/ws/projects/bank", "bank.bank")


def test_a_typescript_project_is_graded_through_its_entry_file():
    target = grading_target(Project("src/bank.ts"), Language.TYPESCRIPT, "/ws/projects/bank")
    assert target == FileTarget("/ws/projects/bank/src/bank.ts")


def test_a_go_project_is_graded_through_the_user_package_compiled_into_the_runner():
    target = grading_target(Project("bank.go"), Language.GO, "/ws/projects/bank")
    assert target == CompiledTarget("user")


def test_a_language_without_project_problems_has_no_grading_target():
    with pytest.raises(ValueError, match="not yet supported in java"):
        grading_target(Project("bank.Bank"), Language.JAVA, "/ws/projects/bank")
