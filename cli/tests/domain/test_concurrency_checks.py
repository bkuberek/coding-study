"""S11 and S12 on the bounded-blocking-queue fixture, one defect at a time."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import Case
from coding_study.domain.concurrency import ConcurrencyModel
from coding_study.domain.concurrency_checks import ConcurrencyContent, concurrency_issues
from coding_study.domain.problem import Language, Problem, ProblemKind, Track
from coding_study.domain.stress import (
    CheckerInvariant,
    Count,
    Literal,
    RandomInteger,
    Repeat,
    Selector,
    Step,
    StressScenario,
    WorkerGroup,
)
from tests.fakes import repository_root
from tests.helpers import CONCURRENCY_PROBLEMS

FIXTURE = CONCURRENCY_PROBLEMS / "0001-bounded-blocking-queue"
BROKEN_FILES = (
    "if-not-while.java",
    "if-not-while.kt",
    "if-not-while.py",
    "if-not-while.ts",
    "no-lock.java",
    "no-lock.kt",
    "no-lock.py",
)


@pytest.fixture(scope="module")
def problem(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("repository"), CONCURRENCY_PROBLEMS)
    return FsProblemRepository(root).load("bounded-blocking-queue")


def content(problem: Problem, **changes: object) -> ConcurrencyContent:
    base = ConcurrencyContent(
        directory="problems/0001-bounded-blocking-queue",
        meta=problem.meta,
        cases=problem.cases,
        problem_markdown=(FIXTURE / "problem.md").read_text(),
        explanation=(FIXTURE / "solutions" / "explanation.md").read_text(),
        files=("meta.yaml", "problem.md", "tests.json"),
        broken_files=BROKEN_FILES,
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def errors(checked: ConcurrencyContent) -> list[str]:
    return [str(issue) for issue in concurrency_issues(checked)]


def with_meta(problem: Problem, **changes: object) -> ConcurrencyContent:
    return content(problem, meta=replace(problem.meta, **changes))  # type: ignore[arg-type]


def with_stress(problem: Problem, **changes: object) -> ConcurrencyContent:
    """`s1` with some fields of its scenario replaced."""
    cases = tuple(
        replace(case, input=replace(case.input, **changes))  # type: ignore[arg-type]
        if case.id == "s1"
        else case
        for case in problem.cases
    )
    return content(problem, cases=cases)


def with_concurrency(problem: Problem, **changes: object) -> ConcurrencyContent:
    concurrency = replace(problem.meta.concurrency, **changes)  # type: ignore[arg-type]
    return with_meta(problem, concurrency=concurrency)


def s1(problem: Problem) -> StressScenario:
    stress = next(case.input for case in problem.cases if case.id == "s1")
    assert isinstance(stress, StressScenario)
    return stress


def workers(*groups: WorkerGroup) -> dict[str, object]:
    return {"workers": groups}


def group(*steps: Step, count: int = 2, repeat: int = 10, is_mix: bool = False) -> WorkerGroup:
    return WorkerGroup("worker", count, Repeat(repeat), steps, is_mix)


def test_the_fixture_passes(problem):
    assert errors(content(problem)) == []


def test_non_concurrent_problems_are_not_checked(problem):
    checked = with_meta(problem, kind=ProblemKind.DESIGN, track=Track.LLD)
    assert errors(checked) == []


def test_kind_concurrent_needs_track_concurrency(problem):
    assert any(
        "track concurrency" in error for error in errors(with_meta(problem, track=Track.LLD))
    )


def test_typescript_cannot_use_threads(problem):
    models = {**problem.meta.concurrency.models, Language.TYPESCRIPT: ConcurrencyModel.THREADS}  # type: ignore[union-attr]
    found = errors(with_concurrency(problem, models=models))
    assert any("typescript cannot use the threads model" in error for error in found)


def test_every_language_needs_a_model(problem):
    models = {Language.JAVA: ConcurrencyModel.THREADS}
    found = errors(with_concurrency(problem, models=models))
    assert any("no model for python" in error for error in found)


def test_a_generator_is_not_allowed(problem):
    found = errors(content(problem, files=("generator.py", "meta.yaml")))
    assert any("generator.py: concurrent problems have no generator" in error for error in found)


def test_the_concurrency_section_is_required(problem):
    markdown = (FIXTURE / "problem.md").read_text().replace("## Concurrency", "## Threads")
    assert any(
        'missing "## Concurrency"' in error
        for error in errors(content(problem, problem_markdown=markdown))
    )


def test_the_concurrency_section_follows_constraints(problem):
    text = (FIXTURE / "problem.md").read_text()
    concurrency = text[text.index("## Concurrency") : text.index("## Hints")]
    moved = text.replace(concurrency, "").replace("## Constraints", concurrency + "## Constraints")
    found = errors(content(problem, problem_markdown=moved))
    assert any('"## Concurrency" must come after "## Constraints"' in error for error in found)


def test_caught_by_names_a_stress_case(problem):
    broken = (replace(problem.meta.concurrency.broken[0], caught_by=("ex1",)),)  # type: ignore[union-attr]
    found = errors(with_concurrency(problem, broken=broken))
    assert any('caught_by "ex1" is not a stress case' in error for error in found)


def test_broken_ids_differ_from_approach_ids(problem):
    broken = (replace(problem.meta.concurrency.broken[0], id="monitor"),)  # type: ignore[union-attr]
    found = errors(with_concurrency(problem, broken=broken))
    assert any('duplicate id "monitor"' in error for error in found)


def test_every_declared_broken_file_exists(problem):
    found = errors(content(problem, broken_files=BROKEN_FILES[1:]))
    assert found == [
        "problems/0001-bounded-blocking-queue/solutions/broken/if-not-while.java: "
        "missing (declared in concurrency.broken)"
    ]


def test_every_broken_file_maps_to_a_broken_reference(problem):
    found = errors(content(problem, broken_files=(*BROKEN_FILES, "deadlock.py")))
    assert any("deadlock.py: maps to no broken reference" in error for error in found)


def test_a_broken_file_outside_its_languages_is_flagged(problem):
    found = errors(content(problem, broken_files=(*BROKEN_FILES, "no-lock.ts")))
    assert any("no-lock.ts: its language is not in" in error for error in found)


def test_every_broken_reference_has_a_section(problem):
    text = (FIXTURE / "solutions" / "explanation.md").read_text()
    edited = text[: text.index("## Broken: if-not-while")]
    found = errors(content(problem, explanation=edited))
    assert any('missing "## Broken: if-not-while (Wait guarded by if)"' in error for error in found)


def test_broken_sections_need_every_subsection(problem):
    text = (FIXTURE / "solutions" / "explanation.md").read_text()
    edited = text.replace("### Failing interleaving", "### Schedule", 1)
    found = errors(content(problem, explanation=edited))
    assert any(
        '"### Failing interleaving" is missing in broken no-lock' in error for error in found
    )


def test_the_constructor_is_not_a_step(problem):
    found = errors(
        with_stress(problem, **workers(group(Step("BoundedBlockingQueue", (Literal(1),)))))
    )
    assert any("the constructor" in error for error in found)


def test_steps_name_methods(problem):
    found = errors(with_stress(problem, **workers(group(Step("peek", ())))))
    assert any('no method "peek"' in error for error in found)


def test_steps_match_the_arity(problem):
    found = errors(with_stress(problem, **workers(group(Step("put", ())))))
    assert any("put takes 1 argument, got 0" in error for error in found)


def test_template_ranges_fit_the_parameter_type(problem):
    found = errors(with_stress(problem, **workers(group(Step("put", (RandomInteger(0, 2**31),))))))
    assert any("outside the int range" in error for error in found)


def test_harness_ops_check_their_arguments(problem):
    found = errors(with_stress(problem, **workers(group(Step("@pause", (Literal(0),))))))
    assert any("@pause takes a count from 1 to 1000" in error for error in found)


def test_probe_sections_are_balanced_per_iteration(problem):
    enter = Step("@enter", (Literal("data"), Literal("exclusive")))
    found = errors(with_stress(problem, **workers(group(enter))))
    assert any('@enter "data" has no @exit' in error for error in found)


def test_a_mix_step_must_balance_its_own_sections(problem):
    enter = Step("@enter", (Literal("data"), Literal("shared")))
    leave = Step("@exit", (Literal("data"),))
    found = errors(with_stress(problem, **workers(group(enter, leave, is_mix=True))))
    assert any("has no @exit in the same iteration" in error for error in found)


def test_selectors_name_methods(problem):
    found = errors(with_stress(problem, invariants=(Count(Selector("peek"), equals=1),)))
    assert any('no method "peek"' in error for error in found)


def test_selectors_name_existing_arguments(problem):
    found = errors(with_stress(problem, invariants=(Count(Selector("put", "arg1"), equals=1),)))
    assert any("put has no argument 1" in error for error in found)


def test_selectors_name_existing_groups(problem):
    found = errors(with_stress(problem, invariants=(Count(Selector("take", group="x"), equals=1),)))
    assert any('no worker group "x"' in error for error in found)


def test_a_void_method_has_no_output_to_select(problem):
    found = errors(with_stress(problem, invariants=(Count(Selector("put"), equals=1),)))
    assert any("put returns nothing" in error for error in found)


def test_a_stress_case_runs_at_least_two_workers(problem):
    found = errors(with_stress(problem, **workers(group(Step("size", ()), count=1))))
    assert any("1 workers; a stress case runs 2 to 64" in error for error in found)


def test_ops_per_run_are_limited(problem):
    found = errors(with_stress(problem, **workers(group(Step("size", ()), repeat=10_001))))
    assert any("ops per run in java; at most 20000" in error for error in found)


def test_a_checker_invariant_needs_stress_checker(problem):
    found = errors(with_stress(problem, invariants=(CheckerInvariant("conserved"),)))
    assert any("stress_checker.py: missing" in error for error in found)


def test_stress_checker_needs_a_checker_invariant(problem):
    found = errors(content(problem, files=("meta.yaml", "stress_checker.py")))
    assert any("stress_checker.py: present but no stress case" in error for error in found)


def test_setup_starts_with_the_constructor(problem):
    setup = replace(s1(problem).setup, ops=("size",))
    found = errors(with_stress(problem, setup=setup))
    assert any(
        'setup.ops[0]: expected the class name "BoundedBlockingQueue"' in error for error in found
    )


def test_sequential_cases_are_left_to_s4(problem):
    cases = (Case("h9", s1(problem).setup),)
    assert errors(content(problem, cases=(*problem.cases, *cases))) == []


def test_unused_paths_are_reported_relative_to_the_problem(problem):
    found = errors(content(problem, broken_files=BROKEN_FILES[1:]))
    assert Path(found[0].split(":")[0]).name == "if-not-while.java"
