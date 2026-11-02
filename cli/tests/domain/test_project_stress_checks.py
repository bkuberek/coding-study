"""Static checks on a project problem with stress cases and broken overlays: S7, S10, S11, S12
and S14 as they apply to it (docs/specs/problem-format.md#stress-cases-in-projects)."""

from dataclasses import replace

import pytest

from coding_study.adapters.fs_problem_repository import FsProblemRepository
from coding_study.domain.cases import OperationSequence
from coding_study.domain.concurrency import ConcurrencyModel
from coding_study.domain.problem import Language, Problem
from coding_study.domain.project import ProjectFile, ProjectTree
from coding_study.domain.ready_criteria import ready_problems
from coding_study.domain.static_checks import ProblemContent, static_checks
from coding_study.domain.stress import (
    CheckerInvariant,
    Literal,
    Repeat,
    Step,
    StressScenario,
    WorkerGroup,
)
from tests.fakes import repository_root
from tests.helpers import PROJECT_STRESS_PROBLEMS, TALLY_PROJECT

FIXTURE = PROJECT_STRESS_PROBLEMS / TALLY_PROJECT
DIRECTORY = f"problems/{TALLY_PROJECT}"
META = f"{DIRECTORY}/meta.yaml"
TESTS = f"{DIRECTORY}/tests.json"
PROBLEM = f"{DIRECTORY}/problem.md"
EXPLANATION = f"{DIRECTORY}/solutions/explanation.md"
BROKEN = f"{DIRECTORY}/solutions/broken"


@pytest.fixture(scope="module")
def tally(tmp_path_factory) -> Problem:
    root = repository_root(tmp_path_factory.mktemp("repository"), PROJECT_STRESS_PROBLEMS)
    return FsProblemRepository(root).load("tally-project-python")


def content(problem: Problem, **changes: object) -> ProblemContent:
    base = ProblemContent(
        directory=DIRECTORY,
        problem=problem,
        problem_markdown=(FIXTURE / "problem.md").read_text(),
        explanation=(FIXTURE / "solutions" / "explanation.md").read_text(),
        files=("meta.yaml", "problem.md", "tests.json"),
        solution_files=("explanation.md",),
    )
    return replace(base, **changes)  # type: ignore[arg-type]


def errors(checked: ProblemContent) -> list[str]:
    return [str(issue) for issue in static_checks(checked).errors]


def with_concurrency(problem: Problem, **changes: object) -> Problem:
    concurrency = replace(problem.meta.concurrency, **changes)  # type: ignore[arg-type]
    return replace(problem, meta=replace(problem.meta, concurrency=concurrency))


def with_broken(problem: Problem, **broken: ProjectTree) -> Problem:
    files = problem.project_files
    assert files is not None
    return replace(problem, project_files=replace(files, broken=broken))


def with_case(problem: Problem, case_id: str, **changes: object) -> Problem:
    cases = tuple(
        replace(case, **changes) if case.id == case_id else case  # type: ignore[arg-type]
        for case in problem.cases
    )
    return replace(problem, cases=cases)


def s1(problem: Problem) -> StressScenario:
    stress = next(case.input for case in problem.cases if case.id == "s1")
    assert isinstance(stress, StressScenario)
    return stress


def overlay(path: str = "tally/counts.py", text: str = "class Counts: ...\n") -> ProjectTree:
    return ProjectTree((ProjectFile(path, len(text.encode()), text),))


def test_the_fixture_passes(tally):
    assert errors(content(tally)) == []


def test_the_fixture_loads_its_broken_overlay(tally):
    assert tally.project_files is not None
    assert tally.project_files.broken["unlocked-add"].paths == {"tally/counts.py"}


def test_a_project_needs_no_concurrency_section(tally):
    markdown = (FIXTURE / "problem.md").read_text()
    assert "## Concurrency" not in markdown
    assert not [found for found in errors(content(tally)) if "Concurrency" in found]


def test_the_model_fits_the_language(tally):
    problem = replace(tally, meta=replace(tally.meta, languages=(Language.TYPESCRIPT,)))
    problem = with_concurrency(problem, models={Language.TYPESCRIPT: ConcurrencyModel.THREADS})
    assert f"{META}: concurrency.model: typescript cannot use the threads model (use async)" in (
        errors(content(problem))
    )


def test_a_stress_case_belongs_to_a_level(tally):
    found = errors(content(with_case(tally, "s1", level=None)))
    assert f"{TESTS}: cases[12] s1: level must be from 1 to 2" in found


def test_a_stress_case_calls_only_methods_of_its_level(tally):
    take = WorkerGroup("taker", 2, Repeat(10), (Step("take", (Literal("k"), Literal(1))),))
    scenario = replace(s1(tally), workers=(*s1(tally).workers, take))
    problem = with_case(tally, "s1", input=scenario, level=1)
    assert f"{TESTS}: cases[12] s1: take is introduced at level 2" in errors(content(problem))


def test_a_stress_case_setup_and_final_call_only_methods_of_its_level(tally):
    setup = OperationSequence(("Tally", "take"), ((), ("k", 1)))
    problem = with_case(tally, "s1", input=replace(s1(tally), setup=setup), level=1)
    assert f"{TESTS}: cases[12] s1: take is introduced at level 2" in errors(content(problem))


def test_stress_steps_name_methods(tally):
    bad = WorkerGroup("worker", 2, Repeat(10), (Step("missing", ()),))
    problem = with_case(tally, "s1", input=replace(s1(tally), workers=(bad,)))
    assert f'{TESTS}: cases[12] s1: workers[worker].steps[0]: no method "missing"' in errors(
        content(problem)
    )


def test_caught_by_names_a_stress_case(tally):
    broken = replace(tally.meta.concurrency.broken[0], caught_by=("h1",))  # type: ignore[union-attr]
    problem = with_concurrency(tally, broken=(broken,))
    assert f'{META}: concurrency.broken[0]: caught_by "h1" is not a stress case' in errors(
        content(problem)
    )


def test_every_declared_broken_overlay_exists(tally):
    found = errors(content(with_broken(tally)))
    assert f"{BROKEN}/unlocked-add/: missing (declared in concurrency.broken)" in found


def test_a_declared_broken_overlay_has_files(tally):
    found = errors(content(with_broken(tally, **{"unlocked-add": ProjectTree(())})))
    assert f"{BROKEN}/unlocked-add/: missing (declared in concurrency.broken)" in found


def test_every_broken_overlay_maps_to_a_broken_reference(tally):
    problem = with_broken(tally, **{"unlocked-add": overlay(), "spare": overlay()})
    found = errors(content(problem))
    assert f"{BROKEN}/spare: maps to no broken reference in concurrency.broken" in found


def test_a_broken_reference_of_a_project_is_a_directory(tally):
    found = errors(content(tally, broken_files=("unlocked-add.py",)))
    message = "a project's broken reference is a directory, solutions/broken/<id>/"
    assert f"{BROKEN}/unlocked-add.py: {message}" in found


def test_a_broken_overlay_holds_text(tally):
    binary = ProjectTree((ProjectFile("tally/counts.py", 3, None),))
    found = errors(content(with_broken(tally, **{"unlocked-add": binary})))
    assert f"{BROKEN}/unlocked-add/tally/counts.py: is not UTF-8 text" in found


def test_broken_overlays_need_a_concurrency_block(tally):
    problem = replace(tally, meta=replace(tally.meta, concurrency=None))
    stress_free = replace(
        problem, cases=tuple(case for case in problem.cases if case.id not in ("s1", "s2"))
    )
    found = errors(content(stress_free))
    assert f"{BROKEN}: only a project with a concurrency block has broken overlays" in found


def test_stress_cases_need_a_concurrency_block(tally):
    problem = replace(tally, meta=replace(tally.meta, concurrency=None))
    problem = with_broken(problem)
    message = "a stress case needs the concurrency block in meta.yaml"
    assert f"{TESTS}: cases[12] s1: {message}" in errors(content(problem))


def test_every_broken_overlay_has_its_explanation_section(tally):
    explanation = (FIXTURE / "solutions" / "explanation.md").read_text()
    without = explanation.split("## Broken:")[0]
    found = errors(content(tally, explanation=without))
    assert f'{EXPLANATION}: missing "## Broken: unlocked-add (Add outside the lock)"' in found


def test_a_checker_invariant_needs_stress_checker(tally):
    scenario = replace(s1(tally), invariants=(CheckerInvariant("counts"),))
    found = errors(content(with_case(tally, "s1", input=scenario)))
    assert (
        f"{DIRECTORY}/stress_checker.py: missing (a stress case has a checker invariant)" in found
    )


def test_a_project_may_have_stress_checker_for_a_checker_invariant(tally):
    scenario = replace(s1(tally), invariants=(CheckerInvariant("counts"),))
    files = ("meta.yaml", "problem.md", "tests.json", "stress_checker.py")
    assert errors(content(with_case(tally, "s1", input=scenario), files=files)) == []


def test_stress_checker_needs_a_checker_invariant(tally):
    files = ("meta.yaml", "problem.md", "tests.json", "stress_checker.py")
    found = errors(content(tally, files=files))
    assert (
        f"{DIRECTORY}/stress_checker.py: present but no stress case has a checker invariant"
        in found
    )


def test_an_approach_id_may_not_start_with_broken(tally):
    approach = replace(tally.meta.approaches[0], id="broken-copy")
    problem = replace(tally, meta=replace(tally.meta, approaches=(approach,)))
    assert f'{META}: approaches: approach "broken-copy" may not start with "broken-"' in errors(
        content(problem)
    )


# Ready criteria


def ready(problem: Problem) -> tuple[str, ...]:
    return ready_problems(content(problem))


def test_the_fixture_meets_the_stress_rules_of_ready(tally):
    reasons = ready(tally)
    assert [reason for reason in reasons if "stress" in reason or "broken" in reason] == []
    assert [reason for reason in reasons if "hidden" in reason or "visible" in reason] == []


def test_a_project_with_stress_cases_has_at_least_two(tally):
    problem = replace(tally, cases=tuple(case for case in tally.cases if case.id != "s2"))
    assert "needs at least 2 stress cases (has 1)" in ready(problem)


def test_a_project_with_stress_cases_has_a_broken_overlay(tally):
    assert "no broken reference in python" in ready(with_concurrency(tally, broken=()))


def test_stress_cases_do_not_count_toward_the_hidden_hand_written_cases(tally):
    cases = tuple(case for case in tally.cases if case.id not in ("h5", "h6", "h7"))
    reasons = ready(replace(tally, cases=cases))
    assert "level 2 needs at least 2 hidden hand-written cases (has 1)" in reasons
    assert "needs at least 8 hidden hand-written cases (has 5)" in reasons
