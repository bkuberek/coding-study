"""Project problems built in code, for the generated level tests and the project statement."""

from collections.abc import Sequence

from coding_study.domain.cases import Case, Expected, JsonValue, OperationSequence
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Language,
    Level,
    Problem,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.project import Project
from coding_study.domain.signature import ClassSignature, Method, Param, Returns
from coding_study.domain.type_dsl import parse_return_type, parse_value_type

type Call = tuple[str, Sequence[JsonValue], JsonValue]
"""An operation of a case: the canonical method, its arguments and its expected output."""


def method(name: str, level: int, params: str = "", returns: str = "void") -> Method:
    """`params` as `name: type` pairs separated by `;`: `timestamp: long; accountId: string`."""
    declared = tuple(
        Param(param_name.strip(), parse_value_type(type_text.strip()))
        for param_name, type_text in (pair.split(":") for pair in params.split(";") if pair)
    )
    return Method(name, declared, Returns(parse_return_type(returns)), level=level)


CREATE_ACCOUNT = method("createAccount", 1, "timestamp: long; accountId: string", "bool")
DEPOSIT = method("deposit", 1, "timestamp: long; accountId: string; amount: long", "long")
TRANSFER = method(
    "transfer", 2, "timestamp: long; sourceId: string; targetId: string; amount: long", "long"
)
BANK = ClassSignature("Bank", (), (CREATE_ACCOUNT, DEPOSIT, TRANSFER))
LEVELS = (Level(1, "Accounts"), Level(2, "Transfers"))
OPS = ComparatorSpec(ComparatorType.OPS)


def project_meta(
    signature: ClassSignature = BANK,
    comparator: ComparatorSpec = OPS,
    language: Language = Language.PYTHON,
    levels: tuple[Level, ...] = LEVELS,
) -> ProblemMeta:
    return ProblemMeta(
        id="0001",
        slug=f"bank-project-{language}",
        title="Bank Project",
        status=ContentStatus.DRAFT,
        difficulty=Difficulty.MEDIUM,
        track=Track.PRACTICAL,
        kind=ProblemKind.PROJECT,
        signature=signature,
        comparator=comparator,
        approaches=(
            Approach(
                "reference",
                "Balances in a dictionary",
                ApproachRole.OPTIMAL,
                "O(1)",
                "O(n)",
                ComplexityClass.CONSTANT,
                ComplexityClass.LINEAR,
            ),
        ),
        languages=(language,),
        levels=levels,
        project=Project("bank.bank" if language is Language.PYTHON else "src/bank.ts"),
    )


def ops_case(
    case_id: str,
    level: int,
    *calls: Call,
    visible: bool = True,
    note: str | None = None,
    constructor: Sequence[JsonValue] = (),
    class_name: str = "Bank",
) -> Case:
    ops = (class_name, *(name for name, _, _ in calls))
    args = (tuple(constructor), *(tuple(arguments) for _, arguments, _ in calls))
    expected: list[JsonValue] = [None, *(output for _, _, output in calls)]
    return Case(
        case_id, OperationSequence(ops, args), Expected(expected), visible, level, note=note
    )


def project_problem(*cases: Case, meta: ProblemMeta | None = None) -> Problem:
    return Problem(meta or project_meta(), cases)
