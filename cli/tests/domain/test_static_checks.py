from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import Case, Expected, FunctionInput, OperationSequence
from coding_study.domain.problem import (
    ComparatorSpec,
    ComparatorType,
    Language,
    Level,
    Perf,
    ProblemKind,
    StubSource,
    Track,
)
from coding_study.domain.signature import Param, Returns
from coding_study.domain.static_checks import ProblemContent, static_checks
from coding_study.domain.type_dsl import VoidType, parse_return_type, parse_value_type
from tests.fakes import repository_root

PRACTICE = Path(__file__).resolve().parents[1] / "fixtures" / "practice" / "problems"
TWO_SUM = PRACTICE / "0001-two-sum"
LRU = PRACTICE / "0002-lru-cache"
META = "problems/0001-two-sum/meta.yaml"
LRU_META = "problems/0002-lru-cache/meta.yaml"
EXPLANATION = "problems/0001-two-sum/solutions/explanation.md"
LRU_EXPLANATION = "problems/0002-lru-cache/solutions/explanation.md"


@pytest.fixture(scope="module")
def problems(tmp_path_factory):
    root = repository_root(tmp_path_factory.mktemp("repository"), PRACTICE)
    repository = FsProblemRepository(root)
    return {slug: repository.load(slug) for slug in ("two-sum", "lru-cache")}


def content(problems, slug="two-sum", **changes) -> ProblemContent:
    directory = TWO_SUM if slug == "two-sum" else LRU
    base = ProblemContent(
        directory=f"problems/{directory.name}",
        problem=problems[slug],
        problem_markdown=(directory / "problem.md").read_text(),
        explanation=(directory / "solutions" / "explanation.md").read_text(),
        files=tuple(sorted(path.name for path in directory.iterdir() if path.is_file())),
        solution_files=tuple(sorted(path.name for path in (directory / "solutions").iterdir())),
    )
    return replace(base, **changes)


def errors(content_) -> list[str]:
    return [str(issue) for issue in static_checks(content_).errors]


def warnings(content_) -> list[str]:
    return [str(issue) for issue in static_checks(content_).warnings]


def edited(text: str, old: str, new: str) -> str:
    assert old in text
    return text.replace(old, new)


def with_meta(problems, slug="two-sum", **meta_changes):
    problem = problems[slug]
    return replace(problem, meta=replace(problem.meta, **meta_changes))


def test_complete_problem_passes(problems):
    assert errors(content(problems)) == []


def test_complete_problem_has_no_warnings(problems):
    assert warnings(content(problems)) == []


def test_optimal_approach_without_language_notes_is_a_warning(problems):
    assert warnings(content(problems, "lru-cache")) == [
        f'{LRU_EXPLANATION}: approach ordered-dict: no "### Language notes"'
    ]


# S3


def test_reserved_names_are_errors(problems):
    meta = problems["two-sum"].meta
    signature = replace(meta.signature, params=(replace(meta.signature.params[0], name="class"),))
    problem = with_meta(problems, signature=signature)
    assert any(
        '"class" is a reserved word in java' in issue
        for issue in errors(content(problems, problem=problem))
    )


def test_a_rust_keyword_that_a_raw_identifier_spells_is_no_error(problems):
    meta = problems["two-sum"].meta
    signature = replace(meta.signature, params=(replace(meta.signature.params[0], name="move"),))
    problem = with_meta(problems, signature=signature, languages=(*meta.languages, Language.RUST))
    assert not any("reserved word" in issue for issue in errors(content(problems, problem=problem)))


def test_a_rust_keyword_no_raw_identifier_spells_is_an_error(problems):
    meta = problems["two-sum"].meta
    signature = replace(meta.signature, params=(replace(meta.signature.params[0], name="self"),))
    problem = with_meta(problems, signature=signature, languages=(*meta.languages, Language.RUST))
    assert f'{META}: signature: "self" is a reserved word in rust' in errors(
        content(problems, problem=problem)
    )


def test_shadowed_python_builtins_are_warnings(problems):
    meta = problems["two-sum"].meta
    signature = replace(meta.signature, params=(replace(meta.signature.params[0], name="sum"),))
    problem = with_meta(problems, signature=signature)
    assert warnings(content(problems, problem=problem)) == [
        f'{META}: signature: "sum" shadows the Python builtin'
    ]


def test_names_that_shadow_an_imported_python_type_are_warnings(problems):
    meta = problems["two-sum"].meta
    day = Param("date", parse_value_type("date"))
    signature = replace(meta.signature, params=(day, *meta.signature.params[1:]))
    problem = with_meta(problems, signature=signature)
    assert warnings(content(problems, problem=problem)) == [
        f'{META}: signature: "date" shadows the type date that the Python stub imports'
    ]


def test_a_go_parameter_that_shadows_an_imported_package_is_a_warning(problems):
    meta = problems["two-sum"].meta
    day = Param("time", parse_value_type("date"))
    signature = replace(meta.signature, params=(day, *meta.signature.params[1:]))
    problem = with_meta(problems, signature=signature, languages=(*meta.languages, Language.GO))
    assert warnings(content(problems, problem=problem)) == [
        f'{META}: signature: "time" shadows the package time that the Go stub imports'
    ]


def test_a_go_function_named_after_an_imported_package_is_an_error(problems):
    meta = problems["two-sum"].meta
    signature = replace(
        meta.signature, name="decimal", returns=Returns(parse_return_type("decimal"))
    )
    problem = with_meta(problems, signature=signature, languages=(*meta.languages, Language.GO))
    conflict = '"decimal" conflicts with the package decimal that the Go stub imports'
    assert f"{META}: signature: {conflict}" in errors(content(problems, problem=problem))


# S4


def test_case_values_are_checked_against_the_signature(problems):
    problem = problems["two-sum"]
    bad = Case("h9", FunctionInput({"nums": [1, "2"], "target": 3}), Expected([0, 1]))
    problem = replace(problem, cases=(*problem.cases, bad))
    assert errors(content(problems, problem=problem)) == [
        'problems/0001-two-sum/tests.json: cases[4] h9: input.nums[1]: expected int, got "2"'
    ]


# S5


def problem_md_errors(problems, old: str, new: str) -> list[str]:
    markdown = edited((TWO_SUM / "problem.md").read_text(), old, new)
    return errors(content(problems, problem_markdown=markdown))


def test_missing_problem_md(problems):
    assert errors(content(problems, problem_markdown=None)) == [
        "problems/0001-two-sum/problem.md: missing"
    ]


def test_title_must_equal_meta(problems):
    assert problem_md_errors(problems, "# Two Sum\n", "# 2Sum\n") == [
        'problems/0001-two-sum/problem.md: title "2Sum" must equal meta.yaml title "Two Sum"'
    ]


def test_required_section_missing(problems):
    assert problem_md_errors(problems, "## Constraints\n", "## Limits\n") == [
        'problems/0001-two-sum/problem.md: missing "## Constraints"'
    ]


def test_required_section_empty(problems):
    markdown = edited(
        (TWO_SUM / "problem.md").read_text(),
        "- `nums`: the integers to search\n- `target`: the required sum\n",
        "",
    )
    assert errors(content(problems, problem_markdown=markdown)) == [
        'problems/0001-two-sum/problem.md: "## Input" is empty'
    ]


def test_sections_in_order(problems):
    markdown = (TWO_SUM / "problem.md").read_text()
    statement = markdown[markdown.index("## Statement") : markdown.index("## Input")]
    reordered = markdown.replace(statement, "").replace(
        "## Constraints", statement + "## Constraints"
    )
    assert errors(content(problems, problem_markdown=reordered)) == [
        'problems/0001-two-sum/problem.md: "## Statement" must come before "## Input"'
    ]


def test_example_without_marker(problems):
    assert problem_md_errors(problems, "<!-- case: ex2 -->\n", "") == [
        "problems/0001-two-sum/problem.md: Example 2 needs exactly one <!-- case: <id> --> marker",
        'problems/0001-two-sum/problem.md: visible case "ex2" has no example',
    ]


def test_example_with_unknown_case(problems):
    assert problem_md_errors(problems, "<!-- case: ex2 -->", "<!-- case: ex9 -->") == [
        'problems/0001-two-sum/problem.md: Example 2: no case "ex9" in tests.json',
        'problems/0001-two-sum/problem.md: visible case "ex2" has no example',
    ]


def test_example_with_hidden_case(problems):
    assert problem_md_errors(problems, "<!-- case: ex2 -->", "<!-- case: h1 -->") == [
        'problems/0001-two-sum/problem.md: Example 2: case "h1" is not visible',
        'problems/0001-two-sum/problem.md: visible case "ex2" has no example',
    ]


def test_example_needs_an_explanation(problems):
    assert problem_md_errors(
        problems, "Equal values at different positions form a valid pair.\n", ""
    ) == ["problems/0001-two-sum/problem.md: Example 2 needs at least one line of explanation"]


def test_case_referenced_twice(problems):
    assert problem_md_errors(problems, "<!-- case: ex2 -->", "<!-- case: ex1 -->") == [
        'problems/0001-two-sum/problem.md: visible case "ex1" is referenced 2 times',
        'problems/0001-two-sum/problem.md: visible case "ex2" has no example',
    ]


def test_hints_are_numbered_from_one(problems):
    assert problem_md_errors(problems, "### Hint 2", "### Hint 3") == [
        'problems/0001-two-sum/problem.md: hint 2 is titled "Hint 3"'
    ]


def test_todo_placeholder(problems):
    assert problem_md_errors(problems, "Exactly one valid pair exists.", "TODO") == [
        'problems/0001-two-sum/problem.md: "## Constraints" contains TODO'
    ]


# S6


def explanation_errors(problems, old: str, new: str) -> list[str]:
    explanation = edited((TWO_SUM / "solutions/explanation.md").read_text(), old, new)
    return errors(content(problems, explanation=explanation))


def test_missing_explanation(problems):
    assert errors(content(problems, explanation=None)) == [f"{EXPLANATION}: missing"]


def test_missing_subsection(problems):
    assert explanation_errors(
        problems, "### Correctness\n\nEvery pair is checked, so the unique answer is found.\n", ""
    ) == [f'{EXPLANATION}: missing "### Correctness" in approach brute-force']


def test_missing_approach_section(problems):
    explanation = (TWO_SUM / "solutions/explanation.md").read_text()
    cut = explanation[: explanation.index("## Approach: hash-map")]
    assert errors(content(problems, explanation=cut)) == [
        f'{EXPLANATION}: missing "## Approach: hash-map (One-pass hash map)"'
    ]


def test_section_for_an_unknown_approach(problems):
    assert explanation_errors(
        problems,
        "## Approach: hash-map (One-pass hash map)",
        "## Approach: hashing (One-pass hash map)",
    )[0] == (f'{EXPLANATION}: "## Approach: hashing" names no approach in meta.yaml')


def test_heading_name_must_equal_meta(problems):
    assert explanation_errors(problems, "(Check every pair)", "(Pairs)") == [
        f'{EXPLANATION}: approach brute-force is named "Check every pair" in meta.yaml, not "Pairs"'
    ]


def test_complexity_must_equal_meta(problems):
    assert explanation_errors(
        problems, "- Time: O(n) — one pass", "- Time: O(n log n) — one pass"
    ) == [f'{EXPLANATION}: approach hash-map: needs a line "- Time: O(n) — <why>"']


def test_overview_row_must_match_meta(problems):
    assert explanation_errors(
        problems, "| hash-map | optimal | O(n) | O(n) |", "| hash-map | optimal | O(1) | O(n) |"
    ) == [f'{EXPLANATION}: ## Overview row hash-map: time "O(1)" must equal meta.yaml "O(n)"']


def test_overview_needs_every_approach(problems):
    assert explanation_errors(
        problems, "| brute-force | brute | O(n^2) | O(1) | n is tiny |\n", ""
    ) == [f"{EXPLANATION}: ## Overview has no row for brute-force"]


# S7


def test_solution_file_for_an_unknown_approach(problems):
    files = (*content(problems).solution_files, "greedy.py")
    assert errors(content(problems, solution_files=files)) == [
        "problems/0001-two-sum/solutions/greedy.py: maps to no declared approach"
    ]


def test_bytecode_and_hidden_files_are_ignored(problems):
    files = (*content(problems).solution_files, ".DS_Store")
    assert errors(content(problems, solution_files=files)) == []


def test_approach_without_a_file(problems):
    files = tuple(name for name in content(problems).solution_files if name != "brute-force.py")
    assert errors(content(problems, solution_files=files)) == [
        f"{META}: approaches: brute-force has no reference file in solutions/",
        f"{META}: approaches: oracle brute-force needs solutions/brute-force.py",
    ]


# S8


def test_checker_comparator_needs_checker_py(problems):
    problem = with_meta(problems, comparator=ComparatorSpec(ComparatorType.CHECKER))
    assert errors(content(problems, problem=problem)) == [
        "problems/0001-two-sum/checker.py: missing (comparator: checker)"
    ]


def test_checker_py_needs_the_checker_comparator(problems):
    files = (*content(problems).files, "checker.py")
    assert errors(content(problems, files=files)) == [
        "problems/0001-two-sum/checker.py: present but the comparator is unordered"
    ]


def test_buggy_stub_needs_a_file_per_language(problems):
    problem = with_meta(problems, stub=StubSource.BUGGY)
    assert len(errors(content(problems, problem=problem))) == 4


FLOAT = ComparatorSpec(ComparatorType.FLOAT)
FLOAT_ON_DECIMAL = (
    '"float" applies its tolerance to doubles only, and {subject} decimal and no double: '
    "decimals compare exactly by value, so use {fix}"
)


def comparator_errors(content_: ProblemContent) -> list[str]:
    return [issue for issue in errors(content_) if ": comparator" in issue]


def returning(problems, declared: str, comparator: ComparatorSpec) -> ProblemContent:
    signature = problems["two-sum"].meta.signature
    returns = replace(signature.returns, type=parse_return_type(declared))
    problem = with_meta(
        problems, signature=replace(signature, returns=returns), comparator=comparator
    )
    return content(problems, problem=problem)


def lru_returning(problems, get: str, put: str, comparator: ComparatorSpec) -> ProblemContent:
    lru = problems["lru-cache"]
    signature = lru.meta.signature
    get_method, put_method = signature.methods
    methods = (
        replace(get_method, returns=Returns(parse_return_type(get))),
        replace(put_method, returns=Returns(parse_return_type(put))),
    )
    meta = replace(lru.meta, signature=replace(signature, methods=methods), comparator=comparator)
    return content(problems, "lru-cache", problem=replace(lru, meta=meta))


def test_float_comparator_on_a_decimal_return_is_an_error(problems):
    assert comparator_errors(returning(problems, "list<decimal>", FLOAT)) == [
        f"{META}: comparator: " + FLOAT_ON_DECIMAL.format(subject="twoSum returns", fix="exact")
    ]


def test_float_comparator_on_a_double_return_is_fine(problems):
    assert comparator_errors(returning(problems, "double[]", FLOAT)) == []


def test_exact_comparator_on_a_decimal_return_is_fine(problems):
    assert (
        comparator_errors(returning(problems, "decimal", ComparatorSpec(ComparatorType.EXACT)))
        == []
    )


def test_float_comparator_on_a_decimal_output_from_parameter_is_an_error(problems):
    signature = problems["two-sum"].meta.signature
    decimals = Param("amounts", parse_value_type("decimal[]"))
    returns = Returns(VoidType(), output_from="amounts")
    problem = with_meta(
        problems,
        signature=replace(signature, params=(decimals,), returns=returns),
        comparator=FLOAT,
    )
    assert comparator_errors(content(problems, problem=problem)) == [
        f"{META}: comparator: " + FLOAT_ON_DECIMAL.format(subject="twoSum returns", fix="exact")
    ]


def test_float_comparator_on_methods_returning_only_decimals_is_an_error(problems):
    assert comparator_errors(lru_returning(problems, "decimal", "void", FLOAT)) == [
        f"{LRU_META}: comparator: "
        + FLOAT_ON_DECIMAL.format(subject="the methods of LRUCache return", fix="ops")
    ]


def test_float_comparator_on_methods_returning_a_double_too_is_fine(problems):
    assert comparator_errors(lru_returning(problems, "decimal", "double", FLOAT)) == []


def test_per_method_float_on_a_decimal_method_is_an_error(problems):
    per_method = ComparatorSpec(ComparatorType.OPS, per_method={"get": ComparatorType.FLOAT})
    assert comparator_errors(lru_returning(problems, "list<decimal>", "double", per_method)) == [
        f"{LRU_META}: comparator.per_method.get: "
        + FLOAT_ON_DECIMAL.format(subject="get returns", fix="exact")
    ]


def test_per_method_float_on_a_double_method_is_fine(problems):
    per_method = ComparatorSpec(ComparatorType.OPS, per_method={"put": ComparatorType.FLOAT})
    assert comparator_errors(lru_returning(problems, "decimal", "double", per_method)) == []


def test_lld_problems_need_a_rubric(problems):
    problem = with_meta(problems, track=Track.LLD)
    assert errors(content(problems, problem=problem)) == [
        "problems/0001-two-sum/rubric.md: missing (track: lld)"
    ]


# S9


def test_expected_from_must_be_a_python_approach(problems):
    problem = with_meta(problems, perf=Perf(expected_from="sorting"))
    assert errors(content(problems, problem=problem)) == [
        f'{META}: perf.expected_from: "sorting" has no Python reference'
    ]


def test_size_ladder_ascending(problems):
    problem = with_meta(problems, perf=Perf(size_ladder=(100, 10), expected_from="hash-map"))
    assert errors(content(problems, problem=problem)) == [
        f"{META}: perf.size_ladder: must be ascending"
    ]


# S10


GET_ONLY = Case(
    "l1", OperationSequence(("LRUCache", "get"), ((1,), (1,))), Expected([None, -1]), True, 1
)
"""A visible level-1 case, so level 1 has an example whatever level the other cases get."""


def progressive(problems, case_level: int | None, levels=(1, 2)) -> ProblemContent:
    lru = problems["lru-cache"]
    signature = lru.meta.signature
    methods = (replace(signature.methods[0], level=1), replace(signature.methods[1], level=2))
    meta = replace(
        lru.meta,
        kind=ProblemKind.PROGRESSIVE,
        levels=tuple(Level(number, f"Step {number}") for number in levels),
        signature=replace(signature, methods=methods),
    )
    cases = (*(replace(case, level=case_level) for case in lru.cases), GET_ONLY)
    level_1 = "## Level 1: Step 1\n\nGet.\n\n### Example 1\n\n<!-- case: l1 -->\n\nEmpty.\n\n"
    markdown = (
        (LRU / "problem.md").read_text().replace("## Examples", f"{level_1}## Level 2: Step 2")
    )
    return content(
        problems,
        "lru-cache",
        problem=replace(lru, meta=meta, cases=cases),
        problem_markdown=markdown,
    )


def test_progressive_cases_use_only_unlocked_methods(problems):
    found = errors(progressive(problems, case_level=1))
    assert [message for message in found if "introduced" in message] == [
        "problems/0002-lru-cache/tests.json: cases[0] ex1: put is introduced at level 2",
        "problems/0002-lru-cache/tests.json: cases[1] h1: put is introduced at level 2",
    ]


def test_progressive_cases_need_a_level(problems):
    assert "problems/0002-lru-cache/tests.json: cases[0] ex1: level must be from 1 to 2" in errors(
        progressive(problems, case_level=None)
    )


def test_progressive_levels_are_contiguous(problems):
    assert (
        "problems/0002-lru-cache/meta.yaml: levels: levels must be numbered 1, 2, ... without gaps"
        in errors(progressive(problems, case_level=2, levels=(1, 3)))
    )


def test_valid_progressive_problem(problems):
    assert errors(progressive(problems, case_level=2)) == []


# S13


def list_problem(problems, case_input):
    meta = problems["two-sum"].meta
    head = Param("head", parse_value_type("ListNode"))
    signature = replace(meta.signature, params=(head,), returns=Returns(parse_return_type("int")))
    languages = (*meta.languages, Language.RUST)
    case = Case("c1", FunctionInput({"head": case_input}), Expected(1))
    problem = replace(problems["two-sum"], cases=(case,))
    return replace(problem, meta=replace(meta, signature=signature, languages=languages))


def test_rust_cannot_be_listed_with_a_cyclic_list_input(problems):
    problem = list_problem(problems, {"values": [1, 2], "cycle_at": 0})
    assert (
        f"{META}: languages: cannot list rust: a cyclic ListNode input cannot be built in Rust: "
        "an Option<Box<ListNode>> cannot point back"
    ) in errors(content(problems, problem=problem))


def test_rust_can_be_listed_with_an_acyclic_list_input(problems):
    problem = list_problem(problems, [1, 2])
    issues = errors(content(problems, problem=problem))
    assert [issue for issue in issues if "cannot list" in issue] == []
