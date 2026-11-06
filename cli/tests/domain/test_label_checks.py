from dataclasses import replace

import pytest

from coding_study.domain.items import ItemMeta
from coding_study.domain.label_checks import item_label_issues, problem_label_issues
from coding_study.domain.labels import Labels
from coding_study.domain.problem import ContentStatus, Difficulty, ProblemKind, Track
from coding_study.domain.taxonomy import Scope
from tests.project_builders import project_meta

LABELS = Labels(domains=("backend",), job_roles=("backend",), scope=Scope.FUNCTION)
FUNCTION_KINDS = [
    ProblemKind.FUNCTION,
    ProblemKind.DESIGN,
    ProblemKind.PROGRESSIVE,
    ProblemKind.CONCURRENT,
]


def problem_meta(kind: ProblemKind, labels: Labels = LABELS, workspace: bool = False):
    return replace(project_meta(), kind=kind, labels=labels, workspace=workspace)


def item_meta(track: Track, labels: Labels) -> ItemMeta:
    return ItemMeta(
        slug="an-item",
        title="An Item",
        track=track,
        difficulty=Difficulty.EASY,
        estimate_minutes=20,
        status=ContentStatus.READY,
        labels=labels,
    )


def messages(issues) -> list[str]:
    return [f"{issue.location}: {issue.message}" for issue in issues]


@pytest.mark.parametrize("kind", FUNCTION_KINDS)
def test_a_labelled_problem_of_function_scope_passes(kind):
    assert problem_label_issues(problem_meta(kind)) == ()


@pytest.mark.parametrize("scope", [Scope.PROJECT, Scope.SYSTEM])
def test_a_project_kind_problem_has_project_or_system_scope(scope):
    labels = replace(LABELS, scope=scope)
    assert problem_label_issues(problem_meta(ProblemKind.PROJECT, labels)) == ()


@pytest.mark.parametrize("scope", [Scope.PROJECT, Scope.SYSTEM])
@pytest.mark.parametrize("kind", FUNCTION_KINDS)
def test_a_problem_of_another_kind_than_project_has_function_scope(kind, scope):
    labels = replace(LABELS, scope=scope)
    assert messages(problem_label_issues(problem_meta(kind, labels))) == [
        f"scope: {scope} does not fit kind {kind}: use function"
    ]


def test_a_project_kind_problem_cannot_have_function_scope():
    assert messages(problem_label_issues(problem_meta(ProblemKind.PROJECT))) == [
        "scope: function does not fit kind project: use project or system"
    ]


@pytest.mark.parametrize(
    ("missing", "labels"),
    [
        ("domains", replace(LABELS, domains=())),
        ("job_roles", replace(LABELS, job_roles=())),
        ("scope", replace(LABELS, scope=None)),
    ],
)
def test_a_catalog_problem_needs_all_three_labels(missing, labels):
    meta = problem_meta(ProblemKind.FUNCTION, labels)
    assert messages(problem_label_issues(meta)) == [f"{missing}: required in the catalog"]


def test_a_catalog_problem_without_labels_misses_each_of_them():
    meta = problem_meta(ProblemKind.FUNCTION, Labels())
    assert [issue.location for issue in problem_label_issues(meta)] == [
        "domains",
        "job_roles",
        "scope",
    ]


def test_a_workspace_problem_may_leave_the_labels_out():
    assert problem_label_issues(problem_meta(ProblemKind.FUNCTION, Labels(), True)) == ()


def test_a_workspace_problem_that_sets_a_scope_still_has_to_fit_its_kind():
    labels = replace(Labels(), scope=Scope.SYSTEM)
    meta = problem_meta(ProblemKind.FUNCTION, labels, True)
    assert messages(problem_label_issues(meta)) == [
        "scope: system does not fit kind function: use function"
    ]


@pytest.mark.parametrize(
    ("track", "scope"),
    [(Track.SYSTEM_DESIGN, Scope.SYSTEM), (Track.CODE_REVIEW, Scope.FUNCTION)],
)
def test_an_item_has_the_scope_of_its_track(track, scope):
    labels = replace(LABELS, scope=scope)
    assert item_label_issues(item_meta(track, labels)) == ()


def test_a_system_design_item_cannot_have_function_scope():
    assert messages(item_label_issues(item_meta(Track.SYSTEM_DESIGN, LABELS))) == [
        "scope: function does not fit track system-design: use system"
    ]


def test_a_code_review_item_cannot_have_project_scope():
    labels = replace(LABELS, scope=Scope.PROJECT)
    assert messages(item_label_issues(item_meta(Track.CODE_REVIEW, labels))) == [
        "scope: project does not fit track code-review: use function"
    ]


def test_an_item_needs_all_three_labels():
    meta = item_meta(Track.CODE_REVIEW, Labels())
    assert [issue.location for issue in item_label_issues(meta)] == [
        "domains",
        "job_roles",
        "scope",
    ]
