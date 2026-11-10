"""fix-the-flaws-typescript grades a service that keeps its accounts and notes across the cases of a
run, downloads the starter's own files, and is attacked by probes that only mean something while
the starter would answer them. These tests keep the cases, the starter's files, the manifest and
the reference's queries in step."""

import json
import re
from collections.abc import Iterator, Mapping
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0307-fix-the-flaws-typescript"
ENV: Mapping[str, str] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]["env"]
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
STARTER = PROBLEM / "starter"
ATTACHMENTS = STARTER / "attachments"
ATTACHMENT_PATH = re.compile(r"^/attachments/(.+)$")
SQL_ARGUMENT = re.compile(r"\.prepare\(\s*([`\"])(.*?)\1", re.DOTALL)
REFERENCE_SOURCES = sorted((PROBLEM / "solutions" / "reference" / "src").glob("*.ts"))

type Step = Mapping[str, Any]


def steps_of(steps: list[Step]) -> Iterator[Step]:
    """Each request step, with each flow it uses written in place."""
    for step in steps:
        if "use" in step:
            yield from steps_of(TESTS["flows"][step["use"]])
        elif "request" in step:
            yield step


def users_signed_up(case: Mapping[str, Any]) -> Iterator[str]:
    for step in case["steps"]:
        if "use" in step:
            yield step["with"]["user"]
        elif step.get("request", {}).get("path") == "/users":
            yield step["request"]["json"]["username"]


def resolved(raw_name: str) -> Path:
    """Where the starter's download goes: the name decoded once, joined to the folder."""
    parts = PurePosixPath(unquote(raw_name)).parts
    return Path(ATTACHMENTS, *parts).resolve()


def downloads() -> Iterator[tuple[str, Step, str]]:
    """Each download a case sends: its case, its step and its raw name."""
    for case in TESTS["cases"]:
        for step in steps_of(case["steps"]):
            found = ATTACHMENT_PATH.match(step["request"]["path"])
            if found is not None:
                yield case["id"], step, found[1]


def downloads_served() -> list[Any]:
    return [
        pytest.param(step, name, id=f"{case_id} {name}")
        for case_id, step, name in downloads()
        if step["expected"]["status"] == 200
    ]


def climbs() -> list[Any]:
    """The downloads whose name leads out of the folder."""
    return [
        pytest.param(step, name, id=f"{case_id} {name}")
        for case_id, step, name in downloads()
        if resolved(name).parent != ATTACHMENTS.resolve()
    ]


def written_titles(case: Mapping[str, Any]) -> list[str]:
    return [
        step["request"]["json"]["title"]
        for step in steps_of(case["steps"])
        if step["request"]["method"] == "POST" and step["request"]["path"] == "/notes"
    ]


def searches(case: Mapping[str, Any]) -> Iterator[str]:
    for step in steps_of(case["steps"]):
        if step["request"]["path"] == "/notes" and "query" in step["request"]:
            yield step["request"]["query"]["q"]


def probe_cases() -> list[Any]:
    """The cases whose last search expects nothing back."""
    return [
        pytest.param(case, id=case["id"])
        for case in TESTS["cases"]
        if (last := case["steps"][-1]).get("expected", {}).get("body") == []
        and "query" in last.get("request", {})
    ]


def test_each_user_signs_up_in_one_case():
    """The service keeps its accounts across cases, so a second sign-up would answer 409."""
    users = [user for case in TESTS["cases"] for user in users_signed_up(case)]

    assert sorted(user for user in set(users) if users.count(user) > 1) == []


def test_the_administrator_signs_in_with_the_password_the_app_reads():
    passwords = {
        step["request"]["json"]["password"]
        for case in TESTS["cases"]
        for step in steps_of(case["steps"])
        if step["request"]["path"] == "/login" and step["request"]["json"]["username"] == "admin"
    }

    assert passwords == {ENV["ADMIN_PASSWORD"]}


@pytest.mark.parametrize(("step", "raw_name"), downloads_served())
def test_a_download_expected_back_is_the_starters_file(step: Step, raw_name: str):
    assert step["expected"]["body"] == resolved(raw_name).read_text(encoding="utf-8")


def test_the_cases_climb_out_of_the_folder_more_than_one_way():
    assert len(climbs()) >= 3


@pytest.mark.parametrize(("step", "raw_name"), climbs())
def test_a_climb_is_refused(step: Step, raw_name: str):
    assert step["expected"]["status"] == 404


@pytest.mark.parametrize(("step", "raw_name"), climbs())
def test_a_climb_reaches_a_starter_file_the_starter_would_serve(step: Step, raw_name: str):
    """Otherwise the starter would answer 404 too, and the case would prove nothing."""
    starter_files = {path for path in STARTER.resolve().rglob("*") if path.is_file()}

    assert resolved(raw_name) in starter_files


@pytest.mark.parametrize("case", probe_cases())
def test_a_probe_matches_no_title_so_only_an_injection_answers_one(case: Mapping[str, Any]):
    titles = written_titles(case)

    assert all(text.lower() not in title.lower() for text in searches(case) for title in titles)


@pytest.mark.parametrize("case", probe_cases())
def test_a_probe_holds_a_quote(case: Mapping[str, Any]):
    assert all("'" in text for text in searches(case))


@pytest.mark.parametrize("source", REFERENCE_SOURCES, ids=lambda path: path.name)
def test_the_reference_builds_no_sql_from_a_template(source: Path):
    templates = [
        sql
        for quote, sql in SQL_ARGUMENT.findall(source.read_text(encoding="utf-8"))
        if quote == "`" or "${" in sql
    ]

    assert templates == []


def test_the_starters_search_is_the_one_query_built_from_a_template():
    """The injection the review names is the only one, so the fix of level 3 is complete."""
    found = [
        (path.name, sql)
        for path in sorted((STARTER / "src").glob("*.ts"))
        for quote, sql in SQL_ARGUMENT.findall(path.read_text(encoding="utf-8"))
        if quote == "`" and "${" in sql
    ]

    assert [name for name, _ in found] == ["notes.ts"]
