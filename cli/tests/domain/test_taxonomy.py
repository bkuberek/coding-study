import json

import pytest

from coding_study.domain.taxonomy import DOMAINS, JOB_ROLES, PATTERNS, Scope, pattern_rank
from tests.helpers import SCHEMAS_DIRECTORY

SCHEMAS_HOLDING_LABELS = ("meta.schema.json", "item.schema.json")


def schema_definitions(schema_file: str) -> dict:
    return json.loads((SCHEMAS_DIRECTORY / schema_file).read_text())["$defs"]


def test_patterns_match_the_meta_schema_in_taxonomy_order():
    assert schema_definitions("meta.schema.json")["pattern"]["enum"] == list(PATTERNS)


@pytest.mark.parametrize("schema_file", SCHEMAS_HOLDING_LABELS)
def test_domains_match_the_schema_in_taxonomy_order(schema_file):
    assert schema_definitions(schema_file)["domain"]["enum"] == list(DOMAINS)


@pytest.mark.parametrize("schema_file", SCHEMAS_HOLDING_LABELS)
def test_job_roles_match_the_schema_in_taxonomy_order(schema_file):
    assert schema_definitions(schema_file)["job_role"]["enum"] == list(JOB_ROLES)


@pytest.mark.parametrize("schema_file", SCHEMAS_HOLDING_LABELS)
def test_scopes_match_the_schema_in_taxonomy_order(schema_file):
    assert schema_definitions(schema_file)["scope"]["enum"] == [scope.value for scope in Scope]


def test_rank_is_the_taxonomy_position():
    assert pattern_rank("two-pointers") == 1


def test_unknown_patterns_rank_after_every_known_one():
    assert pattern_rank("no-such-pattern") == len(PATTERNS)
