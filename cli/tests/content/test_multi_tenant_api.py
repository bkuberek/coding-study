"""multi-tenant-api-typescript runs its migrations as one Postgres role and its app as another, so
that row-level security applies to the app. Its cases name the keys and ids the baseline seeds,
and those of an organization `grade_setup` adds in graded runs only. These tests keep the roles,
the manifest, the compose file, the seeds, the cases and the searches in step."""

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0286-multi-tenant-api-typescript"
PROJECT: Mapping[str, Any] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]
COMPOSE: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "services" / "compose.yaml").read_text(encoding="utf-8")
)
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
BASELINE = (PROBLEM / "starter" / "migrations" / "0001_baseline.sql").read_text(encoding="utf-8")
GRADE_SETUP = (PROBLEM / "grading" / "grade_setup.ts").read_text(encoding="utf-8")
SEARCHES = [
    PROBLEM / "starter" / "src" / "search.ts",
    PROBLEM / "solutions" / "reference" / "src" / "search.ts",
]
HIDDEN_PREFIX = "x-"
BEARER = re.compile(r"^Bearer (\S+)$")


def user_of(variable: str) -> str | None:
    return urlsplit(PROJECT["env"][variable]).username


def seeded_keys(sql: str) -> set[str]:
    """The keys of the one insert into `api_keys` a migration or script holds."""
    values = sql.partition("INSERT INTO api_keys")[2].split("INSERT INTO")[0].partition(";")[0]
    return set(re.findall(r"\('([^']+)', '[^']+', '[^']+'\)", values))


def sql_strings(path: Path) -> str:
    """The double-quoted strings of a TypeScript file, where its queries are, without comments."""
    return " ".join(re.findall(r'"([^"]*)"', path.read_text(encoding="utf-8")))


def requests_of(case: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Each request a case sends, whatever its shape."""
    yield from case.get("before", [])
    if "request" in case:
        yield case["request"]
    for step in case.get("steps", []):
        yield step["request"]
    parallel = case.get("parallel", {})
    yield from parallel.get("requests", [parallel["request"]] if "request" in parallel else [])
    if "after" in case:
        yield case["after"]["request"]


def key_of(request: Mapping[str, Any]) -> str | None:
    found = BEARER.match(request.get("headers", {}).get("Authorization", ""))
    return found[1] if found is not None else None


def refuses_the_key(case: Mapping[str, Any]) -> bool:
    return case.get("expected", {}).get("status") == 401


def visible_cases() -> list[Mapping[str, Any]]:
    return [case for case in TESTS["cases"] if case.get("visible")]


def unordered_step_cases() -> list[Mapping[str, Any]]:
    return [
        case
        for case in TESTS["cases"]
        if "steps" in case and case.get("comparator", {}).get("type") == "unordered"
    ]


def test_grading_applies_the_starters_own_baseline():
    graded = (PROBLEM / "grading" / "baseline" / "0001_baseline.sql").read_text(encoding="utf-8")

    assert graded == BASELINE


def test_the_app_connects_as_the_role_the_baseline_creates_without_bypassing_policies():
    role = user_of("DATABASE_URL")

    assert re.search(rf"CREATE ROLE {role} LOGIN PASSWORD '\w+' NOSUPERUSER NOBYPASSRLS", BASELINE)


def test_migrations_run_as_the_databases_owner():
    owner = COMPOSE["services"]["db"]["environment"]["POSTGRES_USER"]

    assert user_of("OWNER_DATABASE_URL") == owner


def test_the_app_and_the_owner_are_different_roles():
    assert user_of("DATABASE_URL") != user_of("OWNER_DATABASE_URL")


def test_bootstrap_migrates_through_the_owners_url():
    bootstrap = PROJECT["commands"]["bootstrap"]

    assert bootstrap[-2:] == ["--database-url-var", "OWNER_DATABASE_URL"]


@pytest.mark.parametrize(
    "path", ["grading/grade_setup.ts", "starter/scripts/reset.ts"], ids=["grade_setup", "reset"]
)
def test_problem_scripts_connect_as_the_owner(path: str):
    script = (PROBLEM / path).read_text(encoding="utf-8")

    assert "process.env.OWNER_DATABASE_URL" in script
    assert "process.env.DATABASE_URL" not in script


def test_every_key_a_case_sends_is_seeded_or_refused():
    known = seeded_keys(BASELINE) | seeded_keys(GRADE_SETUP)
    sent = {
        key
        for case in TESTS["cases"]
        if not refuses_the_key(case)
        for request in requests_of(case)
        if (key := key_of(request)) is not None
    }

    assert sent <= known


def test_the_organization_grade_setup_adds_uses_only_reserved_ids():
    quoted = re.findall(r"'([^']+)'", GRADE_SETUP.partition("HIDDEN_ORGANIZATION")[2])
    identifiers = [value for value in quoted if re.fullmatch(r"[\w-]+", value) and "-" in value]

    assert identifiers
    assert all(value.startswith(HIDDEN_PREFIX) for value in identifiers)


@pytest.mark.parametrize("case", [pytest.param(case, id=case["id"]) for case in visible_cases()])
def test_a_visible_case_names_nothing_grade_setup_adds(case: Mapping[str, Any]):
    """`cstudy test` runs no `grade_setup`, so the hidden organization is not there."""
    sent = json.dumps(list(requests_of(case)))

    assert re.search(rf"(?<![\w-]){HIDDEN_PREFIX}", sent) is None


@pytest.mark.parametrize("path", SEARCHES, ids=["starter", "reference"])
def test_the_searches_query_by_no_organization(path: Path):
    """They prove the policies: a search that filters by organization itself proves nothing."""
    queries = sql_strings(path)

    assert "FROM tasks" in queries
    assert "tenant" not in queries


@pytest.mark.parametrize(
    "case", [pytest.param(case, id=case["id"]) for case in unordered_step_cases()]
)
def test_a_multi_step_case_compared_unordered_expects_only_lists(case: Mapping[str, Any]):
    """The case's comparator judges every step, and `unordered` takes only a list."""
    bodies = [
        step["expected"]["body"] for step in case["steps"] if "body" in step.get("expected", {})
    ]

    assert all(isinstance(body, list) for body in bodies)
