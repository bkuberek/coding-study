from dataclasses import replace

from coding_study.domain.cases import Case, Expected, FunctionInput, OperationSequence
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Level,
    Problem,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.signature import (
    ClassSignature,
    FunctionSignature,
    Method,
    Param,
    Returns,
)
from coding_study.domain.statement import render_statement
from coding_study.domain.type_dsl import ArrayType, ListType, Scalar, ScalarType, VoidType

INT = ScalarType(Scalar.INT)
META = ProblemMeta(
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
            "Map",
            ApproachRole.OPTIMAL,
            "O(n)",
            "O(n)",
            ComplexityClass.LINEAR,
            ComplexityClass.LINEAR,
        ),
    ),
    patterns=("arrays-hashing",),
)
EX1 = Case("ex1", FunctionInput({"nums": [4, 9, 2, 8], "target": 11}), Expected([1, 2]), True)
HIDDEN = Case("h1", FunctionInput({"nums": [1], "target": 2}), Expected([0, 0]))
PROBLEM_MD = """\
# Two Sum

## Statement

Find them.

## Examples

### Example 1

<!-- case: ex1 -->

The values add up.

## Constraints

- small

## Hints

### Hint 1

Use a map.

## Follow-ups

- faster?
"""


def rendered(markdown: str | None = PROBLEM_MD, cases=(EX1, HIDDEN), meta=META) -> str:
    return render_statement(Problem(meta, cases), markdown, None)


def test_statement_starts_with_the_title():
    assert rendered().splitlines()[0] == "# Two Sum"


def test_statement_shows_difficulty_track_and_patterns_under_the_title():
    assert rendered().splitlines()[2] == "easy · dsa · arrays-hashing"


def test_statement_keeps_the_sections():
    assert "## Statement\n\nFind them." in rendered()


def test_statement_never_shows_hints():
    assert "Use a map" not in rendered()


def test_statement_keeps_sections_after_the_hints():
    assert "## Follow-ups" in rendered()


def test_example_marker_is_replaced_by_input_and_expected_output():
    assert ("```text\nInput:  nums = [4, 9, 2, 8], target = 11\nOutput: [1, 2]\n```") in rendered()


def test_example_marker_is_not_shown():
    assert "<!-- case:" not in rendered()


def test_statement_says_where_it_comes_from():
    assert (
        rendered()
        .rstrip()
        .endswith(
            "<!-- Rendered by cstudy from the problem's problem.md; edits here are overwritten. -->"
        )
    )


def test_without_problem_md_the_visible_cases_become_examples():
    assert "### Example 1\n\n```text\nInput:  nums = [4, 9, 2, 8]" in rendered(None)


def test_without_problem_md_hidden_cases_stay_hidden():
    assert "[0, 0]" not in rendered(None)


def test_operation_sequences_show_operations_arguments_and_outputs():
    case = Case(
        "ex1",
        OperationSequence(("LRUCache", "get"), ((2,), (1,))),
        Expected([None, -1]),
        visible=True,
    )
    assert (
        'Operations: ["LRUCache", "get"]\nArguments:  [[2], [1]]\nOutput:     [null, -1]'
    ) in rendered(None, (case,))


DECIMAL = ScalarType(Scalar.DECIMAL)
DATE = ScalarType(Scalar.DATE)
STRING = ScalarType(Scalar.STRING)
PRORATE = replace(
    META,
    signature=FunctionSignature(
        "prorate",
        (
            Param("premium", DECIMAL),
            Param("start", DATE),
            Param("holidays", ListType(DATE)),
            Param("periods", ArrayType(ArrayType(DATE))),
            Param("classCode", STRING),
        ),
        Returns(ArrayType(DECIMAL)),
    ),
)
PRORATE_CASE = Case(
    "ex1",
    FunctionInput(
        {
            "premium": "2500.50",
            "start": "2026-01-01",
            "holidays": ["2026-01-01", "2026-12-25"],
            "periods": [["2026-01-01", "2026-07-01"]],
            "classCode": "A1",
        }
    ),
    Expected(["1250.25", "0"]),
    visible=True,
)


def test_decimal_and_date_arguments_show_unquoted():
    assert "premium = 2500.50, start = 2026-01-01," in rendered(None, (PRORATE_CASE,), PRORATE)


def test_decimal_and_date_elements_of_arrays_and_lists_show_unquoted():
    assert "holidays = [2026-01-01, 2026-12-25], periods = [[2026-01-01, 2026-07-01]]," in rendered(
        None, (PRORATE_CASE,), PRORATE
    )


def test_string_arguments_stay_quoted():
    assert 'classCode = "A1"\n' in rendered(None, (PRORATE_CASE,), PRORATE)


def test_decimal_outputs_show_unquoted():
    assert "Output: [1250.25, 0]" in rendered(None, (PRORATE_CASE,), PRORATE)


def test_arguments_outside_the_signature_show_as_json():
    case = replace(PRORATE_CASE, input=FunctionInput({"premium": "1", "extra": "2026-01-01"}))
    assert 'extra = "2026-01-01"' in rendered(None, (case,), PRORATE)


RATE_TABLE = replace(
    META,
    kind=ProblemKind.DESIGN,
    signature=ClassSignature(
        "RateTable",
        (Param("currency", STRING),),
        (
            Method(
                "publish",
                (Param("effective", DATE), Param("rates", ListType(DECIMAL))),
                Returns(VoidType()),
            ),
            Method("rateAsOf", (Param("day", DATE), Param("classCode", STRING)), Returns(DECIMAL)),
        ),
    ),
    comparator=ComparatorSpec(ComparatorType.OPS),
)
RATE_TABLE_CASE = Case(
    "ex1",
    OperationSequence(
        ("RateTable", "publish", "rateAsOf", "unknown"),
        (("USD",), ("2026-01-01", ["12.5", "0.75"]), ("2026-03-01", "A1"), ("2026-03-01",)),
    ),
    Expected([None, None, "12.5", "2026-03-01"]),
    visible=True,
)


def test_operation_arguments_show_decimal_and_date_unquoted():
    assert (
        'Arguments:  [["USD"], [2026-01-01, [12.5, 0.75]], [2026-03-01, "A1"], ["2026-03-01"]]'
        in rendered(None, (RATE_TABLE_CASE,), RATE_TABLE)
    )


def test_operation_outputs_show_decimal_and_date_by_each_method_return():
    assert 'Output:     [null, null, 12.5, "2026-03-01"]' in rendered(
        None, (RATE_TABLE_CASE,), RATE_TABLE
    )


def test_output_from_a_parameter_shows_by_the_parameter_type():
    signature = FunctionSignature(
        "sortDays", (Param("days", ArrayType(DATE)),), Returns(VoidType(), output_from="days")
    )
    case = Case("ex1", FunctionInput({"days": ["2026-02-01"]}), Expected(["2026-02-01"]), True)
    meta = replace(META, signature=signature)
    assert "Output: [2026-02-01]" in rendered(None, (case,), meta)


def test_checker_problems_without_expected_accept_any_valid_answer():
    meta = replace(META, comparator=ComparatorSpec(ComparatorType.CHECKER))
    case = Case("ex1", FunctionInput({"n": 3}), None, visible=True)
    assert "Output: any valid answer" in rendered(None, (case,), meta)


def test_checker_problems_show_their_sample_answer_as_one_of_many():
    meta = replace(META, comparator=ComparatorSpec(ComparatorType.CHECKER))
    case = Case("ex1", FunctionInput({"n": 3}), Expected([1, 2]), visible=True)
    assert "Output: [1, 2]  (one valid answer)" in rendered(None, (case,), meta)


def test_unknown_marker_is_kept_for_cs_verify_to_report():
    markdown = "# Two Sum\n\n## Examples\n\n<!-- case: nope -->\n"
    assert "<!-- case: nope -->" in rendered(markdown)


# Progressive problems

LEVELS = (Level(1, "Set and get"), Level(2, "Delete"), Level(3, "Prefix scans"))
PROGRESSIVE = replace(
    META,
    slug="level-store",
    title="Level Store",
    track=Track.PRACTICAL,
    kind=ProblemKind.PROGRESSIVE,
    patterns=(),
    signature=ClassSignature("LevelStore", (), ()),
    comparator=ComparatorSpec(ComparatorType.OPS),
    levels=LEVELS,
)
PROGRESSIVE_MD = """\
# Level Store

## Statement

Build a store.

## Level 1: Set and get

Store values.

### Example 1

<!-- case: ex1 -->

The value comes back.

## Level 2: Delete

Remove values.

### Example 1

<!-- case: ex2 -->

The value is gone.

## Level 3: Prefix scans

List keys by prefix.

### Example 1

<!-- case: ex3 -->

Both keys match.

## Constraints

- small
"""


def level_case(case_id: str, level: int) -> Case:
    return Case(
        case_id,
        OperationSequence(("LevelStore",), ((),)),
        Expected([f"{case_id}-output"]),
        visible=True,
        level=level,
    )


LEVEL_CASES = (level_case("ex1", 1), level_case("ex2", 2), level_case("ex3", 3))


def progressive(unlocked: int | None, markdown: str | None = PROGRESSIVE_MD) -> str:
    return render_statement(Problem(PROGRESSIVE, LEVEL_CASES), markdown, unlocked)


def test_unlocked_levels_are_shown():
    assert "## Level 2: Delete\n\nRemove values." in progressive(2)


def test_locked_levels_are_hidden():
    assert "Prefix scans" not in progressive(2)


def test_examples_of_locked_levels_are_hidden():
    assert "ex3-output" not in progressive(2)


def test_examples_of_unlocked_levels_are_shown():
    assert "ex2-output" in progressive(2)


def test_sections_after_the_locked_levels_are_kept():
    assert "## Constraints" in progressive(1)


def test_a_notice_replaces_the_locked_levels():
    assert (
        "The value comes back.\n\n"
        "> Levels 2 to 3 are locked. Pass every case up to level 1 with `cstudy test` to unlock "
        "the next one.\n\n## Constraints"
    ) in progressive(1)


def test_the_notice_names_a_single_locked_level():
    assert (
        "> Level 3 is locked. Pass every case up to level 2 with `cstudy test` to unlock it."
        in progressive(2)
    )


def test_no_notice_once_every_level_is_unlocked():
    assert "locked" not in progressive(3)


def test_every_level_shows_once_all_are_unlocked():
    assert "## Level 3: Prefix scans" in progressive(3)


def test_progressive_metadata_names_the_unlocked_level():
    assert progressive(2).splitlines()[2] == "easy · practical · level 2 of 3"


def test_without_a_stored_level_only_level_1_shows():
    assert "## Level 2" not in progressive(None)


def test_without_problem_md_examples_are_grouped_by_unlocked_level():
    assert "## Level 2: Delete\n\n### Example 1\n\n```text" in progressive(2, None)


def test_without_problem_md_locked_examples_stay_hidden():
    assert "ex3-output" not in progressive(2, None)
