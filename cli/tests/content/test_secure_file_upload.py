"""secure-file-upload-typescript carries every file its cases upload as base64 in tests.json, and
each submission grades the earlier levels again, so a level 1 upload must still pass level 2's
type rules. These tests keep the files, the records and bytes the cases expect back, the bodies
built around `MAX_BODY_BYTES`, the scanner's delays and the users that keep each case's quota its
own in step."""

import base64
import hashlib
import json
import re
from collections.abc import Iterator, Mapping
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0289-secure-file-upload-typescript"
PROJECT: Mapping[str, Any] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]
ENV: Mapping[str, str] = PROJECT["env"]
SCANNER: Mapping[str, Any] = yaml.safe_load(
    (PROBLEM / "mocks" / "scanner.yaml").read_text(encoding="utf-8")
)
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
CASES = {case["id"]: case for case in TESTS["cases"]}
MAX_BODY_BYTES = int(ENV["MAX_BODY_BYTES"])
SCAN_TIMEOUT_MS = 1000
"""What the statement gives each request to the scanner."""
MAGIC_BY_EXTENSION: Mapping[str, tuple[bytes, ...]] = {
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
    "pdf": (b"%PDF-",),
}
ACTIVE_MARKERS = ("<!doctype", "<html", "<head", "<body", "<script", "<iframe", "<svg")
ACCEPTED = (201, 202)
CAPTURED_ID = re.compile(r"^/files/\{\{(\w+)\}\}(/content)?$")

type Step = Mapping[str, Any]


def steps_of(case: Mapping[str, Any]) -> Iterator[Step]:
    """Each request a case sends with what it expects, whatever the case's shape."""
    if "request" in case:
        yield {"request": case["request"], "expected": case["expected"]}
    yield from case.get("steps", [])
    parallel = case.get("parallel")
    if parallel is not None:
        yield {"request": parallel["request"], "expected": {"status": ACCEPTED[0]}}
    if "after" in case:
        yield case["after"]


def is_upload(step: Step) -> bool:
    request = step["request"]
    return request["method"] == "POST" and request.get("path") == "/files" and "json" in request


def file_uploads() -> Iterator[Any]:
    """Each upload that carries a file, as a parameter named by its case and the file's name."""
    for case in TESTS["cases"]:
        for step in steps_of(case):
            if is_upload(step) and "data" in step["request"]["json"]:
                name = step["request"]["json"].get("name")
                yield pytest.param(step, id=f"{case['id']} {name}")


def refuses_the_request(step: Step) -> bool:
    return step["expected"].get("body") == {"error": "invalid_request"}


def is_accepted(step: Step) -> bool:
    return step["expected"]["status"] in ACCEPTED


def uploaded(step: Step) -> bytes:
    return base64.b64decode(step["request"]["json"]["data"], validate=True)


def shown_name(name: str) -> str:
    return re.split(r"[/\\]", name)[-1]


def users_of(case: Mapping[str, Any]) -> set[str]:
    return {
        user
        for step in steps_of(case)
        if (user := step["request"].get("headers", {}).get("X-User"))
    }


def mismatches(case: Mapping[str, Any]) -> Iterator[str]:
    """Each record or content a step expects that differs from the bytes its id was given for."""
    files: dict[str, bytes] = {}
    for step in case.get("steps", []):
        for name, source in step.get("capture", {}).items():
            if is_upload(step) and source == "body.id":
                files[name] = uploaded(step)
        expected = step.get("expected", {})
        found = CAPTURED_ID.match(step["request"].get("path", ""))
        if found is None or expected.get("status") != 200 or "body" not in expected:
            continue
        data = files[found[1]]
        if found[2] is None:
            wanted = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            got = {name: expected["body"][name] for name in wanted}
        else:
            wanted, got = data.decode("ascii"), expected["body"]
        if got != wanted:
            yield f"{step['request']['path']}: expected {got}, uploaded {wanted}"


def chunk_sizes(body: str) -> Iterator[int]:
    """The size of each chunk of a chunked body, checking its framing as it goes."""
    rest = body
    while rest:
        size_line, _, rest = rest.partition("\r\n")
        size = int(size_line, 16)
        assert rest[size : size + 2] == "\r\n", "each chunk ends with CRLF"
        rest = rest[size + 2 :]
        yield size


def scan_delays() -> Iterator[int]:
    for scenario in SCANNER["scenarios"].values():
        if scenario.get("route") == "scan":
            for entry in scenario.get("sequence", [scenario]):
                if "delay_ms" in entry:
                    yield entry["delay_ms"]


def test_each_user_sends_the_requests_of_one_case():
    """The app keeps its files across cases, so a shared user would share a quota."""
    cases_of_user: dict[str, set[str]] = {}
    for case in TESTS["cases"]:
        for user in users_of(case):
            cases_of_user.setdefault(user, set()).add(case["id"])

    assert {user: ids for user, ids in cases_of_user.items() if len(ids) > 1} == {}


@pytest.mark.parametrize(
    "step", [param for param in file_uploads() if not refuses_the_request(param.values[0])]
)
def test_an_upload_refused_for_anything_but_its_request_carries_canonical_base64(step: Step):
    """Base64 a decoder would skip or guess at would be refused as `invalid_request` first."""
    data = step["request"]["json"]["data"]

    assert base64.b64encode(base64.b64decode(data, validate=True)).decode() == data


@pytest.mark.parametrize(
    "step", [param for param in file_uploads() if is_accepted(param.values[0])]
)
def test_an_accepted_upload_is_a_file_level_2_allows(step: Step):
    """Every level is graded again later, so a level 1 upload meets level 2's rules too."""
    data = uploaded(step)
    extension = shown_name(step["request"]["json"]["name"]).rpartition(".")[2].lower()

    assert data.startswith(MAGIC_BY_EXTENSION[extension])
    assert not any(marker in data.decode("latin1").lower() for marker in ACTIVE_MARKERS)


@pytest.mark.parametrize(
    "case", [pytest.param(case, id=case["id"]) for case in TESTS["cases"] if "steps" in case]
)
def test_a_record_or_content_expected_back_is_what_was_uploaded(case: Mapping[str, Any]):
    assert list(mismatches(case)) == []


@pytest.mark.parametrize(("case_id", "size"), [("h3", MAX_BODY_BYTES), ("h4", MAX_BODY_BYTES + 1)])
def test_the_bodies_at_the_limit_are_sized_to_it(case_id: str, size: int):
    assert len(CASES[case_id]["request"]["body"].encode()) == size


def test_the_declared_body_is_over_the_limit_and_the_sent_one_under_it():
    request = CASES["h1"]["request"]

    assert int(request["headers"]["Content-Length"]) > MAX_BODY_BYTES
    assert len(request["body"].encode()) < MAX_BODY_BYTES


def test_the_chunked_body_passes_the_limit_and_never_ends():
    sizes = list(chunk_sizes(CASES["h2"]["request"]["body"]))

    assert sum(sizes) > MAX_BODY_BYTES
    assert 0 not in sizes


def test_every_delay_on_the_scan_route_outlasts_one_attempt():
    assert all(delay > SCAN_TIMEOUT_MS for delay in scan_delays())


def test_the_wait_for_an_expired_link_outlasts_the_link():
    seconds = next(
        step["request"]["json"]["expires_in_s"]
        for step in CASES["h42"]["steps"]
        if step["request"].get("path", "").endswith("/links")
    )

    assert SCANNER["scenarios"]["slow_status"]["delay_ms"] > seconds * 1000


def test_the_scanner_key_a_case_expects_is_the_one_the_app_reads():
    headers = CASES["v9"]["log"][0]["headers"]

    assert headers["Authorization"] == f"Bearer {ENV['SCANNER_API_KEY']}"
