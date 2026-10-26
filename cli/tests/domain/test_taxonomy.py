import json

from coding_study.domain.taxonomy import PATTERNS, pattern_rank
from tests.helpers import SCHEMAS_DIRECTORY


def test_patterns_match_the_meta_schema_in_taxonomy_order():
    schema = json.loads((SCHEMAS_DIRECTORY / "meta.schema.json").read_text())
    assert schema["$defs"]["pattern"]["enum"] == list(PATTERNS)


def test_rank_is_the_taxonomy_position():
    assert pattern_rank("two-pointers") == 1


def test_unknown_patterns_rank_after_every_known_one():
    assert pattern_rank("no-such-pattern") == len(PATTERNS)
