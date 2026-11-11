"""Every kind of problem in every language gets code intelligence by a route the catalog names, or
says in data why not (docs/specs/web-ui.md#where-each-server-runs). The kinds and languages come
from the domain's enums, so a new one fails here until it has a route."""

import itertools
import re
from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.adapters.problem_documents import meta_from_document
from coding_study.domain.code_intelligence import (
    SERVICE_PROJECT_ROUTES,
    SIDECAR_SERVERS,
    Placement,
    RouteKind,
    route_for,
    route_kind,
    route_of,
    server_for,
)
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta, Track
from tests.service_problems import meta_document

SPEC = Path(__file__).resolve().parents[3] / "docs" / "specs" / "web-ui.md"
TABLE_HEADING = "### Where each server runs"
EXPECTED_GAPS = {
    Language.RUST: Placement.NOT_APPLICABLE,
}
"""The service projects without a server, each with its reason in the catalog's data: a cell that
loses its route fails here, as does one that gains it without this list changing."""


def service_meta(language: Language) -> ProblemMeta:
    return meta_from_document({**meta_document(), "languages": [language.value]}, "meta.yaml")


def meta_of(kind: ProblemKind, track: Track = Track.DSA) -> ProblemMeta:
    """A problem of `kind` that is no service project."""
    return replace(service_meta(Language.PYTHON), kind=kind, track=track, project=None)


@pytest.mark.parametrize("language", Language)
@pytest.mark.parametrize("kind", ProblemKind)
def test_every_kind_runs_its_languages_server_on_this_machine(kind, language):
    route = route_of(meta_of(kind), language)

    assert (route and route.placement) is Placement.NATIVE


@pytest.mark.parametrize("language", Language)
def test_a_debugging_problem_runs_its_languages_server_on_this_machine(language):
    route = route_of(meta_of(ProblemKind.FUNCTION, Track.DEBUGGING), language)

    assert (route and route.placement) is Placement.NATIVE


def test_a_debugging_problem_is_its_own_kind_in_the_table():
    assert route_kind(meta_of(ProblemKind.FUNCTION, Track.DEBUGGING)) is RouteKind.DEBUGGING


def test_a_service_project_is_its_own_kind_in_the_table():
    assert route_kind(service_meta(Language.PYTHON)) is RouteKind.SERVICE_PROJECT


@pytest.mark.parametrize("language", Language)
def test_every_service_project_has_a_route_or_a_reason_in_data(language):
    route = route_of(service_meta(language), language)

    assert route is not None
    if not route.runs:
        assert (EXPECTED_GAPS.get(language), bool(route.reason)) == (route.placement, True)


def test_the_service_projects_without_a_server_are_the_expected_ones():
    gaps = {
        language: route.placement
        for language, route in SERVICE_PROJECT_ROUTES.items()
        if not route.runs
    }

    assert gaps == EXPECTED_GAPS


def test_no_cell_waits_for_p13_any_more():
    assert not any("P13" in route.reason for route in SERVICE_PROJECT_ROUTES.values())


@pytest.mark.parametrize("language", Language)
@pytest.mark.parametrize("kind", RouteKind)
def test_a_route_that_runs_a_server_has_one_to_run(kind, language):
    route = route_for(kind, language)
    server = server_for(language)

    if route is not None and route.runs:
        expected = server in SIDECAR_SERVERS if route.placement is Placement.SIDECAR else True
        assert (server is not None, expected) == (True, True)


def spec_table() -> dict[tuple[str, str], str]:
    """The first table under `TABLE_HEADING` in the web UI spec: each cell by its row's kind and
    its column's language, in lower case."""
    text = SPEC.read_text(encoding="utf-8").split(TABLE_HEADING, 1)[1]
    lines = text.splitlines()
    first = next(index for index, line in enumerate(lines) if line.startswith("|"))
    rows = list(itertools.takewhile(lambda line: line.startswith("|"), lines[first:]))
    header = [cell.lower() for cell in _cells(rows[0])]
    cells: dict[tuple[str, str], str] = {}
    for row in rows[2:]:
        kind, *values = _cells(row)
        pairs = zip(header[1:], values, strict=True)
        cells.update({(kind.lower(), language): value.lower() for language, value in pairs})
    return cells


def _cells(row: str) -> list[str]:
    return [re.sub(r"[`*]", "", cell).strip() for cell in row.strip().strip("|").split("|")]


WORDS = {
    Placement.NATIVE: "native",
    Placement.SIDECAR: "sidecar",
    Placement.PENDING: "pending",
    Placement.NOT_APPLICABLE: "not applicable",
}


@pytest.mark.parametrize("language", Language)
@pytest.mark.parametrize("kind", RouteKind)
def test_the_specs_table_says_what_the_catalog_does(kind, language):
    route = route_for(kind, language)
    written = spec_table()[(kind.value.replace("_", " "), language.value)]

    assert written.startswith(WORDS[route.placement] if route else "no route")
