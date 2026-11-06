"""Check S24: the labels of a catalog problem or item (docs/specs/authoring.md#static).

A catalog entry has `domains`, `job_roles` and `scope`, and its scope fits what it is: a `project`
problem works on a project or a system, any other problem on one function or class, a system design
item on a system and a code review item on a function. A workspace problem may leave all three out,
and when it names a scope that scope has to fit too.
"""

from dataclasses import dataclass

from coding_study.domain.items import ItemMeta
from coding_study.domain.labels import Labels
from coding_study.domain.problem import ProblemKind, ProblemMeta, Track
from coding_study.domain.taxonomy import Scope

_ITEM_SCOPES: dict[Track, tuple[Scope, ...]] = {
    Track.SYSTEM_DESIGN: (Scope.SYSTEM,),
    Track.CODE_REVIEW: (Scope.FUNCTION,),
}
_PROJECT_SCOPES = (Scope.PROJECT, Scope.SYSTEM)
_FUNCTION_SCOPES = (Scope.FUNCTION,)


@dataclass(frozen=True, slots=True)
class LabelIssue:
    location: str
    """The field, such as `scope`."""
    message: str


@dataclass(frozen=True, slots=True)
class _ScopeRule:
    basis: str
    """What the scope has to fit, such as `kind project`."""
    allowed: tuple[Scope, ...]


def problem_label_issues(meta: ProblemMeta) -> tuple[LabelIssue, ...]:
    scopes = _PROJECT_SCOPES if meta.kind is ProblemKind.PROJECT else _FUNCTION_SCOPES
    missing = () if meta.workspace else _missing(meta.labels)
    return (*missing, *_misfit(meta.labels, _ScopeRule(f"kind {meta.kind}", scopes)))


def item_label_issues(meta: ItemMeta) -> tuple[LabelIssue, ...]:
    rule = _ScopeRule(f"track {meta.track}", _ITEM_SCOPES[meta.track])
    return (*_missing(meta.labels), *_misfit(meta.labels, rule))


def _missing(labels: Labels) -> tuple[LabelIssue, ...]:
    absent = (
        ("domains", not labels.domains),
        ("job_roles", not labels.job_roles),
        ("scope", labels.scope is None),
    )
    return tuple(LabelIssue(field, "required in the catalog") for field, gone in absent if gone)


def _misfit(labels: Labels, rule: _ScopeRule) -> tuple[LabelIssue, ...]:
    if labels.scope is None or labels.scope in rule.allowed:
        return ()
    allowed = " or ".join(rule.allowed)
    return (LabelIssue("scope", f"{labels.scope} does not fit {rule.basis}: use {allowed}"),)
