import json
import re
from datetime import UTC, datetime

import pytest

from coding_study.domain.progress_export import (
    EXPORT_FORMAT,
    EXPORT_VERSION,
    ProgressSnapshot,
    export_document,
    export_text,
    parse_export,
)

EXPORTED_AT = datetime(2026, 10, 24, 10, 0, tzinfo=UTC)
SNAPSHOT = ProgressSnapshot(
    3,
    {
        "attempts": ({"id": 1, "slug": "two-sum", "lang": None, "ease": 2.5},),
        "schedule": (),
    },
)


def document(**overrides: object) -> dict[str, object]:
    fields: dict[str, object] = {
        "format": EXPORT_FORMAT,
        "version": EXPORT_VERSION,
        "schema_version": 3,
        "exported_at": "2026-10-24T10:00:00+00:00",
        "tables": {"attempts": [{"id": 1, "slug": "two-sum", "lang": None, "ease": 2.5}]},
    }
    return fields | overrides


def test_the_document_names_its_format_and_versions():
    exported = export_document(SNAPSHOT, EXPORTED_AT)
    assert (exported["format"], exported["version"], exported["schema_version"]) == (
        EXPORT_FORMAT,
        EXPORT_VERSION,
        3,
    )


def test_the_document_records_when_it_was_exported():
    assert export_document(SNAPSHOT, EXPORTED_AT)["exported_at"] == "2026-10-24T10:00:00+00:00"


def test_the_document_holds_every_row_as_stored():
    assert export_document(SNAPSHOT, EXPORTED_AT)["tables"] == {
        "attempts": [{"id": 1, "slug": "two-sum", "lang": None, "ease": 2.5}],
        "schedule": [],
    }


def test_a_document_parses_back_into_its_snapshot():
    assert parse_export(export_document(SNAPSHOT, EXPORTED_AT)) == SNAPSHOT


def test_the_text_is_the_document_as_json():
    assert json.loads(export_text(SNAPSHOT, EXPORTED_AT)) == export_document(SNAPSHOT, EXPORTED_AT)


def test_the_text_holds_one_row_per_line():
    assert export_text(SNAPSHOT, EXPORTED_AT).splitlines()[5:10] == [
        '  "tables": {',
        '    "attempts": [',
        '      {"id": 1, "slug": "two-sum", "lang": null, "ease": 2.5}',
        "    ],",
        '    "schedule": []',
    ]


def test_the_text_ends_with_a_newline():
    assert export_text(SNAPSHOT, EXPORTED_AT).endswith("}\n")


def test_the_text_of_an_empty_snapshot_is_json():
    assert json.loads(export_text(ProgressSnapshot(3, {}), EXPORTED_AT))["tables"] == {}


def test_the_snapshot_counts_rows_per_table():
    assert SNAPSHOT.row_counts() == {"attempts": 1, "schedule": 0}


@pytest.mark.parametrize(
    ("broken", "reason"),
    [
        ([], "not a coding-study progress export"),
        (document(format="other"), "not a coding-study progress export"),
        (document(version=2), "export version 2 is not supported (expected 1)"),
        (document(schema_version="3"), "schema_version must be a positive integer"),
        (document(schema_version=0), "schema_version must be a positive integer"),
        (document(tables=[]), "tables must be an object of row lists"),
        (document(tables={"attempts": {}}), "tables.attempts must be a list of rows"),
        (document(tables={"attempts": [1]}), "tables.attempts[0] must be an object"),
        (
            document(tables={"attempts": [{"id": [1]}]}),
            "tables.attempts[0].id must be a string, a number or null",
        ),
        (
            document(tables={"attempts": [{"id": True}]}),
            "tables.attempts[0].id must be a string, a number or null",
        ),
    ],
)
def test_a_broken_document_is_rejected_with_a_reason(broken, reason):
    with pytest.raises(ValueError, match=re.escape(reason)):
        parse_export(broken)
