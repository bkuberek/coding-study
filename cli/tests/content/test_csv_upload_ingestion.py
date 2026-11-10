"""csv-upload-ingestion-typescript grades a bulk file that its `grade_setup` generates from
`grading/bulk.json`, too big for a case to carry, and its cases drive S3 and SQS on the emulator
directly. These tests keep the bulk cases' expected answers equal to what the generator writes,
the bulk file bigger than the app's memory limit, every bucket and queue a case names one the
problem sets up, and every wait of a case well inside its limit."""

import json
import re
from collections.abc import Iterator, Mapping
from functools import cache
from typing import Any

import pytest
import yaml

from tests.helpers import REPOSITORY_ROOT

PROBLEM = REPOSITORY_ROOT / "problems" / "0284-csv-upload-ingestion-typescript"
BULK: Mapping[str, Any] = json.loads(
    (PROBLEM / "grading" / "bulk.json").read_text(encoding="utf-8")
)
PROJECT: Mapping[str, Any] = yaml.safe_load((PROBLEM / "meta.yaml").read_text(encoding="utf-8"))[
    "project"
]
ENV: Mapping[str, str] = PROJECT["env"]
TESTS: Mapping[str, Any] = json.loads((PROBLEM / "tests.json").read_text(encoding="utf-8"))
CASES = {case["id"]: case for case in TESTS["cases"]}
EMULATOR = "http://aws:5000/"
HEADER = "sku,description,quantity\n"
MEBIBYTE = 1 << 20
MAX_WAIT_S = 20
"""SQS refuses a longer `WaitTimeSeconds`."""
GRADER_BUCKET = "grader"
"""Where a case keeps a result it received, to read it back as JSON."""
BULK_SKU = "BULK-"

type Step = Mapping[str, Any]


def bulk_line(row: int) -> tuple[str, str, int]:
    """Row `row` of the bulk file, as `grade_setup.ts` writes it."""
    sku = f"{BULK_SKU}{row % BULK['skus']:03d}"
    description = f"Pallet line {row} {BULK['filler'] * 4}"[: BULK["description_length"]]
    bad = row % BULK["bad_every"] == 0
    return sku, description, 0 if bad else row % BULK["quantity_cycle"] + 1


@cache
def bulk_stock() -> Mapping[str, tuple[str, int]]:
    """Each SKU's description and quantity once the bulk file loads."""
    stock: dict[str, tuple[str, int]] = {}
    for row in range(1, BULK["rows"] + 1):
        sku, description, quantity = bulk_line(row)
        if quantity > 0:
            stock[sku] = (description, stock.get(sku, ("", 0))[1] + quantity)
    return stock


def bad_bulk_lines() -> list[int]:
    """The file's line of each bad row: the header is line 1, so row `n` is line `n + 1`."""
    return [row + 1 for row in range(BULK["bad_every"], BULK["rows"] + 1, BULK["bad_every"])]


@cache
def bulk_size() -> int:
    lines = (",".join(map(str, bulk_line(row))) + "\n" for row in range(1, BULK["rows"] + 1))
    return len(HEADER) + sum(len(line) for line in lines)


def steps_of(steps: list[Step]) -> Iterator[Step]:
    """Each step, with the flows it uses written out."""
    for step in steps:
        if "use" in step:
            yield from steps_of(TESTS["flows"][step["use"]])
        else:
            yield step


def requests_of(case: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    return (step["request"] for step in steps_of(case["steps"]))


def emulator_requests() -> Iterator[Mapping[str, Any]]:
    for case in CASES.values():
        yield from (r for r in requests_of(case) if r.get("url", "").startswith(EMULATOR))


def answer_to(case_id: str, path: str) -> Any:
    """What a case expects of the GET of `path`, a path of the app or the emulator's."""
    for step in steps_of(CASES[case_id]["steps"]):
        request = step["request"]
        if request["method"] == "GET" and path in (request.get("path"), request.get("url")):
            return step["expected"]["body"]
    raise AssertionError(f"{case_id} never asks for {path}")


def bulk_import() -> Mapping[str, Any]:
    rejected = len(bad_bulk_lines())
    return {
        "key": BULK["key"],
        "status": "loaded",
        "rows": BULK["rows"],
        "loaded": BULK["rows"] - rejected,
        "rejected": rejected,
    }


def wait_s(request: Mapping[str, Any]) -> int:
    return request.get("json", {}).get("WaitTimeSeconds", 0)


def test_the_bulk_file_is_bigger_than_the_apps_memory():
    limit = int(PROJECT["app"]["mem_limit"].removesuffix("m")) * MEBIBYTE

    assert bulk_size() > limit


@pytest.mark.parametrize(("case_id", "uploads"), [("h17", 1), ("h25", 2)])
def test_each_bulk_case_expects_one_import_per_upload_of_the_bulk_file(case_id: str, uploads: int):
    """`h24` uploads the bulk file a second time, and `h25` restarts the app while it loads."""
    assert answer_to(case_id, "/imports") == [bulk_import()] * uploads


def test_the_case_after_the_crash_restarts_the_app_and_keeps_its_data():
    """A reset would erase what the crash left, which is what `h25` judges."""
    assert (CASES["h25"].get("restart"), "fresh" in CASES["h25"]) == ("app", False)


def test_the_bulk_case_expects_a_report_line_for_each_bad_row_the_generator_writes():
    report = "".join(f"{line},invalid_quantity\n" for line in bad_bulk_lines())

    assert answer_to("h17", f"{EMULATOR}upload-reports/{BULK['key']}") == f"line,error\n{report}"


@pytest.mark.parametrize(
    ("case_id", "sku", "uploads"),
    [("h17", "BULK-000", 1), ("h17", "BULK-042", 1), ("h25", "BULK-007", 2)],
)
def test_each_bulk_product_is_what_the_generator_adds_up_to(case_id: str, sku: str, uploads: int):
    description, quantity = bulk_stock()[sku]

    assert answer_to(case_id, f"/products/{sku}") == {
        "sku": sku,
        "description": description,
        "quantity": quantity * uploads,
    }


def test_every_queue_a_case_names_is_one_the_problem_sets_up():
    queues = {value for name, value in ENV.items() if name.endswith("_QUEUE_URL")}
    named = {r["json"]["QueueUrl"] for r in emulator_requests() if "json" in r}

    assert named <= queues


def test_every_bucket_a_case_names_is_one_the_problem_sets_up_or_the_graders_own():
    buckets = {ENV["UPLOAD_BUCKET"], ENV["REPORT_BUCKET"], GRADER_BUCKET}
    named = {r["url"].removeprefix(EMULATOR).split("/")[0] for r in emulator_requests()}

    assert named - {""} <= buckets


def test_no_case_waits_longer_than_sqs_allows():
    assert max(wait_s(request) for request in emulator_requests()) <= MAX_WAIT_S


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_a_cases_waits_take_at_most_half_its_limit(case_id: str):
    """The reference's slowest case stays within half its limit, and a case that waits in vain
    must still end inside it."""
    case = CASES[case_id]
    waited_ms = 1000 * sum(wait_s(request) for request in requests_of(case))

    assert waited_ms <= case["hang_guard_ms"] / 2


def skus_in(steps: list[Step]) -> Iterator[str]:
    """The valid SKUs of the files a case uploads, and of the products it asks for."""
    for step in steps:
        files = [step.get("with", {}).get("csv"), step.get("request", {}).get("body")]
        for file in filter(None, files):
            fields = (line.split(",")[0] for line in file.splitlines()[1:])
            yield from (field for field in fields if VALID_SKU.fullmatch(field))
        product = PRODUCT_PATH.fullmatch(step.get("request", {}).get("path", ""))
        if product is not None:
            yield product[1]


VALID_SKU = re.compile(r"[A-Z0-9][A-Z0-9-]{0,31}")
PRODUCT_PATH = re.compile(r"/products/(.+)")


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_a_case_names_only_skus_of_its_own_or_of_the_bulk_file(case_id: str):
    """Cases share one database, so a SKU of one case must not appear in another."""
    own = (f"{case_id.upper()}-", BULK_SKU)

    assert all(sku.startswith(own) for sku in skus_in(CASES[case_id]["steps"]))
